import gradio as gr
import os
from src.config import LANGUAGES
from src.core.synthesizer import load_voices_sync
from src.core.pipeline import step1_a_transcribe, step1_b_translate, step2_generate_dubbed_video
from src.utils.audio_helper import make_video_browser_compatible

CUSTOM_CSS = """
body, .gradio-container, .gradio-container > div {
    background-color: #0b0f19 !important;
    color: #e2e8f0 !important;
    max-width: 100% !important;
    width: 100% !important;
    padding: 0px !important;
    margin: 0px !important;
}
.main-layout {
    padding-left: 24px !important;
    padding-right: 24px !important;
    padding-bottom: 24px !important;
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
/* When video is loaded, style the video player element to be rounded */
video {
    border-radius: 16px !important;
    overflow: hidden !important;
}
/* Hide the webcam and file upload source select buttons / toolbar */
.source-selection,
[data-testid="source-select"],
div[class*="source-select"],
span[class*="source-selection"],
button[aria-label="Upload file"],
button[aria-label="Record video from camera"] {
    display: none !important;
    visibility: hidden !important;
    height: 0px !important;
    padding: 0px !important;
    margin: 0px !important;
}
/* Force fixed height on the video player and video element to prevent layout shifts */
video,
div[class*="video-container"] {
    height: 320px !important;
    max-height: 320px !important;
    object-fit: contain !important;
}
/* Style the dataframe custom toolbar inside the header-row */
#dataframe-toolbar {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    gap: 8px !important;
    margin: 0 !important;
    padding: 0 !important;
    width: auto !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    order: -1 !important;
}
/* Style the dropdown to look like a small button menu */
#dataframe-toolbar div[class*="dropdown"] {
    background: #1e293b !important;
    border: none !important;
    border-radius: 8px !important;
    height: 32px !important;
    min-height: 32px !important;
    display: flex !important;
    align-items: center !important;
    transition: background 150ms !important;
}
#dataframe-toolbar div[class*="dropdown"]:hover {
    background: #334155 !important;
}
#dataframe-toolbar div[class*="dropdown"] select {
    padding: 4px 12px !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: #ffffff !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
    outline: none !important;
}
/* Style the import/export buttons to be aligned and matched */
#dataframe-toolbar button,
#dataframe-toolbar div.upload-button {
    height: 32px !important;
    min-height: 32px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
}
/* Ensure the native controls and header-row have the right height and styling */
#transcription-dataframe .header-row,
#transcription-dataframe div[class*="header-row"] {
    min-height: 40px !important;
    height: 40px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    padding-left: 8px !important;
    padding-right: 8px !important;
    border-bottom: 1px solid #1e293b !important;
    background-color: #0f172a !important;
}
/* Center the native copy/fullscreen buttons inside the controls wrapper */
#transcription-dataframe .controls,
#transcription-dataframe div[class*="controls"] {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    order: 1 !important;
}
#hidden-action-trigger {
    display: none !important;
}
/* Force text wrapping and character breaking for long strings (like Khmer text) in dataframe cells */
.gradio-container table td {
    white-space: normal !important;
    word-break: break-all !important;
    overflow-wrap: anywhere !important;
}
"""

def get_history_videos():
    import os
    output_dir = "output"
    if not os.path.exists(output_dir):
        return []
    
    files = [f for f in os.listdir(output_dir) if f.lower().endswith(".mp4")]
    # Sort files by modification time, newest first
    files = sorted(
        files, 
        key=lambda f: os.path.getmtime(os.path.join(output_dir, f)), 
        reverse=True
    )
    return files

