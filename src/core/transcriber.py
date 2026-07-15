import subprocess
import whisper
import imageio_ffmpeg

WHISPER_MODELS = {}

def get_whisper_model(model_name):
    if model_name not in WHISPER_MODELS:
        print(f"Loading Whisper model '{model_name}' (this might take a while on the first run)...")
        WHISPER_MODELS[model_name] = whisper.load_model(model_name)
    return WHISPER_MODELS[model_name]

from src.utils.path_helper import get_ffmpeg_executable

def extract_audio(video_path, output_wav_path):
    ffmpeg_exe = get_ffmpeg_executable()
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
