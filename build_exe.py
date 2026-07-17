import subprocess
import sys
import os

print("Starting PyInstaller compilation process...")

cmd = [
    ".venv\\Scripts\\pyinstaller",
    "--noconfirm",
    "--onedir",
    "--console",
    "--name", "DubberAI",
    "--add-data", "resources;resources",
    "--collect-all", "gradio",
    "--collect-all", "safehttpx",
    "--collect-all", "groovy",
    "--collect-all", "whisper",
    "--collect-all", "deep_translator",
    "--collect-all", "edge_tts",
    "--collect-all", "pydub",
    "--collect-all", "pandas",
    "--collect-all", "starlette",
    "--collect-all", "fastapi",
    "run.py"
]

print("Executing command:", " ".join(cmd))
result = subprocess.run(cmd, capture_output=False, text=True)

if result.returncode == 0:
    print("\nSUCCESS: Compilation completed successfully!")
    print("You can find your executable inside the 'dist/DubberAI' folder.")
else:
    print(f"\nFAILURE: PyInstaller exited with code {result.returncode}")
    sys.exit(result.returncode)