def generate_history_html():
    import os
    videos = get_history_videos()
    if not videos:
        return """
        <div class="text-slate-500 text-xs text-center py-6 font-medium">
            No exported videos found.
        </div>
        """
        
    html = '<div class="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">'
    for vid in videos:
        import urllib.parse
        abs_file_path = os.path.abspath(os.path.join("output", vid))
        url_safe_path = urllib.parse.quote(abs_file_path.replace("\\", "/"), safe="")
        download_url = f"/gradio_api/file={url_safe_path}"
        base_name = vid[:-4] if vid.lower().endswith(".mp4") else vid
        # Escape single quotes in filenames to avoid JS errors
        js_safe_vid = vid.replace("'", "\\'")
        js_safe_base = base_name.replace("'", "\\'")
        
        html += f"""
        <div class="flex items-center justify-between p-2.5 bg-[#1e293b]/20 hover:bg-[#1e293b]/40 rounded-xl border border-white/5 transition-all duration-150 group">
            <div class="flex-grow min-w-0 mr-4 cursor-pointer" onclick="window.triggerAction('select', '{js_safe_vid}')" title="Click to play">
                <span class="text-xs font-semibold text-slate-200 truncate block hover:text-blue-400 transition-colors">{vid}</span>
            </div>
            <div class="flex items-center gap-2">
                <!-- Rename button -->
                <button onclick="const newName = prompt('Rename video:', '{js_safe_base}'); if(newName && newName.trim()) window.triggerAction('rename', '{js_safe_vid}|' + newName.trim());" 
                        class="transition-opacity opacity-70 hover:opacity-100 cursor-pointer" 
                        style="background: none !important; border: none !important; outline: none !important; box-shadow: none !important; padding: 4px !important; margin: 0 !important;" 
                        title="Rename Video">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" style="color: #f59e0b !important;" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
                </button>
                <!-- Eye (Preview) button -->
                <button onclick="window.triggerAction('select', '{js_safe_vid}')" 
                        class="transition-opacity opacity-70 hover:opacity-100 cursor-pointer" 
                        style="background: none !important; border: none !important; outline: none !important; box-shadow: none !important; padding: 4px !important; margin: 0 !important;" 
                        title="Preview Video">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10b981" style="color: #10b981 !important;" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                </button>
                <!-- Download button -->
                <a href="{download_url}" download="{vid}" 
                   class="transition-opacity opacity-70 hover:opacity-100 cursor-pointer" 
                   style="background: none !important; border: none !important; outline: none !important; box-shadow: none !important; padding: 4px !important; margin: 0 !important; display: inline-flex; align-items: center;" 
                   title="Download Video">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" style="color: #3b82f6 !important;" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                </a>
                <!-- Delete button -->
                <button onclick="if(confirm('Are you sure you want to delete this video?')) window.triggerAction('delete', '{js_safe_vid}')" 
                        class="transition-opacity opacity-70 hover:opacity-100 cursor-pointer" 
                        style="background: none !important; border: none !important; outline: none !important; box-shadow: none !important; padding: 4px !important; margin: 0 !important;" 
                        title="Delete Video">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#ef4444" style="color: #ef4444 !important;" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
        </div>
        """
    html += '</div>'
    return html

