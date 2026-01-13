import os
from PIL import Image

class MediaResolver:
    @staticmethod
    def get_display_image(base_path):
        """
        Takes a base path like '2025-12-05_19-51-05.jpg' and 
        returns a PIL Image object of the best available version.
        """
        dir_name = os.path.dirname(base_path)
        file_name = os.path.basename(base_path)
        name_no_ext = os.path.splitext(file_name)[0]

        # Potential file candidates
        img_path = os.path.join(dir_name, f"{name_no_ext}_image.jpg")
        cap_path = os.path.join(dir_name, f"{name_no_ext}_caption.png")

        # Logic: If both base image and caption exist, overlay them
        if os.path.exists(img_path) and os.path.exists(cap_path):
            base = Image.open(img_path).convert("RGBA")
            overlay = Image.open(cap_path).convert("RGBA")
            
            # Ensure overlay matches base size
            if overlay.size != base.size:
                overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
                
            return Image.alpha_composite(base, overlay).convert("RGB")
            
        # Fallback to the '_image' variant if it exists alone
        if os.path.exists(img_path):
            return Image.open(img_path)

        # Final fallback to the original linked path (which might be the corrupt one)
        if os.path.exists(base_path):
            return Image.open(base_path)
            
        return None