import os
import sys
import io
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import customtkinter as ctk
from utils.logger import get_logger

logger = get_logger(__name__)

class AssetManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssetManager, cls).__new__(cls)
            cls._instance.icons = {}
            cls._base_path = cls._get_base_path()
        return cls._instance

    @staticmethod
    def _get_base_path():
        """Resolves the absolute path to resources (works for dev & PyInstaller)."""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, "src", "assets", "icons")
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(os.path.dirname(current_dir), "assets", "icons")

    def get_path(self, filename):
        return os.path.join(self._base_path, filename)

    def get_resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def _render_svg(self, path, size):
        """Renders an SVG to a PIL Image using PyMuPDF (fitz)."""
        try:
            with fitz.open(path) as doc:
                page = doc.load_page(0)
                
                # Get the natural size of the SVG
                rect = page.rect
                if rect.width == 0 or rect.height == 0: return None
                
                # Calculate zoom to match requested size
                zoom_x = size[0] / rect.width
                zoom_y = size[1] / rect.height
                mat = fitz.Matrix(zoom_x, zoom_y)
                
                # Render to Pixmap (RGBA)
                pix = page.get_pixmap(matrix=mat, alpha=True)
                
                # Convert Pixmap to PIL Image
                # 'samples' contains the raw bytes
                img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
                return img
                
        except Exception:
            logger.warning("SVG render failed for %s", os.path.basename(path), exc_info=True)
            return None

    def _create_fallback_icon(self, size, color_fill):
        """Generates a simple geometric placeholder if icon is missing."""
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw a rounded rectangle outline
        draw.rectangle([1, 1, size[0]-2, size[1]-2], outline=color_fill, width=2)
        return img

    def load_image(self, name, size=None):
        """Loads an image/icon without recoloring."""
        size = size or (50, 50)
        key = f"img_{name}_{size}"
        if key in self.icons: return self.icons[key]
        
        path = self.get_path(f"{name}.svg")
        if not os.path.exists(path): path = self.get_path(f"{name}.png")
        
        pil_img = None
        if os.path.exists(path):
            if path.endswith(".svg"):
                pil_img = self._render_svg(path, size)
            else:
                try:
                    pil_img = Image.open(path).convert("RGBA")
                    pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
                except Exception:
                    logger.debug("Image load failed for %s", path, exc_info=True)

        if not pil_img:
            pil_img = self._create_fallback_icon(size, (150, 150, 150))

        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        self.icons[key] = ctk_img
        return ctk_img

    def load_icon(self, name, size=(20, 20)):
        """
        Loads an icon with auto-theming (Black for Light Mode, White for Dark Mode).
        Falls back to a generated placeholder if rendering fails.
        """
        key = f"icon_{name}_{size}"
        if key in self.icons: return self.icons[key]
        
        path = self.get_path(f"{name}.svg")
        if not os.path.exists(path): path = self.get_path(f"{name}.png")

        pil_base = None
        if os.path.exists(path):
            if path.endswith(".svg"):
                pil_base = self._render_svg(path, size)
            else:
                try:
                    pil_base = Image.open(path).convert("RGBA")
                    pil_base = pil_base.resize(size, Image.Resampling.LANCZOS)
                except Exception:
                    logger.debug("Icon load failed for %s", path, exc_info=True)

        if pil_base:
            try:
                # Create Light Mode (Black)
                pil_black = pil_base
                
                # Create Dark Mode (White)
                r, g, b, alpha = pil_base.split()
                pil_white = Image.merge("RGBA", (
                    Image.new("L", pil_base.size, 255),
                    Image.new("L", pil_base.size, 255),
                    Image.new("L", pil_base.size, 255),
                    alpha
                ))
            except Exception:
                logger.error("Icon theme generation failed for %s", name, exc_info=True)
                pil_black = self._create_fallback_icon(size, "black")
                pil_white = self._create_fallback_icon(size, "white")
        else:
            pil_black = self._create_fallback_icon(size, "black")
            pil_white = self._create_fallback_icon(size, "white")

        ctk_img = ctk.CTkImage(light_image=pil_black, dark_image=pil_white, size=size)
        self.icons[key] = ctk_img
        return ctk_img

assets = AssetManager()
