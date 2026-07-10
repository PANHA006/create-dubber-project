import os
import tempfile
import math
import shutil
import subprocess
import imageio_ffmpeg
from pydub import AudioSegment

def load_audio_segment_natively(file_path):
    """Bypasses pydub's dependency on ffprobe by decoding audio to raw PCM in memory using ffmpeg."""
    temp_pcm = file_path + ".raw"
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", file_path,
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        temp_pcm
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    with open(temp_pcm, "rb") as f:
        pcm_data = f.read()
        
    try:
        os.remove(temp_pcm)
    except Exception as e:
        print(f"Warning: could not remove temp raw PCM file: {e}")
        
    return AudioSegment(
        data=pcm_data,
        sample_width=2,
        frame_rate=16000,
        channels=1
    )

def get_audio_duration(file_path):
    audio = load_audio_segment_natively(file_path)
    return len(audio) / 1000.0

def adjust_audio_speed(input_path, output_path, speed):
    if abs(speed - 1.0) < 0.05:
        shutil.copyfile(input_path, output_path)
        return
    
    filters = []
    temp_speed = speed
    if temp_speed > 3.0:
        temp_speed = 3.0
    if temp_speed < 0.5:
        temp_speed = 0.5
        
    while temp_speed > 2.0:
        filters.append("atempo=2.0")
        temp_speed /= 2.0
    while temp_speed < 0.5:
        filters.append("atempo=0.5")
        temp_speed /= 0.5
    filters.append(f"atempo={temp_speed:.2f}")
    filter_str = ",".join(filters)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", input_path,
        "-filter:a", filter_str,
        "-vn",
        output_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def mix_audio_tracks(original_audio_path, dubbed_audio_path, background_volume, output_mixed_path):
    original_audio = load_audio_segment_natively(original_audio_path)
    dubbed_audio = load_audio_segment_natively(dubbed_audio_path)
    
    if background_volume > 0.0:
        vol = max(background_volume, 0.0001)
        db_reduction = 20 * math.log10(vol)
        reduced_bg = original_audio.apply_gain(db_reduction)
        mixed_audio = reduced_bg.overlay(dubbed_audio)
    else:
        mixed_audio = dubbed_audio
        
    mixed_audio.export(output_mixed_path, format="wav")

def is_video_browser_compatible(video_path):
    """Checks if the video has a browser-compatible container (.mp4) and codec (h264/vp9/av1)."""
    if not video_path:
        return False
        
    _, ext = os.path.splitext(video_path.lower())
    if ext != ".mp4":
        return False
        
    try:
        temp_bin_dir = os.path.join(tempfile.gettempdir(), "ffmpeg_local_bin")
        ffprobe_exe = os.path.join(temp_bin_dir, "ffprobe.exe")
        if not os.path.exists(ffprobe_exe):
            return False
            
        cmd = [
            ffprobe_exe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        codec = result.stdout.strip().lower()
        return codec in ["h264", "vp9", "av1"]
    except Exception as e:
        print(f"Warning: could not probe video codec: {e}")
        return False

def make_video_browser_compatible(video_path):
    """If the video is not browser-compatible, transcodes it to standard H.264/AAC MP4."""
    if not video_path:
        return None
        
    # If already compatible, bypass transcoding entirely
    if is_video_browser_compatible(video_path):
        print(f"Video is already browser-compatible: {video_path}")
        return video_path
        
    temp_dir = os.path.dirname(video_path)
    output_path = os.path.join(temp_dir, f"playable_{os.path.basename(video_path)}")
    if not output_path.lower().endswith(".mp4"):
        output_path = os.path.splitext(output_path)[0] + ".mp4"
        
    print(f"Transcoding uploaded video to browser-compatible H.264/AAC format: {output_path}")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-preset", "fast",
        "-crf", "23",
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path
    except Exception as e:
        print(f"Error converting video: {e}")
        return video_path
