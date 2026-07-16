# AI Video Dubber & Translator

An extensible, production-ready AI video translation and dubbing application. It transcribes audio from an uploaded video using a local Whisper model, translates it into a target language, generates synthesized speech utilizing Microsoft Edge TTS, matches/aligns the voice speed with the timing of the original video segments, and merges the new dubbed audio track back into the video, keeping a customizable volume level of the original background music/sound effects.

---

## 🚀 Key Features

- **Keyless and Local:** No API keys are required for transcription, translation, or text-to-speech.
- **Whisper Word-Level Timestamps:** Refines segment start and end timings to align with the first and last spoken words, eliminating leading/trailing silences.
- **Precise Timing Formats:** Displays and allows editing of segment timings in `MM:SS.SS` formatted string representation (e.g., `02:53.20`).
- **Customizable AI Voice Delay:** Provides a UI slider to delay the dubbed voice by `X` seconds (defaulting to `0.20` seconds) to create a natural dubbing delay without altering speech speed.
- **Interactive Editing Table:** Transcribe and preview translations side-by-side in a spreadsheet-like data grid where you can refine, rewrite, or correct the translated texts before generating the dubbed audio.
- **Interactive Video Library:** Features an HTML scrollable list layout showing all dubbed videos in the `output/` directory with inline actions: **Rename (✏️)**, **Preview (👁️)**, **Download (💾)**, and **Delete (🗑️)**.
- **Flexible Script Import & Export:** Export subtitles with timing columns and import them back in `ID|START|END|TRANS` or `ID|START|END|ORIG|TRANS` pipe-delimited format.
- **Dynamic Proportional Watermarking:** Auto-detects input video resolution and scales the official Gradio brand logo proportional to `12%` width with `3%` margin.
- **Merge Short Segments limit:** Capped the merge limit to a maximum of 5 consecutive segments.
- **Decoupled Processing:** Solves Windows file locks by creating isolated video copies during compilation, allowing smooth streaming and web previewing.
- **Zero Global Requirements:** Static binary wrappers for FFmpeg and FFprobe are automatically resolved and downloaded to avoid system path installation requirements on Windows.

---

## 📂 Project Structure

```text
dubber-create-3/
├── src/
│   ├── config.py             # Global constants & target languages mapping
│   ├── core/                 # Core AI & processing engines
│   │   ├── transcriber.py     # Whisper audio extraction & transcription
│   │   ├── translator.py      # Translation API interfacing (deep-translator)
│   │   ├── synthesizer.py     # Edge TTS speech synthesis
│   │   └── pipeline.py        # Orchestration logic (Step 1 and Step 2 workflows)
│   ├── utils/                # Helper utilities
│   │   ├── path_helper.py     # Local ffmpeg/ffprobe installer & path injection
│   │   └── audio_helper.py    # Native PCM loader, speed alignment, and track mixing
│   └── ui/                   # Web interface layer
│       └── web_ui.py          # Gradio interface blocks and event triggers
├── output/                   # Default storage folder for dubbed videos
├── run.py                    # Main app runner script
├── requirements.txt          # Python package requirements
├── generate_test_video.py    # Utility to make a test video
└── README.md                 # Project documentation
```

---

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.8 or higher installed on your machine.
- Active internet connection (for downloading dependencies and Whisper models on first run).

### Installation Steps

1. **Clone or download** the repository to your local machine.
2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   ```
3. **Activate the virtual environment**:
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```
4. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

*Note: On Windows, static binary wrappers for `FFmpeg` and `FFprobe` will be downloaded and resolved automatically in a temporary folder upon first run. No manual path setup is required.*

---

## 💻 Running the Application

### 1. Start the Server
Run the main script from your terminal:
```bash
python run.py
```
*(If you are using a virtual environment on Windows, make sure it is activated or run `.venv\Scripts\python run.py`)*

### 2. Access the Web Interface
Once the server starts up, open your web browser and navigate to:
👉 **`http://127.0.0.1:7860`**

### 3. Step-by-Step Guide
1. **Upload your video** in the video player area.
2. **Configure your settings** on the left panel (such as Target Language, Font, AI Voice Delay, Background Music Volume, etc.).
3. Click **"Transcribe & Translate"** to run Step 1.
4. **Review / edit the results** in the interactive table showing the transcription, translated text, and exact start/end timings (`MM:SS.SS`).
5. Click **"Generate Dubbed Video"** to render the final dubbed track and subbed output video.

---

## 🧪 Helper Utilities

To generate an 8-second blue test video with an embedded English voice track for verification:
```bash
python generate_test_video.py
```
