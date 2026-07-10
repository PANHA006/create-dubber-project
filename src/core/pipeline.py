import os
import shutil
import tempfile
import math
import pandas as pd
from pydub import AudioSegment
import imageio_ffmpeg

from src.config import LANGUAGES
from src.core.transcriber import get_whisper_model, extract_audio
from src.core.translator import translate_text
from src.core.synthesizer import generate_tts
from src.utils.audio_helper import (
    load_audio_segment_natively,
    get_audio_duration,
    adjust_audio_speed,
    mix_audio_tracks
)

def merge_audio_video(video_path, audio_path, output_video_path):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        output_video_path
    ]
    import subprocess
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

# Step 1: Transcribe & Translate
def step1_transcribe_and_translate(video_path, model_name, source_lang, target_lang):
    if not video_path:
        return pd.DataFrame(), "", "", "Please upload a video file first!"
    
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Copy input video to temp directory to avoid Windows file sharing locks while Gradio streams it
        video_ext = os.path.splitext(video_path)[1]
        local_video_path = os.path.join(temp_dir, f"local_input{video_ext}")
        print(f"Creating decoupled local video copy: {local_video_path}")
        shutil.copyfile(video_path, local_video_path)
        
        extracted_audio = os.path.join(temp_dir, "extracted_original.wav")
        
        print("Extracting audio track...")
        extract_audio(local_video_path, extracted_audio)
        
        print("Loading Whisper model...")
        model = get_whisper_model(model_name)
        
        print("Transcribing...")
        result = model.transcribe(extracted_audio)
        
        segments = result.get("segments", [])
        if not segments:
            return pd.DataFrame(), "", "", "No speech detected in the video!"
        
        source_code = "auto"
        if source_lang != "Auto Detect":
            source_code = LANGUAGES.get(source_lang, {}).get("translator", "auto")
            
        target_code = LANGUAGES.get(target_lang, {}).get("translator", "es")
        
        translated_segments = []
        print(f"Translating {len(segments)} segments to {target_lang}...")
        for seg in segments:
            trans_text = translate_text(seg["text"], source_code, target_code)
            translated_segments.append({
                "ID": seg["id"],
                "Start (s)": round(seg["start"], 2),
                "End (s)": round(seg["end"], 2),
                "Original Text": seg["text"].strip(),
                "Translated Text": trans_text.strip() if trans_text else ""
            })
            
        df = pd.DataFrame(translated_segments)
        status_msg = f"Successfully transcribed {len(segments)} segments. You can edit the 'Translated Text' in the table below before generating the dubbed video."
        return df, extracted_audio, temp_dir, status_msg
        
    except Exception as e:
        import traceback
        err_msg = f"Error during Step 1: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        return pd.DataFrame(), "", "", err_msg

# Step 2: Generate Dubbed Video
def step2_generate_dubbed_video(df, video_path, extracted_audio, temp_dir, target_voice, background_volume):
    if df is None or df.empty:
        return None, "Please transcribe the video first in Step 1!"
    if not video_path or not extracted_audio or not temp_dir:
        return None, "Missing file path data. Please perform Step 1 again."
    
    try:
        # Check if we have a local decoupled copy of the video to avoid Windows file locks
        local_video_path = None
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                if file.startswith("local_input"):
                    local_video_path = os.path.join(temp_dir, file)
                    break
        video_to_process = local_video_path if local_video_path else video_path
        print(f"Using decoupled video for dubbing: {video_to_process}")

        print("Loading original audio for duration sizing...")
        original_audio = load_audio_segment_natively(extracted_audio)
        total_duration_ms = len(original_audio)
        
        print(f"Creating output silent canvas ({total_duration_ms/1000.0:.2f} seconds)...")
        dubbed_audio = AudioSegment.silent(duration=total_duration_ms)
        
        for index, row in df.iterrows():
            seg_id = int(row["ID"])
            start_s = float(row["Start (s)"])
            end_s = float(row["End (s)"])
            translated_text = str(row["Translated Text"]).strip()
            
            if not translated_text:
                continue
                
            start_ms = int(start_s * 1000)
            end_ms = int(end_s * 1000)
            target_duration = (end_ms - start_ms) / 1000.0
            
            temp_tts = os.path.join(temp_dir, f"seg_{seg_id}_temp.mp3")
            aligned_tts = os.path.join(temp_dir, f"seg_{seg_id}_aligned.wav")
            
            print(f"Synthesizing Segment {seg_id}: '{translated_text[:30]}...'")
            success = generate_tts(translated_text, target_voice, temp_tts)
            if not success:
                print(f"Skipping segment {seg_id} due to TTS failure.")
                continue
                
            synth_duration = get_audio_duration(temp_tts)
            
            if synth_duration > target_duration and target_duration > 0.2:
                speed = synth_duration / target_duration
                if speed > 2.5:
                    speed = 2.5
                print(f"Adjusting speed of Segment {seg_id}: {speed:.2f}x")
                adjust_audio_speed(temp_tts, aligned_tts, speed)
            else:
                adjust_audio_speed(temp_tts, aligned_tts, 1.0)
                
            # Read and place on timeline
            seg_audio = load_audio_segment_natively(aligned_tts)
            dubbed_audio = dubbed_audio.overlay(seg_audio, position=start_ms)
            
        # Export final dubbed track
        dubbed_wav = os.path.join(temp_dir, "dubbed_track.wav")
        dubbed_audio.export(dubbed_wav, format="wav")
        
        # Mix background audio
        mixed_wav = os.path.join(temp_dir, "mixed_track.wav")
        mix_audio_tracks(extracted_audio, dubbed_wav, background_volume, mixed_wav)
        
        # Assemble video in workspace directory to avoid outputting in temp directories
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize output filename
        orig_filename = os.path.basename(video_path)
        name, ext = os.path.splitext(orig_filename)
        output_video_path = os.path.join(output_dir, f"{name}_dubbed{ext}")
        
        print(f"Rendering dubbed video: {output_video_path}...")
        merge_audio_video(video_to_process, mixed_wav, output_video_path)
        
        status_msg = f"Success! Dubbed video created. Saved to:\n{output_video_path}"
        return output_video_path, status_msg
        
    except Exception as e:
        import traceback
        err_msg = f"Error during Step 2: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        return None, err_msg
