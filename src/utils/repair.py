import os
import sys
import shutil
import subprocess
import re
import urllib.request
import zipfile
import json
from datetime import datetime
from pathlib import Path

class MediaRepairCore:
    """Core logic for Snapchat media restoration."""
    MP4_SIG = b'ftyp'
    JPEG_SIG = b'\xff\xd8\xff'

    def __init__(self, ffmpeg_path="ffmpeg"):
        self.ffmpeg_exe = ffmpeg_path

    def parse_date(self, filename):
        """Extracts timestamp from Snapchat filename format YYYY-MM-DD_HH-MM-SS."""
        match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
        if match:
            try:
                dt = datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
                return dt.timestamp()
            except ValueError:
                return None
        return None

    def fix_video(self, in_p, out_p):
        """Transcodes to high-compatibility H.264."""
        cmd = [
            self.ffmpeg_exe, "-y", "-i", str(in_p),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k", 
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out_p)
        ]
        return subprocess.run(cmd, capture_output=True).returncode == 0

    def extract_jpg(self, in_p, out_p):
        """Extracts valid JPEG data from a file with a corrupted header."""
        with open(in_p, 'rb') as f:
            data = f.read()
        soi = data.find(self.JPEG_SIG)
        eoi = data.rfind(b'\xff\xd9')
        if soi != -1 and eoi > soi:
            with open(out_p, 'wb') as f:
                f.write(data[soi : eoi + 2])
            return True
        return False

class EnvironmentManager:
    """Handles automatic FFmpeg installation and PATH configuration."""
    @staticmethod
    def get_ffmpeg():
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        
        # Check local bin directory relative to the src folder
        # Structure: src/utils/repair.py -> src/bin/
        bin_dir = Path(__file__).parent.parent / "bin"
        ffmpeg_exe = bin_dir / ("ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
        
        if ffmpeg_exe.exists():
            return str(ffmpeg_exe)

        print("FFmpeg not found. Downloading portable binaries...")
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        if os.name == 'nt':
            url = "https://github.com/GyanD/codexffmpeg/releases/download/7.0.1/ffmpeg-7.0.1-full_build.zip"
            zip_path = bin_dir / "ffmpeg.zip"
            urllib.request.urlretrieve(url, zip_path)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("ffmpeg.exe"):
                        with open(ffmpeg_exe, "wb") as f:
                            f.write(zip_ref.read(file))
            zip_path.unlink()
            return str(ffmpeg_exe)
        else:
            # For Linux/macOS, we rely on system package managers
            return "ffmpeg"