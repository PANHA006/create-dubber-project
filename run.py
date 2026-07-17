import sys
import io

# Force console outputs to use UTF-8 and write unbuffered directly to console
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True, write_through=True)
except Exception:
    pass

try:
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True, write_through=True)
except Exception:
    pass

print("==========================================================", flush=True)
print("              STARTING DUBBER AI APPLICATION             ", flush=True)
print("==========================================================", flush=True)
print("[DubberAI] Initializing environment and paths...", flush=True)

if sys.platform == 'win32':
    import asyncio
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        if not getattr(_ProactorBasePipeTransport._call_connection_lost, '__patched__', False):
            _orig_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
            
            def _patched_call_connection_lost(self, exc):
                try:
                    _orig_call_connection_lost(self, exc)
                except (ConnectionResetError, OSError):
                    # Silence ConnectionResetError and OSError during cleanup of forcibly closed socket
                    pass
                    
            _patched_call_connection_lost.__patched__ = True
            _ProactorBasePipeTransport._call_connection_lost = _patched_call_connection_lost
    except Exception:
        pass

import warnings
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

# 1. Initialize local path injection for FFmpeg & FFprobe
from src.utils.path_helper import setup_ffmpeg_path
setup_ffmpeg_path()

print("[DubberAI] Loading audio/video processing libraries...", flush=True)
# Configure pydub to use the same ffmpeg executable
import imageio_ffmpeg
from pydub import AudioSegment
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

print("[DubberAI] Loading machine learning and interface libraries (this may take 10-20 seconds)...", flush=True)
# 2. Build and launch the Gradio UI
import gradio as gr
from src.ui.web_ui import build_ui, CUSTOM_CSS

demo, head_html = build_ui()
print("[DubberAI] Libraries loaded. Launching local web server...", flush=True)

if __name__ == "__main__":
    import os
    output_abs_path = os.path.abspath("output")
    demo.queue()
    demo.launch(
        server_name="127.0.0.1", 
        share=False, 
        inbrowser=True,
        theme=gr.themes.Default(), 
        css=CUSTOM_CSS, 
        head=head_html,
        allowed_paths=[output_abs_path]
    )
