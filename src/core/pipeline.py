import os
import shutil
import tempfile
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
from src.utils.subtitle_helper import generate_ass_file
from src.utils.path_helper import get_ffmpeg_executable

def assemble_video(video_path, audio_path, ass_path, output_video_path):
    ffmpeg_exe = get_ffmpeg_executable()
    
    cmd = [ffmpeg_exe, "-y", "-i", video_path]
    
    if audio_path:
        cmd.extend(["-i", audio_path])
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
    else:
        cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])
        
    if ass_path:
        safe_ass_path = ass_path.replace("\\", "/").replace(":", "\\:")
        
        # Check if local fonts folder exists to load custom fonts
        fonts_dir = os.path.join(os.getcwd(), "resources", "fonts")
        if os.path.exists(fonts_dir):
            safe_fonts_dir = fonts_dir.replace("\\", "/").replace(":", "\\:")
            # Khmer requires HarfBuzz complex shaping for consonant clusters,
            # coeng signs, and dependent vowels to be positioned correctly.
            cmd.extend(["-vf", f"ass=filename='{safe_ass_path}':fontsdir='{safe_fonts_dir}':shaping=complex"])
        else:
            cmd.extend(["-vf", f"ass=filename='{safe_ass_path}':shaping=complex"])
            
        cmd.extend(["-c:v", "libx264"])
    else:
        cmd.extend(["-c:v", "copy"])
        
    if audio_path:
        cmd.extend(["-c:a", "aac"])
    else:
        cmd.extend(["-c:a", "copy"])
        
    cmd.append(output_video_path)
    
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
            
        from src.utils.subtitle_helper import merge_fragmented_segments
        segments = merge_fragmented_segments(segments)
        
        source_code = "auto"
        if source_lang != "Auto Detect":
            source_code = LANGUAGES.get(source_lang, {}).get("translator", "auto")
            
        target_code = LANGUAGES.get(target_lang, {}).get("translator", "es")
        
        translated_segments = []
        print(f"Translating {len(segments)} segments to {target_lang}...")
        for seg in segments:
            trans_text = translate_text(seg["text"], source_code, target_code)
            clean_trans = trans_text.strip() if trans_text else ""
            
            if target_lang == "Khmer":
                from src.utils.subtitle_helper import clean_khmer_subtitles, balance_khmer_lines
                clean_trans = clean_khmer_subtitles(clean_trans)
                
                clean_trans = balance_khmer_lines(clean_trans, max_len=42)
                
            translated_segments.append({
                "ID": seg["id"],
                "Start": round(seg["start"], 2),
                "End": round(seg["end"], 2),
                "Orig": seg["text"].strip(),
                "Trans": clean_trans
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
def step2_generate_dubbed_video(df, video_path, extracted_audio, temp_dir, target_voice, background_volume, remove_spoken_voice=False, processing_mode="Dubbing Only", sub_font="Arial", sub_font_size=24, sub_align="Bottom", sub_bg_box=False):
    if df is None or df.empty:
        return None, "Please transcribe the video first in Step 1!"
    if not video_path or not extracted_audio or not temp_dir:
        return None, "Missing file path data. Please perform Step 1 again."
    
    try:
        is_dubbing_enabled = processing_mode in ["Dubbing Only", "Dubbing + Subtitles"]
        is_subtitles_enabled = processing_mode in ["Subtitles Only", "Dubbing + Subtitles"]
        
        # Check if we have a local decoupled copy of the video to avoid Windows file locks
        local_video_path = None
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                if file.startswith("local_input"):
                    local_video_path = os.path.join(temp_dir, file)
                    break
        video_to_process = local_video_path if local_video_path else video_path
        print(f"Using decoupled video for processing: {video_to_process}")

        mixed_wav = None
        if is_dubbing_enabled:
            print("Loading original audio for duration sizing...")
            original_audio = load_audio_segment_natively(extracted_audio)
            total_duration_ms = len(original_audio)
            
            print(f"Creating output silent canvas ({total_duration_ms/1000.0:.2f} seconds)...")
            dubbed_audio = AudioSegment.silent(duration=total_duration_ms)
            
            for index, row in df.iterrows():
                seg_id = int(row["ID"])
                start_s = float(row["Start"])
                end_s = float(row["End"])
                translated_text = str(row["Trans"]).strip()
                
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
            
            # Mute spoken segments from original background audio if requested
            bg_track_to_mix = extracted_audio
            if remove_spoken_voice:
                print("Muting original spoken voice segments in background audio...")
                muted_bg = os.path.join(temp_dir, "muted_background.wav")
                bg_audio = load_audio_segment_natively(extracted_audio)
                for index, row in df.iterrows():
                    start_ms = int(float(row["Start"]) * 1000)
                    end_ms = int(float(row["End"]) * 1000)
                    start_ms = max(0, min(start_ms, len(bg_audio)))
                    end_ms = max(0, min(end_ms, len(bg_audio)))
                    if end_ms > start_ms:
                        silence = AudioSegment.silent(duration=end_ms - start_ms, frame_rate=bg_audio.frame_rate)
                        bg_audio = bg_audio[:start_ms] + silence + bg_audio[end_ms:]
                bg_audio.export(muted_bg, format="wav")
                bg_track_to_mix = muted_bg

            # Mix background audio
            mixed_wav = os.path.join(temp_dir, "mixed_track.wav")
            mix_audio_tracks(bg_track_to_mix, dubbed_wav, background_volume, mixed_wav)

        ass_path = None
        if is_subtitles_enabled:
            print("Generating ASS subtitle file...")
            ass_path = os.path.join(temp_dir, "subtitles.ass")
            align_map = {"Bottom": 2, "Top": 8, "Middle": 5}
            alignment = align_map.get(sub_align, 2)
            generate_ass_file(df, ass_path, font_name=sub_font, font_size=sub_font_size, alignment=alignment, bg_box=sub_bg_box)
            
        # Assemble video in workspace directory to avoid outputting in temp directories
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize output filename
        orig_filename = os.path.basename(video_path)
        name, ext = os.path.splitext(orig_filename)
        
        import time
        timestamp = int(time.time())
        if processing_mode == "Subtitles Only":
            output_video_path = os.path.join(output_dir, f"{name}_subtitled_{timestamp}{ext}")
        elif processing_mode == "Dubbing + Subtitles":
            output_video_path = os.path.join(output_dir, f"{name}_dubbed_subtitled_{timestamp}{ext}")
        else:
            output_video_path = os.path.join(output_dir, f"{name}_dubbed_{timestamp}{ext}")
            
        print(f"Rendering output video: {output_video_path}...")
        assemble_video(video_to_process, mixed_wav, ass_path, output_video_path)
        
        status_msg = f"Success! Dubbed video created. Saved to:\n{output_video_path}"
        return output_video_path, status_msg
        
    except Exception as e:
        import traceback
        err_msg = f"Error during Step 2: {str(e)}\n{traceback.format_exc()}"
        print(err_msg)
        return None, err_msg
