import os
import cv2
import sys
from PIL import Image, ImageDraw
from utils.cache_manager import cache
from contextlib import contextmanager

# Context manager to suppress C-level stderr (OpenCV noise)
@contextmanager
def suppress_stderr():
    fd = sys.stderr.fileno()
    def _redirect_stderr(to):
        sys.stderr.close()
        os.dup2(to.fileno(), fd)
        sys.stderr = os.fdopen(fd, 'w')

    with os.fdopen(os.dup(fd), 'w') as old_stderr:
        with open(os.devnull, 'w') as file:
            _redirect_stderr(file)
        try:
            yield
        finally:
            _redirect_stderr(old_stderr)

def extract_video_thumbnail(video_path):
    if not os.path.exists(video_path): return None

    # STEP 1: Check Cache
    cached_img = cache.get(video_path)
    if cached_img:
        return cached_img

    # STEP 2: Fast Fail
    try:
        if os.path.getsize(video_path) < 1024: 
            return None
    except OSError:
        return None

    # STEP 3: Extraction (Silenced)
    extracted_img = None
    cap = None
    
    try:
        # Try to suppress, but fallback if environment forbids it
        try:
            with suppress_stderr():
                cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
        except:
            cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)

        if cap and cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                extracted_img = Image.fromarray(frame_rgb)
    except Exception:
        pass
    finally:
        if cap: cap.release()
        
    # STEP 4: Save
    if extracted_img:
        cache.save(video_path, extracted_img)
        
    return extracted_img

def add_play_icon(pil_img):
    """Overlays a generated play icon onto a thumbnail."""
    if not pil_img: return None
    
    try:
        img = pil_img.copy().convert("RGBA")
        w, h = img.size
        
        overlay = Image.new('RGBA', (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(overlay)
        
        # Scale icon relative to image size
        radius = int(min(w, h) * 0.15)
        cx, cy = w // 2, h // 2
        
        # Circle background
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), 
                     fill=(0,0,0,140), outline=(255,255,255,200), width=2)
        
        # Play Triangle
        tr = radius * 0.5
        draw.polygon([(cx-tr*0.5, cy-tr), (cx-tr*0.5, cy+tr), (cx+tr, cy)], 
                     fill=(255,255,255,240))
        
        return Image.alpha_composite(img, overlay).convert("RGB")

    except Exception:
        return pil_img