import os
import hashlib
from PIL import Image
from utils.logger import get_logger

logger = get_logger(__name__)

class ThumbnailCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThumbnailCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def init(self, root_dir):
        if self.initialized: return
        
        self.cache_dir = os.path.join(root_dir, "cache", "thumbnails")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
        logger.debug("Cache initialized at: %s", self.cache_dir)
        self.initialized = True

    def get(self, video_path):
        """Returns the PIL Image if cached, otherwise None"""
        if not self.initialized: return None
        
        thumb_path = self._get_path(video_path)
        if os.path.exists(thumb_path):
            try:
                # We return the image so it can be used immediately
                return Image.open(thumb_path)
            except Exception:
                logger.debug("Thumbnail cache read failed for %s", thumb_path, exc_info=True)
                return None
        return None

    def save(self, video_path, pil_img):
        """Saves a PIL Image to the cache"""
        if not self.initialized or not pil_img: return
        
        try:
            thumb_path = self._get_path(video_path)
            # Optimize: Convert to RGB and save as optimized JPEG
            pil_img.convert("RGB").save(thumb_path, "JPEG", quality=60, optimize=True)
        except Exception:
            logger.error("Thumbnail cache save failed for %s", video_path, exc_info=True)

    def _get_path(self, video_path):
        # --- THE FIX IS HERE ---
        # Normalize the path to ensure it is absolute and uses consistent separators
        norm_path = os.path.normpath(os.path.abspath(video_path))
        
        # Hash the normalized path so it is always the same for this file
        h = hashlib.md5(norm_path.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.jpg")

# Global singleton
cache = ThumbnailCache()