def handle_history_action(action_str):
    print(f"=== handle_history_action called with action_str: '{action_str}' ===")
    if not action_str:
        return gr.HTML(), None, "", ""
        
    parts = action_str.split(":", 1)
    if len(parts) < 2:
        return gr.HTML(), None, "", ""
        
    action_type, payload = parts[0], parts[1]
    print(f"Parsed action_type: '{action_type}', payload: '{payload}'")
    import os
    output_dir = "output"
    
    html_update = gr.HTML()
    player_update = None
    status_log = ""
    
    if action_type == "select":
        try:
            file_path = os.path.join(output_dir, payload)
            print(f"Target file_path: '{file_path}'")
            exists = os.path.exists(file_path)
            print(f"File exists: {exists}")
            if exists:
                import shutil
                import tempfile
                temp_preview = os.path.join(tempfile.gettempdir(), f"preview_{payload}")
                print(f"Copying to temp preview path: '{temp_preview}'")
                shutil.copy2(file_path, temp_preview)
                player_update = os.path.abspath(temp_preview)
                status_log = f"Loaded video: {payload}"
                print(f"Setting player_update to: '{player_update}'")
            else:
                status_log = f"Error: Video file not found: {payload}"
                print(status_log)
                raise gr.Error(status_log)
        except Exception as e:
            status_log = f"Error loading video: {str(e)}"
            print(status_log)
            raise gr.Error(status_log)
            
    elif action_type == "delete":
        file_path = os.path.join(output_dir, payload)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                status_log = f"Deleted video: {payload}"
            except Exception as e:
                status_log = f"Error deleting file: {e}"
                raise gr.Error(status_log)
        else:
            status_log = f"Error: File '{payload}' not found."
            raise gr.Error(status_log)
        html_update = generate_history_html()
        
    elif action_type == "rename":
        sub_parts = payload.split("|", 1)
        if len(sub_parts) == 2:
            old_name, new_name = sub_parts[0], sub_parts[1].strip()
            if new_name:
                if not new_name.lower().endswith(".mp4"):
                    new_name += ".mp4"
                new_name = os.path.basename(new_name)
                
                old_path = os.path.join(output_dir, old_name)
                new_path = os.path.join(output_dir, new_name)
                
                if os.path.exists(old_path):
                    if os.path.exists(new_path):
                        status_log = f"Error: '{new_name}' already exists."
                        raise gr.Error(status_log)
                    else:
                        try:
                            os.rename(old_path, new_path)
                            status_log = f"Renamed '{old_name}' to '{new_name}'"
                        except Exception as e:
                            status_log = f"Error renaming file: {e}"
                            raise gr.Error(status_log)
                else:
                    status_log = f"Error: file '{old_name}' not found."
                    raise gr.Error(status_log)
        html_update = generate_history_html()
        
    return html_update, player_update, status_log, ""

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
        return None, None, "No video uploaded.", gr.Button(interactive=False), gr.Button(interactive=False)
    try:
        compatible_path = make_video_browser_compatible(raw_path)
        return compatible_path, compatible_path, f"Video uploaded successfully: {os.path.basename(compatible_path)}", gr.Button(interactive=True), gr.Button(interactive=False)
    except Exception as e:
        return None, None, f"Error processing uploaded video: {str(e)}", gr.Button(interactive=False), gr.Button(interactive=False)

def update_voices_dropdown(target_lang):
    voices = load_voices_sync()
    lang_info = LANGUAGES.get(target_lang)
    if not lang_info:
        return gr.Dropdown(choices=[], value=None, allow_custom_value=True)
    
    prefix = lang_info["tts_prefix"]
    filtered_voices = [
        v["ShortName"] for v in voices 
        if v["ShortName"].lower().startswith(prefix.lower())
    ]
    filtered_voices = sorted(filtered_voices)
    
    default_val = filtered_voices[0] if filtered_voices else None
    return gr.Dropdown(choices=filtered_voices, value=default_val, allow_custom_value=True)

def export_script_fn(df):
    if df is None or df.empty:
        return None
        
    import tempfile
    import os
    
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, "subtitle_original.txt")
    lines = ["ID|START|END|ORIG"]
    for _, row in df.iterrows():
        try:
            row_id = int(row["ID"])
        except Exception:
            row_id = row["ID"]
        start = row["Start"]
        end = row["End"]
        orig = row["Orig"]
        lines.append(f"{row_id}|{start}|{end}|{orig}")
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return file_path

