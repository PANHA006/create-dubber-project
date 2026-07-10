import os
import sys
import io
import time
import math
import shutil
import tempfile
import asyncio
import subprocess
import pandas as pd
import gradio as gr

# Force console outputs to use UTF-8 to prevent crashes when printing Unicode text (e.g. Khmer, Arabic, Chinese) on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Create a local ffmpeg.exe and ffprobe.exe wrapper in temp so Whisper and Gradio can call them
try:
    import imageio_ffmpeg
    import urllib.request
    import zipfile
    
    ffmpeg_real_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_bin_dir = os.path.join(tempfile.gettempdir(), "ffmpeg_local_bin")
    os.makedirs(temp_bin_dir, exist_ok=True)
    
    # 1. Setup ffmpeg.exe
    local_ffmpeg_exe = os.path.join(temp_bin_dir, "ffmpeg.exe")
    if not os.path.exists(local_ffmpeg_exe):
        print(f"Creating local ffmpeg.exe alias: {local_ffmpeg_exe}")
        shutil.copyfile(ffmpeg_real_exe, local_ffmpeg_exe)
        
    # 2. Setup ffprobe.exe (needed by Gradio to process final video playability)
    local_ffprobe_exe = os.path.join(temp_bin_dir, "ffprobe.exe")
    if not os.path.exists(local_ffprobe_exe):
        print("ffprobe.exe not found. Downloading static build from GitHub releases...")
        ffprobe_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip"
        zip_path = os.path.join(temp_bin_dir, "ffprobe.zip")
        try:
            req = urllib.request.Request(
                ffprobe_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_bin_dir)
            os.remove(zip_path)
            print("ffprobe.exe downloaded and extracted successfully!")
        except Exception as dl_err:
            print(f"WARNING: Could not download ffprobe.exe automatically: {dl_err}")
            print("Please ensure you have an active internet connection. If Gradio fails to display the video, install ffmpeg/ffprobe manually.")

    # 3. Inject temp directory into PATH
    if temp_bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = temp_bin_dir + os.pathsep + os.environ["PATH"]
    print(f"FFmpeg/FFprobe path injected: {temp_bin_dir}")
except Exception as e:
    print(f"WARNING: Failed to set up local FFmpeg/FFprobe wrapper: {e}")

import pydub
from pydub import AudioSegment
# Configure pydub to use the same ffmpeg executable
if 'imageio_ffmpeg' in sys.modules:
    AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

from deep_translator import GoogleTranslator
import whisper
import edge_tts

# Supported languages mapping
LANGUAGES = {
    "English": {"translator": "en", "tts_prefix": "en-"},
    "Spanish": {"translator": "es", "tts_prefix": "es-"},
    "French": {"translator": "fr", "tts_prefix": "fr-"},
    "German": {"translator": "de", "tts_prefix": "de-"},
    "Italian": {"translator": "it", "tts_prefix": "it-"},
    "Portuguese": {"translator": "pt", "tts_prefix": "pt-"},
    "Chinese (Simplified)": {"translator": "zh-CN", "tts_prefix": "zh-CN-"},
    "Chinese (Traditional)": {"translator": "zh-TW", "tts_prefix": "zh-TW-"},
    "Japanese": {"translator": "ja", "tts_prefix": "ja-"},
    "Korean": {"translator": "ko", "tts_prefix": "ko-"},
    "Russian": {"translator": "ru", "tts_prefix": "ru-"},
    "Arabic": {"translator": "ar", "tts_prefix": "ar-"},
    "Hindi": {"translator": "hi", "tts_prefix": "hi-"},
    "Turkish": {"translator": "tr", "tts_prefix": "tr-"},
    "Vietnamese": {"translator": "vi", "tts_prefix": "vi-"},
    "Thai": {"translator": "th", "tts_prefix": "th-"},
    "Dutch": {"translator": "nl", "tts_prefix": "nl-"},
    "Polish": {"translator": "pl", "tts_prefix": "pl-"},
    "Ukrainian": {"translator": "uk", "tts_prefix": "uk-"},
    "Indonesian": {"translator": "id", "tts_prefix": "id-"},
    "Khmer": {"translator": "km", "tts_prefix": "km-"},
}

