import os
import cv2
from PIL import Image, ImageDraw
from utils.cache_manager import cache

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

    # STEP 3: Extraction
    extracted_img = None
    cap = None
    try:
        cap = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                extracted_img = Image.fromarray(frame_rgb)
    except Exception as e:
        print(f"[CV2 Error] {os.path.basename(video_path)}: {e}")
    finally:
        if cap: cap.release()
        
    # STEP 4: Save
    if extracted_img:
        cache.save(video_path, extracted_img)
        
    return extracted_img

def add_play_icon(pil_img):
    """Overlays the play icon asset onto a thumbnail."""
    if not pil_img: return None
    
    try:
        img = pil_img.copy().convert("RGBA")
        w, h = img.size
        
        # 1. Try loading the actual asset first (High Quality)
        # We construct the path manually here to avoid circular dependencies with assets.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_dir)
        asset_path = os.path.join(src_dir, "assets", "icons", "play.png")
        
        if os.path.exists(asset_path):
            icon = Image.open(asset_path).convert("RGBA")
            # Resize icon to 25% of the thumbnail
            icon_w = int(min(w, h) * 0.25)
            icon_h = icon_w
            icon = icon.resize((icon_w, icon_h), Image.Resampling.LANCZOS)
            
            # Paste centered
            cx, cy = w // 2, h // 2
            img.paste(icon, (cx - icon_w//2, cy - icon_h//2), icon)
            return img.convert("RGB")
            
        else:
            # 2. Fallback: Draw shapes if icon file missing
            overlay = Image.new('RGBA', (w, h), (0,0,0,0))
            draw = ImageDraw.Draw(overlay)
            
            cx, cy = w // 2, h // 2
            radius = int(min(w, h) * 0.15)
            
            draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), 
                         fill=(0,0,0,140), outline=(255,255,255,200), width=2)
            tr = radius * 0.5
            draw.polygon([(cx-tr*0.5, cy-tr), (cx-tr*0.5, cy+tr), (cx+tr, cy)], 
                         fill=(255,255,255,240))
            
            return Image.alpha_composite(img, overlay).convert("RGB")

    except Exception:
        return pil_img