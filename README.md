# AI Video Dubber & Translator

An extensible, production-ready AI video translation and dubbing application. It transcribes audio from an uploaded video using a local Whisper model, translates it into a target language, generates synthesized speech utilizing Microsoft Edge TTS, matches/aligns the voice speed with the timing of the original video segments, and merges the new dubbed audio track back into the video, keeping a customizable volume level of the original background music/sound effects.

## Features
- **Keyless and Local:** No API keys are required for transcription, translation, or text-to-speech.
- **Interactive Editing:** Transcribe and preview translations side-by-side in a spreadsheet-like data grid where you can refine, rewrite, or correct the translated texts before generating the dubbed audio.
- **Zero Global Requirements:** Static binary wrappers for FFmpeg and FFprobe are automatically resolved and downloaded to avoid system path installation requirements on Windows.
- **Whisper Word-Level Timestamps:** Refines segment start and end timings to align with the first and last spoken words, eliminating leading/trailing silences.
- **Precise Timing Formats:** Displays and allows editing of segment timings in `MM:SS.SS` formatted string representation (e.g. `02:53.20`).
- **Customizable AI Voice Delay:** Provides a UI slider to delay the dubbed voice by `X` seconds (defaulting to `0.20` seconds) to create a natural dubbing delay without altering speech speed.
- **Interactive Video Library:** Features an HTML scrollable list layout showing all dubbed videos in the `output/` directory with inline actions: **Rename (✏️)**, **Preview (👁️)**, **Download (💾)**, and **Delete (🗑️)**.
- **Flexible Script Import & Export:** Export subtitles with timing columns and import them back in `ID|START|END|TRANS` or `ID|START|END|ORIG|TRANS` pipe-delimited format.
- **Dynamic Proportional Watermarking:** Auto-detects input video resolution and scales the official Gradio brand logo proportional to `12%` width with `3%` margin.
- **Merge Short Segments limit:** Capped the merge limit to a maximum of 5 consecutive segments.
- **Decoupled Processing:** Solves Windows file locks by creating isolated video copies during compilation, allowing smooth streaming and web previewing.

## Project Structure
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

## Setup and Installation

1. Clone or download the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Web App
Start the Gradio interface:
```bash
python run.py
```
Open your browser and navigate to **`http://127.0.0.1:7860`**.

## Generating a Test Video
To create an 8-second blue test video with speech audio track for quick verification:
```bash
python generate_test_video.py
```
