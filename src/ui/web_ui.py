import gradio as gr
import pandas as pd
from src.config import LANGUAGES
from src.core.synthesizer import load_voices_sync
from src.core.pipeline import step1_transcribe_and_translate, step2_generate_dubbed_video
from src.utils.audio_helper import make_video_browser_compatible

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

def build_ui():
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
        
        # Auto-transcode uploaded videos to browser-compatible format if needed
        input_video.upload(
            fn=make_video_browser_compatible,
            inputs=[input_video],
            outputs=[input_video]
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
        
    return demo
