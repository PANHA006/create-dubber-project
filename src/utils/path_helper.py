import os
import sys
import shutil
import tempfile
import urllib.request
import zipfile

def setup_ffmpeg_path():
    """Sets up a local ffmpeg.exe and ffprobe.exe wrapper in a temp folder and injects it into PATH."""
    try:
        import imageio_ffmpeg
        
        ffmpeg_real_exe = imageio_ffmpeg.get_ffmpeg_exe()
        temp_bin_dir = os.path.join(tempfile.gettempdir(), "ffmpeg_local_bin")
        os.makedirs(temp_bin_dir, exist_ok=True)
        
        # 1. Setup ffmpeg.exe
        local_ffmpeg_exe = os.path.join(temp_bin_dir, "ffmpeg.exe")
        if not os.path.exists(local_ffmpeg_exe):
            print(f"Creating local ffmpeg.exe alias: {local_ffmpeg_exe}")
            shutil.copyfile(ffmpeg_real_exe, local_ffmpeg_exe)
            
        # 2. Setup ffprobe.exe
        local_ffprobe_exe = os.path.join(temp_bin_dir, "ffprobe.exe")
        if not os.path.exists(local_ffprobe_exe):
            print("ffprobe.exe not found. Downloading static build from GitHub releases...")
            ffprobe_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip"
            zip_path = os.path.join(temp_bin_dir, "ffprobe.zip")
            try:
                req = urllib.request.Request(
                    ffprobe_url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_bin_dir)
                os.remove(zip_path)
                print("ffprobe.exe downloaded and extracted successfully!")
            except Exception as dl_err:
                print(f"WARNING: Could not download ffprobe.exe automatically: {dl_err}")
                print("Please ensure you have an active internet connection.")
                
        # 3. Inject temp directory into PATH
        if temp_bin_dir not in os.environ["PATH"]:
            os.environ["PATH"] = temp_bin_dir + os.pathsep + os.environ["PATH"]
        print(f"FFmpeg/FFprobe path injected: {temp_bin_dir}")
        return temp_bin_dir
    except Exception as e:
        print(f"WARNING: Failed to set up local FFmpeg/FFprobe wrapper: {e}")
        return None