def import_script_fn(file_obj, current_df):
    if file_obj is None:
        return current_df, "Please select a file to import.", gr.Button(interactive=False)
        
    import pandas as pd
    file_path = getattr(file_obj, "name", None) or getattr(file_obj, "path", None) or file_obj
    if not file_path:
        return current_df, "Invalid file path.", gr.Button(interactive=False)
        
    if not str(file_path).lower().endswith(".txt"):
        return current_df, "Invalid subtitle script format.\nExpected:\nID|START|END|TRANS  or  ID|START|END|ORIG|TRANS", gr.Button(interactive=False)
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return current_df, "Invalid subtitle script format.\nExpected:\nID|START|END|TRANS  or  ID|START|END|ORIG|TRANS", gr.Button(interactive=False)
    except Exception as e:
        return current_df, f"Error reading file: {e}", gr.Button(interactive=False)
        
    lines = [line.strip() for line in content.replace("\r\n", "\n").split("\n") if line.strip()]
    if not lines:
        return current_df, "File is empty.", gr.Button(interactive=False)
        
    header = lines[0].strip()
    if header == "ID|START|END|TRANS":
        is_orig_trans = False
    elif header == "ID|START|END|ORIG|TRANS":
        is_orig_trans = True
    else:
        return current_df, "Invalid subtitle script format.\nExpected:\nID|START|END|TRANS  or  ID|START|END|ORIG|TRANS", gr.Button(interactive=False)
        
    if current_df is None or current_df.empty:
        return current_df, "No transcription data in the table to update. Please perform Step 1 first.", gr.Button(interactive=False)
        
    new_df = current_df.copy()
    parsed_updates = {}
    
    for line in lines[1:]:
        parts = line.split("|")
        expected_min = 5 if is_orig_trans else 4
        if len(parts) < expected_min:
            return current_df, "Invalid subtitle script format.\nExpected:\nID|START|END|TRANS  or  ID|START|END|ORIG|TRANS", gr.Button(interactive=False)
            
        try:
            row_id = int(parts[0])
            if is_orig_trans:
                trans_text = "|".join(parts[4:])
            else:
                trans_text = "|".join(parts[3:])
        except (ValueError, IndexError):
            return current_df, "Invalid subtitle script format.\nExpected:\nID|START|END|TRANS  or  ID|START|END|ORIG|TRANS", gr.Button(interactive=False)
            
        parsed_updates[row_id] = trans_text
        
    updated_count = 0
    new_df["ID"] = new_df["ID"].astype(int)
    for row_id, trans_text in parsed_updates.items():
        matching_indices = new_df.index[new_df["ID"] == row_id].tolist()
        if matching_indices:
            idx = matching_indices[0]
            new_df.at[idx, "Trans"] = trans_text
            updated_count += 1
            
    status_msg = "Script imported successfully."
    return new_df, status_msg, gr.Button(interactive=True)