WHISPER_MODELS = {}
VOICE_LIST = []

def get_whisper_model(model_name):
    if model_name not in WHISPER_MODELS:
        print(f"Loading Whisper model '{model_name}' (this might take a while on the first run)...")
        WHISPER_MODELS[model_name] = whisper.load_model(model_name)
    return WHISPER_MODELS[model_name]

def load_voices_sync():
    global VOICE_LIST
    if not VOICE_LIST:
        try:
            print("Fetching Microsoft Edge TTS voices list...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(edge_tts.VoicesManager.create())
            VOICE_LIST = voices.voices
            loop.close()
            print(f"Loaded {len(VOICE_LIST)} voices from Microsoft Edge TTS.")
        except Exception as e:
            print(f"Error fetching Edge TTS voices: {e}. Using fallback voice list.")
            # Standard high-quality voices as fallbacks
            VOICE_LIST = [
                {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female"},
                {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
                {"ShortName": "es-ES-ElviraNeural", "Locale": "es-ES", "Gender": "Female"},
                {"ShortName": "es-ES-AlvaroNeural", "Locale": "es-ES", "Gender": "Male"},
                {"ShortName": "fr-FR-DeniseNeural", "Locale": "fr-FR", "Gender": "Female"},
                {"ShortName": "fr-FR-HenriNeural", "Locale": "fr-FR", "Gender": "Male"},
                {"ShortName": "de-DE-AmalaNeural", "Locale": "de-DE", "Gender": "Female"},
                {"ShortName": "de-DE-ConradNeural", "Locale": "de-DE", "Gender": "Male"},
                {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"},
                {"ShortName": "zh-CN-YunxiNeural", "Locale": "zh-CN", "Gender": "Male"},
                {"ShortName": "ja-JP-NanamiNeural", "Locale": "ja-JP", "Gender": "Female"},
                {"ShortName": "ja-JP-KeitaNeural", "Locale": "ja-JP", "Gender": "Male"},
                {"ShortName": "km-KH-SreymomNeural", "Locale": "km-KH", "Gender": "Female"},
                {"ShortName": "km-KH-PisethNeural", "Locale": "km-KH", "Gender": "Male"},
            ]
    return VOICE_LIST

def update_voices_dropdown(target_lang):
    voices = load_voices_sync()
    lang_info = LANGUAGES.get(target_lang)
    if not lang_info:
        return gr.Dropdown(choices=[], value=None)
    
    prefix = lang_info["tts_prefix"]
    filtered_voices = [
        v["ShortName"] for v in voices 
        if v["ShortName"].lower().startswith(prefix.lower())
    ]
    filtered_voices = sorted(filtered_voices)
    
    default_val = filtered_voices[0] if filtered_voices else None
    return gr.Dropdown(choices=filtered_voices, value=default_val)

def translate_text(text, source_lang="auto", target_lang="es"):
    if not text.strip():
        return ""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def extract_audio(video_path, output_wav_path):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_wav_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def load_audio_segment_natively(file_path):
    temp_pcm = file_path + ".raw"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", file_path,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        temp_pcm
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with open(temp_pcm, "rb") as f:
        pcm_data = f.read()
    try:
        os.remove(temp_pcm)
    except Exception as e:
        print(f"Warning: could not remove temp raw PCM file: {e}")
    return AudioSegment(
        data=pcm_data,
        sample_width=2,
        frame_rate=16000,
        channels=1
    )

def get_audio_duration(file_path):
    audio = load_audio_segment_natively(file_path)
    return len(audio) / 1000.0

def adjust_audio_speed(input_path, output_path, speed):
    if abs(speed - 1.0) < 0.05:
        shutil.copyfile(input_path, output_path)
        return
    
    filters = []
    temp_speed = speed
    if temp_speed > 3.0:
        temp_speed = 3.0
    if temp_speed < 0.5:
        temp_speed = 0.5
        
    while temp_speed > 2.0:
        filters.append("atempo=2.0")
        temp_speed /= 2.0
    while temp_speed < 0.5:
        filters.append("atempo=0.5")
        temp_speed /= 0.5
    filters.append(f"atempo={temp_speed:.2f}")
    filter_str = ",".join(filters)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_path,
        "-filter:a", filter_str,
        "-vn",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

async def synthesize_text_async(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_tts(text, voice, output_path):
    try:
        # Run async function synchronously
        asyncio.run(synthesize_text_async(text, voice, output_path))
        return True
    except Exception as e:
        print(f"TTS Synthesis error for text '{text}': {e}")
        return False

def mix_audio_tracks(original_audio_path, dubbed_audio_path, background_volume, output_mixed_path):
    original_audio = load_audio_segment_natively(original_audio_path)
    dubbed_audio = load_audio_segment_natively(dubbed_audio_path)
    
    if background_volume > 0.0:
        vol = max(background_volume, 0.0001)
        db_reduction = 20 * math.log10(vol)
        reduced_bg = original_audio.apply_gain(db_reduction)
        mixed_audio = reduced_bg.overlay(dubbed_audio)
    else:
        mixed_audio = dubbed_audio
        
    mixed_audio.export(output_mixed_path, format="wav")

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


# --- GRADIO WEB INTERFACE ---

with gr.Blocks(title="AI Video Dubber") as demo:
    # State management variables
    extracted_audio_state = gr.State("")
    temp_dir_state = gr.State("")
    

    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎛️ Configurations & Upload")
            input_video = gr.Video(label="Upload Source Video (MP4)", sources=["upload"])
            
            with gr.Group():
                whisper_model = gr.Dropdown(
                    label="Whisper Transcription Model", 
                    choices=["tiny", "base", "small", "medium", "large"], 
                    value="base"
                )
                source_lang = gr.Dropdown(
                    label="Source Language", 
                    choices=["Auto Detect"] + list(LANGUAGES.keys()), 
                    value="Auto Detect"
                )
                target_lang = gr.Dropdown(
                    label="Target Language", 
                    choices=list(LANGUAGES.keys()), 
                    value="Spanish"
                )
                target_voice = gr.Dropdown(
                    label="Target TTS Voice Accent", 
                    choices=[], 
                    value=None
                )
                
            with gr.Group():
                bg_volume = gr.Slider(
                    label="Background Music/Noise Volume (0 = Mute background)", 
                    minimum=0.0, 
                    maximum=1.0, 
                    value=0.15, 
                    step=0.05
                )
            
            btn_step1 = gr.Button("Step 1: Transcribe & Translate", variant="primary")
            
        with gr.Column(scale=2):
            gr.Markdown("### 📝 Translation Preview & Editor")
            status_output = gr.Textbox(label="Engine Status / Logs", placeholder="Awaiting steps...", interactive=False)
            
            # Transcription spreadsheet editor
            transcription_df = gr.Dataframe(
                headers=["ID", "Start (s)", "End (s)", "Original Text", "Translated Text"],
                datatype=["number", "number", "number", "str", "str"],
                column_count=(5, "fixed"),
                interactive=True,
                label="Double-click to edit Translated Text before generating dub"
            )
            
            btn_step2 = gr.Button("Step 2: Generate Dubbed Video", variant="secondary")
            
            gr.Markdown("### 🎥 Output Dubbed Video")
            output_video = gr.Video(label="Final Dubbed Result")
            
    # Language change triggers voice dropdown population
    target_lang.change(
        fn=update_voices_dropdown, 
        inputs=[target_lang], 
        outputs=[target_voice]
    )
    
    # Initialize voice choices on load
    demo.load(
        fn=lambda: update_voices_dropdown("Spanish"),
        outputs=[target_voice]
    )
    
    # Button triggers
    btn_step1.click(
        fn=step1_transcribe_and_translate,
        inputs=[input_video, whisper_model, source_lang, target_lang],
        outputs=[transcription_df, extracted_audio_state, temp_dir_state, status_output]
    )
    
    btn_step2.click(
        fn=step2_generate_dubbed_video,
        inputs=[transcription_df, input_video, extracted_audio_state, temp_dir_state, target_voice, bg_volume],
        outputs=[output_video, status_output]
    )

if __name__ == "__main__":
    demo.queue()
    # Share=True to create a public sharing link if needed, local run is default
    demo.launch(server_name="127.0.0.1", share=False, theme=gr.themes.Default())
