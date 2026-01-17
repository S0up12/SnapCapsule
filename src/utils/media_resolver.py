import os
from PIL import Image

class MediaResolver:
    @staticmethod
    def get_display_image(base_path):
        """
        Optimized resolution for Snapchat media pairs.
        Minimizes disk I/O by prioritizing the composited variant.
        """
        if not base_path or not os.path.exists(base_path):
            return None

        dir_name = os.path.dirname(base_path)
        file_name = os.path.basename(base_path)
        name_no_ext = os.path.splitext(file_name)[0]

        # Standard Snapchat export suffixes
        img_path = os.path.join(dir_name, f"{name_no_ext}_image.jpg")
        cap_path = os.path.join(dir_name, f"{name_no_ext}_caption.png")

        # Optimization: Check for pairs first to avoid multiple opens
        has_img = os.path.exists(img_path)
        has_cap = os.path.exists(cap_path)

        try:
            if has_img and has_cap:
                base = Image.open(img_path).convert("RGBA")
                overlay = Image.open(cap_path).convert("RGBA")
                
                # Faster check for size mismatch
                if overlay.size != base.size:
                    overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
                    
                return Image.alpha_composite(base, overlay).convert("RGB")
                
            if has_img:
                return Image.open(img_path)

            # Fallback to the original path provided
            return Image.open(base_path)
        except Exception as e:
            # Silent fail for corrupt images
            return None

    @staticmethod
    def is_video(path):
        """Standardized video check for the application."""
        return path.lower().endswith(('.mp4', '.mov', '.avi'))