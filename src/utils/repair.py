import os
import shutil
import subprocess
import re
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

class MediaRepairCore:
    """Core logic for Snapchat media restoration and type correction."""
    MP4_SIG = b'ftyp'
    JPEG_SIG = b'\xff\xd8\xff'

    def __init__(self, ffmpeg_path="ffmpeg"):
        self.ffmpeg_exe = ffmpeg_path
        self.ffprobe_exe = str(Path(ffmpeg_path).parent / "ffprobe.exe") if os.name == 'nt' else "ffprobe"

    def check_media_type(self, file_p):
        """
        Aggressive stream analysis. Even if 'moov atom' is missing, 
        we check if any video packets exist.
        """
        # Optimized command to find ANY video stream, ignoring most container errors
        cmd = [
            self.ffprobe_exe, "-v", "error", 
            "-select_streams", "v", 
            "-show_entries", "stream=codec_name", 
            "-of", "csv=p=0", str(file_p)
        ]
        try:
            # We use a timeout to prevent hanging on severely corrupt files
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            output = result.stdout.strip().lower()
            
            # If ffprobe finds any video codec (h264, etc), it is a video
            if output:
                return 'video'
            
            # Secondary check: If first probe fails, check for audio streams
            cmd_audio = [
                self.ffprobe_exe, "-v", "error", 
                "-select_streams", "a", 
                "-show_entries", "stream=codec_name", 
                "-of", "csv=p=0", str(file_p)
            ]
            result_audio = subprocess.run(cmd_audio, capture_output=True, text=True, timeout=5,
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result_audio.stdout.strip():
                return 'audio'
        except Exception:
            pass
        return 'unknown'
    
    def fix_video(self, in_p, out_p):
        """
        Uses ffmpeg to 'transmix' and repair the container.
        Adds '-find_stream_info' to handle files with missing moov atoms.
        """
        cmd = [
            self.ffmpeg_exe, "-y", 
            "-err_detect", "ignore_err", # Ignore minor bitstream errors
            "-i", str(in_p),
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-c:a", "aac", "-b:a", "128k", 
            "-pix_fmt", "yuv420p", 
            "-movflags", "+faststart", # Rebuilds the moov atom at the front
            str(out_p)
        ]
        return subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0).returncode == 0

    def fix_audio(self, in_p, out_p):
        cmd = [self.ffmpeg_exe, "-y", "-i", str(in_p), "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(out_p)]
        return subprocess.run(cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0).returncode == 0

    def parse_date(self, filename):
        match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
        if match:
            try:
                dt = datetime.strptime(match.group(1), '%Y-%m-%d_%H-%M-%S')
                return dt.timestamp()
            except ValueError: return None
        return None

    def extract_jpg(self, in_p, out_p):
        with open(in_p, 'rb') as f: data = f.read()
        soi = data.find(self.JPEG_SIG)
        eoi = data.rfind(b'\xff\xd9')
        if soi != -1 and eoi > soi:
            with open(out_p, 'wb') as f: f.write(data[soi : eoi + 2])
            return True
        return False

class EnvironmentManager:
    @staticmethod
    def get_ffmpeg():
        if shutil.which("ffmpeg"): return "ffmpeg"
        bin_dir = Path(__file__).parent.parent / "bin"
        ffmpeg_exe = bin_dir / ("ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
        if ffmpeg_exe.exists(): return str(ffmpeg_exe)
        
        bin_dir.mkdir(parents=True, exist_ok=True)
        if os.name == 'nt':
            # This build includes both ffmpeg.exe and ffprobe.exe
            url = "https://github.com/GyanD/codexffmpeg/releases/download/7.0.1/ffmpeg-7.0.1-full_build.zip"
            zip_path = bin_dir / "ffmpeg.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("ffmpeg.exe") or file.endswith("ffprobe.exe"):
                        with open(bin_dir / os.path.basename(file), "wb") as f:
                            f.write(zip_ref.read(file))
            zip_path.unlink()
            return str(ffmpeg_exe)
        return "ffmpeg"