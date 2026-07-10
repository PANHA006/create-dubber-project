import asyncio
import os
import subprocess
import imageio_ffmpeg
import edge_tts

async def main():
    print("Generating sample speech audio...")
    text = "Hello! Welcome to the AI video dubbing tutorial. We are testing the voice translation and alignment engine."
    voice = "en-US-GuyNeural"
    audio_path = "sample_speech.mp3"
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(audio_path)
    print("Speech audio generated.")
    
    print("Combining into a sample MP4 video using FFmpeg...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    video_path = "sample_video.mp4"
    
    # We will generate an 8-second blue video with the speech audio track
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=640x480:d=8",
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-shortest",
        video_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"Sample video successfully created: {os.path.abspath(video_path)}")
    
    # Clean up temp mp3
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    asyncio.run(main())
