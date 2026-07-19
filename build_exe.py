import sys
import os
import PyInstaller.__main__

print("Starting PyInstaller compilation process...")

cmd = [
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

print("Executing PyInstaller programmatically with args:", cmd)
try:
    PyInstaller.__main__.run(cmd)
    print("\nSUCCESS: Compilation completed successfully!")
    print("You can find your executable inside the 'dist/DubberAI' folder.")
except Exception as e:
    print(f"\nFAILURE: PyInstaller program raised exception: {e}")
    sys.exit(1)
