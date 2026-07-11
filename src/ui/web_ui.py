import gradio as gr
from src.config import LANGUAGES
from src.core.synthesizer import load_voices_sync
from src.core.pipeline import step1_transcribe_and_translate, step2_generate_dubbed_video
from src.utils.audio_helper import make_video_browser_compatible

CUSTOM_CSS = """
body, .gradio-container {
    background-color: #0b0f19 !important;
    color: #e2e8f0 !important;
    max-width: 100% !important;
    padding-left: 0px !important;
    padding-right: 0px !important;
}
.main-layout {
    padding-left: 24px !important;
    padding-right: 24px !important;
}
footer {
    display: none !important;
}
/* Dataframe custom overrides with minimized padding */
.gradio-container table {
    border-collapse: collapse !important;
}
.gradio-container th {
    background-color: #0f172a !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.05em !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #1e293b !important;
    padding: 4px 8px !important;
}
.gradio-container td {
    border: 1px solid #1e293b !important;
    padding: 4px 8px !important;
}
"""

import os

def process_uploaded_file(file_obj):
    if file_obj is None:
        return None
    if hasattr(file_obj, "path"):
        return file_obj.path
    if isinstance(file_obj, dict) and "path" in file_obj:
        return file_obj["path"]
    if isinstance(file_obj, str):
        return file_obj
    return getattr(file_obj, "name", None)

