import os
import cv2
import sys
from PIL import Image, ImageDraw, ImageOps
from utils.cache_manager import cache
from contextlib import contextmanager

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
    if not os.path.exists(video_path): return None #

    # STEP 1: Check Cache
    cached_img = cache.get(video_path) #
    if cached_img:
        return cached_img #

    # NEW: Try to find the associated static image variant if extraction is difficult.
    # Snapchat often exports an '_image.jpg' alongside the video.
    dir_name = os.path.dirname(video_path)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    img_fallback = os.path.join(dir_name, f"{base_name}_image.jpg")
    
    if os.path.exists(img_fallback):
        try:
            pil_img = Image.open(img_fallback)
            pil_img.thumbnail((300, 300))
            cache.save(video_path, pil_img)
            return pil_img
        except: pass

    # STEP 2: Fast Fail
    try:
        if os.path.getsize(video_path) < 1024: 
            return None #
    except OSError:
        return None #

    # STEP 3: Extraction (Silenced)
    extracted_img = None
    cap = None
    
    try:
        # Try to suppress, but fallback if environment forbids it
        try:
            with suppress_stderr():
                cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG) #
        except:
            cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG) #

        if cap and cap.isOpened():
            ret, frame = cap.read() #
            if ret and frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) #
                extracted_img = Image.fromarray(frame_rgb) #
    except Exception:
        pass
    finally:
        if cap: cap.release() #
        
    # STEP 4: Save
    if extracted_img:
        cache.save(video_path, extracted_img) #
        
    return extracted_img #

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