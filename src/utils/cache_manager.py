import os
import hashlib
from PIL import Image
from pathlib import Path

class ThumbnailCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThumbnailCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def init(self):
        """Initializes cache in the standard Windows Local AppData location."""
        if self.initialized: return
        
        # Resolve Local AppData for high-volume cache data
        local_dir = os.environ.get('LOCALAPPDATA', os.environ.get('TEMP', os.getcwd()))
        self.cache_dir = Path(local_dir) / "SnapCapsule" / "Thumbnails"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
            
        print(f"[DEBUG] Cache initialized at: {self.cache_dir}")
        self.initialized = True

    def get(self, video_path):
        if not self.initialized: return None
        thumb_path = self._get_path(video_path)
        if thumb_path.exists():
            try:
                return Image.open(thumb_path)
            except:
                return None
        return None

    def save(self, video_path, pil_img):
        if not self.initialized or not pil_img: return
        try:
            thumb_path = self._get_path(video_path)
            pil_img.convert("RGB").save(thumb_path, "JPEG", quality=60, optimize=True)
        except Exception as e:
            print(f"[ERROR] Cache save failed: {e}")

    def _get_path(self, video_path):
        norm_path = os.path.normpath(os.path.abspath(video_path))
        h = hashlib.md5(norm_path.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{h}.jpg"

cache = ThumbnailCache()