def handle_video_upload(file_obj):
    raw_path = process_uploaded_file(file_obj)
    if not raw_path:
        return None, None, "No video uploaded.", gr.Button(interactive=False)
    try:
        compatible_path = make_video_browser_compatible(raw_path)
        return compatible_path, compatible_path, f"Video uploaded successfully: {os.path.basename(compatible_path)}", gr.Button(interactive=True)
    except Exception as e:
        return None, None, f"Error processing uploaded video: {str(e)}", gr.Button(interactive=False)

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
    head_html = """
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Outfit', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    """
    with gr.Blocks(title="AI Video Dubber") as demo:
        # State management variables
        extracted_audio_state = gr.State("")
        temp_dir_state = gr.State("")
        video_file_state = gr.State("")
        
        # Navigation Bar Row
        with gr.Row(elem_id="navbar", elem_classes=["flex", "items-center", "gap-4", "p-3", "px-6", "mb-8", "bg-[#0f172a]/80", "backdrop-blur-md", "border-b", "border-white/5", "w-full", "shadow-xl", "shadow-black/20"]):
            gr.HTML("""
            <div class="flex items-center gap-3 cursor-pointer hover:opacity-95 transition-opacity">
                <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-white/5 border border-white/10 shadow-inner">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 2L3 7L12 12L21 7L12 2Z" fill="url(#logo-gradient-tw)" stroke="url(#logo-gradient-tw)" stroke-width="2" stroke-linejoin="round"/>
                        <path d="M3 12L12 17L21 12" stroke="url(#logo-gradient-tw)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
                        <path d="M3 16L12 21L21 16" stroke="url(#logo-gradient-tw)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
                        <defs>
                            <linearGradient id="logo-gradient-tw" x1="3" y1="2" x2="21" y2="21" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#fbbf24"/>
                                <stop offset="1" stop-color="#ea580c"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <div class="flex flex-col">
                    <span class="font-extrabold text-2xl tracking-tight leading-none text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-orange-400 to-orange-600 font-sans">Nak tool</span>
                    <span class="text-[10px] text-slate-500 uppercase tracking-widest font-semibold mt-0.5">Video Dubbing Platform</span>
                </div>
            </div>
            """)
            
            # Spacer pushes everything after it to the right
            gr.HTML('<div class="flex-grow"></div>')
            
            save_as_btn = gr.DownloadButton(
                "Save As 💾", 
                elem_id="nav-save-btn", 
                scale=0,
                elem_classes=[
                    "!bg-gradient-to-r", "!from-amber-500", "!to-orange-600",
                    "hover:!from-amber-400", "hover:!to-orange-500", "!text-white", 
                    "!rounded-full", "!px-4", "!py-2", "!text-xs", "!font-bold",
                    "!transition-all", "!duration-200", "!border-none",
                    "!min-width-0", "!h-auto", "!shadow-md", "!shadow-orange-500/10",
                    "hover:!shadow-orange-500/20", "!w-auto", "!flex-grow-0"
                ]
            )
            
            gr.HTML("""
            <div class="flex items-center gap-3 bg-white/5 border border-white/10 rounded-full p-1 pl-4 ml-auto shadow-inner w-fit">
                <span class="text-slate-400 text-xs font-mono font-medium">example2222@gmail.com</span>
                <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-500 to-orange-600 flex items-center justify-center text-sm font-bold text-white shadow shadow-orange-500/30 border border-white/10 cursor-pointer hover:scale-105 transition-transform duration-200">
                    👤
                </div>
            </div>
            """, scale=0)
            
        with gr.Row(elem_classes=["main-layout", "gap-6"]):
            # Left Column (scale=1)
            with gr.Column(scale=1, elem_classes=["flex", "flex-col", "gap-6"]):
                # Video Preview Card
                with gr.Group(elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!rounded-2xl", "!p-5", "!shadow-xl", "!flex", "!flex-col", "!gap-4"]):
                    gr.HTML('<div class="text-base font-bold text-white mb-2">Video Preview</div>')
                    video_player = gr.Video(label=None, interactive=False, show_label=False)
                    upload_btn = gr.UploadButton(
                        "Upload Source Video 📁", 
                        file_types=["video"], 
                        file_count="single", 
                        elem_classes=[
                            "!bg-gradient-to-r", "!from-amber-500", "!to-orange-600",
                            "hover:!from-amber-400", "hover:!to-orange-500", "!text-white", 
                            "!rounded-xl", "!py-2.5", "!text-sm", "!font-bold",
                            "!transition-all", "!duration-200", "!border-none",
                            "!w-full", "!shadow-md", "!shadow-orange-500/10",
                            "hover:!shadow-orange-500/20"
                        ]
                    )
                
                # Configurations Card
                with gr.Group(elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!rounded-2xl", "!p-5", "!shadow-xl", "!flex", "!flex-col", "!gap-4"]):
                    gr.HTML('<div class="text-base font-bold text-white mb-2">Configurations</div>')
                    with gr.Row(elem_classes=["gap-4"]):
                        whisper_model = gr.Dropdown(
                            label="Whisper Model", 
                            choices=["tiny", "base", "small", "medium", "large"], 
                            value="base"
                        )
                        source_lang = gr.Dropdown(
                            label="Source Lang", 
                            choices=["Auto Detect"] + list(LANGUAGES.keys()), 
                            value="Auto Detect"
                        )
                    with gr.Row(elem_classes=["gap-4"]):
                        target_lang = gr.Dropdown(
                            label="Target Lang", 
                            choices=list(LANGUAGES.keys()), 
                            value="Spanish"
                        )
                        target_voice = gr.Dropdown(
                            label="Target Voice", 
                            choices=[], 
                            value=None
                        )
                        
                    bg_volume = gr.Slider(
                        label="Background Music Volume", 
                        minimum=0.0, 
                        maximum=1.0, 
                        value=0.15, 
                        step=0.05
                    )
                    
                    btn_step1 = gr.Button(
                        "Step 1: Transcribe & Translate", 
                        interactive=False,
                        elem_classes=[
                            "!bg-gradient-to-r", "!from-amber-500", "!to-orange-600",
                            "hover:!from-amber-400", "hover:!to-orange-500", "!text-white", 
                            "!rounded-xl", "!py-2.5", "!text-sm", "!font-bold",
                            "!transition-all", "!duration-200", "!border-none",
                            "!w-full", "!shadow-md", "!shadow-orange-500/10",
                            "hover:!shadow-orange-500/20"
                        ]
                    )
                    
            # Right Column (scale=2)
            with gr.Column(scale=2, elem_classes=["flex", "flex-col", "gap-6"]):
                with gr.Group(elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!rounded-2xl", "!p-5", "!shadow-xl", "!flex", "!flex-col", "!gap-4", "!h-full"]):
                    gr.HTML("""
                    <div class="flex justify-between items-center mb-2">
                        <span class="text-base font-bold text-white">Translation Preview & Editor</span>
                        <span class="text-xs text-slate-500">Double click cells to edit translations</span>
                    </div>
                    """)
                    
                    status_output = gr.Textbox(
                        label=None, 
                        placeholder="Awaiting steps...", 
                        interactive=False, 
                        show_label=False,
                        lines=1
                    )
                    
                    transcription_df = gr.Dataframe(
                        headers=["ID", "Start", "End", "Orig", "Trans"],
                        datatype=["number", "number", "number", "str", "str"],
                        column_count=(5, "fixed"),
                        interactive=True,
                        show_label=False,
                        elem_classes=["!rounded-xl", "!border", "!border-white/5", "!overflow-hidden"]
                    )
                    
                    btn_step2 = gr.Button(
                        "Step 2: Generate Dubbed Video", 
                        interactive=False,
                        elem_classes=[
                            "!bg-gradient-to-r", "!from-blue-600", "!to-indigo-600",
                            "hover:!from-blue-500", "hover:!to-indigo-500", "!text-white", 
                            "!rounded-xl", "!py-2.5", "!text-sm", "!font-bold",
                            "!transition-all", "!duration-200", "!border-none",
                            "!w-full", "!shadow-md", "!shadow-blue-500/10",
                            "hover:!shadow-blue-500/20"
                        ]
                    )
                    
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
        
        # Handle navbar video upload and browser-compatibility conversion
        upload_btn.upload(
            fn=handle_video_upload,
            inputs=[upload_btn],
            outputs=[video_file_state, video_player, status_output, btn_step1]
        )
        
        # Wrapper to enable Step 2 button on transcription success
        def step1_wrapper(video, model, src, tgt):
            df, audio, tmp, status = step1_transcribe_and_translate(video, model, src, tgt)
            is_success = df is not None and len(df) > 0
            btn2_update = gr.Button(interactive=True) if is_success else gr.Button(interactive=False)
            return df, audio, tmp, status, btn2_update
            
        # Button triggers
        btn_step1.click(
            fn=step1_wrapper,
            inputs=[video_file_state, whisper_model, source_lang, target_lang],
            outputs=[transcription_df, extracted_audio_state, temp_dir_state, status_output, btn_step2]
        )
        
        def step2_wrapper(df, video_path, extracted_audio, temp_dir, target_voice, bg_volume):
            out_video, status = step2_generate_dubbed_video(
                df, video_path, extracted_audio, temp_dir, target_voice, bg_volume
            )
            return out_video, status, out_video
            
        btn_step2.click(
            fn=step2_wrapper,
            inputs=[transcription_df, video_file_state, extracted_audio_state, temp_dir_state, target_voice, bg_volume],
            outputs=[video_player, status_output, save_as_btn]
        )
        
    return demo, head_html