def build_ui():
    head_html = """
    <title>AI Video Dubber</title>
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
    with gr.Blocks(title="AI Video Dubber", fill_width=True) as demo:
        # State management variables
        extracted_audio_state = gr.State("")
        temp_dir_state = gr.State("")
        video_file_state = gr.State("")
        
        # Navigation Bar Row
        with gr.Row(elem_id="navbar", elem_classes=["flex", "items-center", "gap-4", "p-3", "px-6", "bg-[#0f172a]/80", "backdrop-blur-md", "border-b", "border-white/5", "w-full", "shadow-xl", "shadow-black/20"]):
            gr.HTML("""
            <div class="flex items-center gap-3 cursor-pointer hover:opacity-95 transition-opacity">
                <div class="flex items-center justify-center w-10 h-10 rounded-xl bg-white/5 border border-white/10 shadow-inner">
                    <svg width="24" height="24" viewBox="0 0 576 576" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M287.5 229L86 344.5L287.5 460L489 344.5L287.5 229Z" stroke="url(#logo-gradient-1)" stroke-width="59" stroke-linejoin="round"/>
                        <path d="M287.5 116L86 231.5L287.5 347L489 231.5L287.5 116Z" stroke="url(#logo-gradient-2)" stroke-width="59" stroke-linejoin="round"/>
                        <path d="M86 344L288 229" stroke="url(#logo-gradient-3)" stroke-width="59" stroke-linejoin="bevel"/>
                        <defs>
                            <linearGradient id="logo-gradient-1" x1="60" y1="344" x2="429.5" y2="344" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#fbbf24"/>
                                <stop offset="1" stop-color="#ea580c"/>
                            </linearGradient>
                            <linearGradient id="logo-gradient-2" x1="513.5" y1="231" x2="143.5" y2="231" gradientUnits="userSpaceOnUse">
                                <stop stop-color="#fbbf24"/>
                                <stop offset="1" stop-color="#ea580c"/>
                            </linearGradient>
                            <linearGradient id="logo-gradient-3" x1="60" y1="344" x2="428.987" y2="341.811" gradientUnits="userSpaceOnUse">
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
                visible=False,
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
            # Left Column (scale=2)
            with gr.Column(scale=2, elem_classes=["flex", "flex-col", "gap-6"]):
                # Video Preview Card (full screen inside card, no padding/margin)
                with gr.Group(elem_classes=["bg-[#0f172a]/40", "border", "border-dashed", "border-white/5", "p-0", "m-0", "shadow-xl", "overflow-hidden"]):
                    video_player = gr.Video(label=None, interactive=True, show_label=False, elem_id="video-preview")
                
                # Configurations Card
                with gr.Group(elem_id="configurations-card", elem_classes=["!bg-[#0f172a]/40", "!border", "!border-dashed", "!border-white/5", "!p-0", "!m-0", "!shadow-xl", "!flex", "!flex-col", "!gap-2"]):
                    with gr.Row(elem_classes=["gap-2"]):
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
                        target_lang = gr.Dropdown(
                            label="Target Lang", 
                            choices=list(LANGUAGES.keys()), 
                            value="Khmer"
                        )
                    with gr.Row(elem_classes=["gap-2"]):
                        target_voice = gr.Dropdown(
                            label="Target Voice", 
                            choices=[], 
                            value=None,
                            allow_custom_value=True
                        )
                        sub_font = gr.Dropdown(
                            choices=["Arial", "Calibri", "Tahoma", "Courier New", "Verdana", "Khmer UI", "DaunPenh", "Khmer OS Battambang", "Battambang"], 
                            value="Battambang", 
                            label="Subtitle Font"
                        )
                        sub_align = gr.Dropdown(
                            choices=["Bottom", "Top", "Middle"],
                            value="Bottom",
                            label="Subtitle Position"
                        )
                        
                    with gr.Row(elem_classes=["!gap-2"]):
                        processing_mode = gr.Radio(
                            choices=["Dubbing Only", "Subtitles Only", "Dubbing + Subtitles"], 
                            value="Dubbing Only", 
                            show_label=False
                        )
                    with gr.Row(elem_classes=["!gap-2"]):
                        sub_font_size = gr.Slider(
                            minimum=10, 
                            maximum=60, 
                            step=2, 
                            value=20, 
                            label="Subtitle Font Size"
                        )
                    with gr.Row(elem_classes=["!gap-2"]):
                        bg_volume = gr.Slider(
                            label="Background Music", 
                            minimum=0.0, 
                            maximum=1.0, 
                            value=0.15, 
                            step=0.05
                        )
                    with gr.Row(elem_classes=["!gap-2"]):
                        ai_delay = gr.Slider(
                            label="AI Voice Delay (seconds)", 
                            minimum=0.0, 
                            maximum=2.0, 
                            value=0.20, 
                            step=0.05
                        )
                    with gr.Column(elem_classes=["!gap-2"]):
                        remove_spoken_voice = gr.Checkbox(
                            label="Remove Original Spoken Voice", 
                            value=True
                        )
                        sub_bg_box = gr.Checkbox(
                            label="Hide Old Subtitles (Black Background)", 
                            value=True
                        )
                        mirror_video = gr.Checkbox(
                            label="Mirror Video (Flip Horizontal)", 
                            value=True
                        )
                        merge_segments = gr.Checkbox(
                            label="Merge Short Segments", 
                            value=False
                        )
                    
                    with gr.Row(elem_classes=["!py-3", "!px-3", "!gap-2"]):
                        btn_transcribe = gr.Button(
                            "Transcript", 
                            interactive=False,
                            elem_classes=[
                                "!bg-gradient-to-r", "!from-amber-500", "!to-amber-600",
                                "hover:!from-amber-400", "hover:!to-amber-500", "!text-white", 
                                "!rounded-xl", "!py-2.5", "!text-sm", "!font-bold",
                                "!transition-all", "!duration-200", "!border-none",
                                "!w-full", "!shadow-md", "!shadow-orange-500/10",
                                "hover:!shadow-orange-500/20"
                            ]
                        )
                        btn_translate = gr.Button(
                            "Translate", 
                            interactive=False,
                            elem_classes=[
                                "!bg-gradient-to-r", "!from-orange-500", "!to-orange-600",
                                "hover:!from-orange-400", "hover:!to-orange-500", "!text-white", 
                                "!rounded-xl", "!py-2.5", "!text-sm", "!font-bold",
                                "!transition-all", "!duration-200", "!border-none",
                                "!w-full", "!shadow-md", "!shadow-orange-500/10",
                                "hover:!shadow-orange-500/20"
                            ]
                        )
                    
            # Right Column (scale=5)
            with gr.Column(scale=5, elem_classes=["flex", "flex-col", "gap-2"]):
                with gr.Group(elem_id="dataframe-group", elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!p-0", "!m-0","!gap-2", "!shadow-xl", "!flex", "!flex-col", "!h-full"]):
                    # Toolbar Row for Import and Export Script
                    with gr.Row(elem_id="dataframe-toolbar", elem_classes=["!p-0", "!m-0", "!gap-2"]):
                        import_script_btn = gr.UploadButton(
                            "📥 Import", 
                            file_types=[".txt"], 
                            elem_classes=[
                                "!bg-[#1e293b]", "hover:!bg-[#334155]", "!text-white", 
                                "!rounded-lg", "!py-1.5", "!px-3", "!text-xs", "!font-semibold",
                                "!transition-all", "!duration-150", "!border-none", "!w-auto"
                            ],
                            scale=0
                        )
                        
                        export_script_btn = gr.DownloadButton(
                            "📤 Export", 
                            elem_classes=[
                                "!bg-[#1e293b]", "hover:!bg-[#334155]", "!text-white", 
                                "!rounded-lg", "!py-1.5", "!px-3", "!text-xs", "!font-semibold",
                                "!transition-all", "!duration-150", "!border-none", "!w-auto"
                            ],
                            scale=0
                        )
                    
                    transcription_df = gr.Dataframe(
                        headers=["ID", "Start", "End", "Orig", "Trans"],
                        datatype=["number", "str", "str", "str", "str"],
                        column_count=(5, "fixed"),
                        interactive=True,
                        show_label=False,
                        elem_classes=["!border-none", "!m-0", "!p-0", "!overflow-auto"],
                        elem_id="transcription-dataframe"
                    )
                    
                    with gr.Row(elem_classes=["!px-4", "!py-4"]):
                        btn_step2 = gr.Button(
                            "Generate Dubbed Video", 
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
                
                # New group below for log and state
                with gr.Group(elem_id="log-state-group", visible=False, elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!p-0", "!m-0", "!shadow-xl", "!flex", "!flex-col"]):
                    gr.HTML("""
                    <div class="flex items-center px-3 py-2 border-b border-white/5">
                        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">Log & State</span>
                    </div>
                    """)
                    status_output = gr.Textbox(
                        label=None, 
                        placeholder="Awaiting steps...", 
                        interactive=False, 
                        show_label=False,
                        lines=3,
                        max_lines=6,
                        elem_classes=["!border-none", "!bg-transparent", "!m-0", "!p-2", "!font-mono", "!text-xs"],
                        elem_id="log-terminal"
                    )
                
                # Video Library & Export History Group (List Layout)
                with gr.Group(elem_id="history-group", elem_classes=["!bg-[#0f172a]/40", "!border", "!border-white/5", "!p-0", "!m-0", "!shadow-xl", "!flex", "!flex-col", "!gap-2"]):
                    gr.HTML("""
                    <div class="flex items-center pb-2 border-b border-white/5">
                        <span class="text-xs font-bold text-slate-400 uppercase tracking-wider font-sans">Export History & Video Library</span>
                    </div>
                    """)
                    
                    history_html_container = gr.HTML(
                        value=generate_history_html(),
                        elem_id="history-list-container"
                    )
                    
                    hidden_action_trigger = gr.Textbox(
                        visible=True,
                        elem_id="hidden-action-trigger"
                    )
                    
        # Language change triggers voice dropdown population
        target_lang.change(
            fn=update_voices_dropdown, 
            inputs=[target_lang], 
            outputs=[target_voice]
        )
        
        # Initialize voice choices on load and move script toolbar DOM inside header-row
        def load_initial_data():
            voices_drop = update_voices_dropdown("Khmer")
            return voices_drop, generate_history_html()

        demo.load(
            fn=load_initial_data,
            outputs=[target_voice, history_html_container],
            js="""
            () => {
                window.triggerAction = (actionName, payload) => {
                    const el = document.getElementById("hidden-action-trigger");
                    if (el) {
                        const inputEl = el.querySelector("input, textarea");
                        if (inputEl) {
                            inputEl.value = actionName + ":" + payload;
                            inputEl.dispatchEvent(new Event("input", { bubbles: true }));
                            inputEl.dispatchEvent(new Event("change", { bubbles: true }));
                        }
                    }
                };

                const checkAndMove = () => {
                    const toolbar = document.getElementById("dataframe-toolbar");
                    const dataframe = document.getElementById("transcription-dataframe");
                    if (toolbar && dataframe) {
                        const headerRow = dataframe.querySelector(".header-row");
                        if (headerRow) {
                            const controls = headerRow.querySelector(".controls");
                            if (controls) {
                                headerRow.insertBefore(toolbar, controls);
                            } else {
                                headerRow.appendChild(toolbar);
                            }
                            return true;
                        }
                    }
                    return false;
                };
                const interval = setInterval(() => {
                    if (checkAndMove()) {
                        clearInterval(interval);
                    }
                }, 100);
                setTimeout(() => clearInterval(interval), 10000);
            }
            """
        )
        
        # Handle video upload directly via the video player dropzone
        video_player.upload(
            fn=handle_video_upload,
            inputs=[video_player],
            outputs=[video_file_state, video_player, status_output, btn_transcribe, btn_translate]
        )
        
        # Handle clearing the video to reset UI state
        def handle_video_clear():
            return None, None, "Video removed.", gr.Button(interactive=False), gr.Button(interactive=False)
            
        video_player.clear(
            fn=handle_video_clear,
            outputs=[video_file_state, video_player, status_output, btn_transcribe, btn_translate]
        )
        
        # Transcription & Translation split wrappers
        def transcribe_wrapper(video, model, mirror, merge):
            df, audio, tmp, status, processed_video = step1_a_transcribe(video, model, mirror, merge)
            is_success = df is not None and len(df) > 0
            btn_translate_update = gr.Button(interactive=True) if is_success else gr.Button(interactive=False)
            return df, audio, tmp, status, btn_translate_update, processed_video, processed_video

        def translate_wrapper(df, source, target):
            # df contains current UI table values (including any user corrections!)
            new_df, status = step1_b_translate(df, source, target)
            is_success = new_df is not None and len(new_df) > 0
            btn_step2_update = gr.Button(interactive=True) if is_success else gr.Button(interactive=False)
            return new_df, status, btn_step2_update
            
        # Button triggers
        btn_transcribe.click(
            fn=transcribe_wrapper,
            inputs=[video_file_state, whisper_model, mirror_video, merge_segments],
            outputs=[transcription_df, extracted_audio_state, temp_dir_state, status_output, btn_translate, video_file_state, video_player]
        )

        btn_translate.click(
            fn=translate_wrapper,
            inputs=[transcription_df, source_lang, target_lang],
            outputs=[transcription_df, status_output, btn_step2]
        )
        
        def step2_wrapper(df, video_path, extracted_audio, temp_dir, target_voice, bg_volume, ai_delay_val, remove_voice, proc_mode, font, font_size, align, bg_box):
            out_video, status = step2_generate_dubbed_video(
                df, video_path, extracted_audio, temp_dir, target_voice, bg_volume, ai_delay_val, remove_voice, proc_mode, font, font_size, align, bg_box
            )
            html_val = generate_history_html()
            return out_video, status, html_val
            
        btn_step2.click(
            fn=step2_wrapper,
            inputs=[transcription_df, video_file_state, extracted_audio_state, temp_dir_state, target_voice, bg_volume, ai_delay, remove_spoken_voice, processing_mode, sub_font, sub_font_size, sub_align, sub_bg_box],
            outputs=[video_player, status_output, history_html_container]
        )
        
        # Import and Export Script event handlers
        import_script_btn.upload(
            fn=import_script_fn,
            inputs=[import_script_btn, transcription_df],
            outputs=[transcription_df, status_output, btn_step2]
        )
        
        export_script_btn.click(
            fn=lambda df: (export_script_fn(df), "Script exported successfully."),
            inputs=[transcription_df],
            outputs=[export_script_btn, status_output]
        )
        
        # Hidden action trigger event handler
        hidden_action_trigger.change(
            fn=handle_history_action,
            inputs=[hidden_action_trigger],
            outputs=[history_html_container, video_player, status_output, hidden_action_trigger]
        )
        
    return demo, head_html
