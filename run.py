import os
import sys
import io

# Force console outputs to use UTF-8 to prevent UnicodeEncodeError crashes on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 1. Initialize local path injection for FFmpeg & FFprobe
from src.utils.path_helper import setup_ffmpeg_path
setup_ffmpeg_path()

# Configure pydub to use the same ffmpeg executable
import imageio_ffmpeg
from pydub import AudioSegment
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# 2. Build and launch the Gradio UI
import gradio as gr
from src.ui.web_ui import build_ui

demo = build_ui()

if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="127.0.0.1", share=False, theme=gr.themes.Default())
