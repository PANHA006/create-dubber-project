import sys
import io

# Force console outputs to use UTF-8 to prevent UnicodeEncodeError crashes on Windows
if not getattr(sys.stdout, '__utf8_wrapped__', False):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stdout.__utf8_wrapped__ = True
    except Exception:
        pass

if not getattr(sys.stderr, '__utf8_wrapped__', False):
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        sys.stderr.__utf8_wrapped__ = True
    except Exception:
        pass

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

# Configure pydub to use the same ffmpeg executable
import imageio_ffmpeg
from pydub import AudioSegment
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

# 2. Build and launch the Gradio UI
import gradio as gr
from src.ui.web_ui import build_ui, CUSTOM_CSS

demo, head_html = build_ui()

if __name__ == "__main__":
    demo.queue()
    demo.launch(server_name="127.0.0.1", share=False, theme=gr.themes.Default(), css=CUSTOM_CSS, head=head_html)
