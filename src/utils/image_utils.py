import os
import cv2
import sys
from PIL import Image, ImageDraw, ImageOps
from utils.cache_manager import cache
from contextlib import contextmanager
import os
from os.path import splitext, basename, join

# Context manager to suppress C-level stderr (OpenCV noise)
@contextmanager
def suppress_stderr():
    fd = sys.stderr.fileno() #
    def _redirect_stderr(to):
        sys.stderr.close() #
        os.dup2(to.fileno(), fd) #
        sys.stderr = os.fdopen(fd, 'w') #

    with os.fdopen(os.dup(fd), 'w') as old_stderr: #
        with open(os.devnull, 'w') as file: #
            _redirect_stderr(file) #
        try:
            yield
        finally:
            _redirect_stderr(old_stderr) #

def composite_snap_image(base_path, overlay_path):
    """
    Overlays a Snapchat caption/overlay PNG onto the base image.
    Returns a combined PIL Image.
    """
    try:
        base = Image.open(base_path).convert("RGBA")
        overlay = Image.open(overlay_path).convert("RGBA")
        
        # Snapchat overlays are usually the same aspect ratio but might 
        # differ in absolute resolution. Scale overlay to match base.
        if base.size != overlay.size:
            overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
            
        combined = Image.alpha_composite(base, overlay)
        return combined.convert("RGB")
    except Exception as e:
        print(f"Error compositing image: {e}")
        return Image.open(base_path) if os.path.exists(base_path) else None

def extract_video_thumbnail(video_path):
    if not os.path.exists(video_path): return None

    # STEP 1: Check Cache (Fastest)
    cached_img = cache.get(video_path)
    if cached_img: return cached_img

    # STEP 2: Fallback to Snapchat's sidecar image
    dir_name = os.path.dirname(video_path)
    base_name = splitext(basename(video_path))[0]
    img_fallback = join(dir_name, f"{base_name}_image.jpg")
    
    if os.path.exists(img_fallback):
        try:
            with Image.open(img_fallback) as pil_img:
                pil_img.thumbnail((300, 300))
                cache.save(video_path, pil_img)
                return pil_img
        except: pass

    # STEP 3: Optimized OpenCV extraction
    extracted_img = None
    cap = None
    try:
        with suppress_stderr():
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                # Force grab the first frame only
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Resize at the CV2 level (faster than Pillow)
                    frame = cv2.resize(frame, (300, 300), interpolation=cv2.INTER_AREA)
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    extracted_img = Image.fromarray(frame_rgb)
    except: pass
    finally:
        if cap: cap.release()
        
    if extracted_img:
        cache.save(video_path, extracted_img)
        
    return extracted_img

def add_play_icon(pil_img):
    """Overlays a generated play icon onto a thumbnail."""
    if not pil_img: return None #
    
    try:
        img = pil_img.copy().convert("RGBA") #
        w, h = img.size #
        
        overlay = Image.new('RGBA', (w, h), (0,0,0,0)) #
        draw = ImageDraw.Draw(overlay) #
        
        # Scale icon relative to image size
        radius = int(min(w, h) * 0.15) #
        cx, cy = w // 2, h // 2 #
        
        # Circle background
        draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), 
                     fill=(0,0,0,140), outline=(255,255,255,200), width=2) #
        
        # Play Triangle
        tr = radius * 0.5 #
        draw.polygon([(cx-tr*0.5, cy-tr), (cx-tr*0.5, cy+tr), (cx+tr, cy)], 
                     fill=(255,255,255,240)) #
        
        return Image.alpha_composite(img, overlay).convert("RGB") #

    except Exception:
        return pil_img #