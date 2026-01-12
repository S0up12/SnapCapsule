import os
import sys
from PIL import Image
import customtkinter as ctk

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
            # Running as compiled .exe
            return os.path.join(sys._MEIPASS, "src", "assets", "icons")
        else:
            # Running from source
            # Go up two levels from utils/assets.py -> src -> root, then down to assets
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(os.path.dirname(current_dir), "assets", "icons")

    def get_path(self, filename):
        return os.path.join(self._base_path, filename)

    def get_resource_path(self, relative_path):
        """Helper for non-icon files (like tutorial.md)"""
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def load_image(self, name, size=None):
        key = f"img_{name}_{size}"
        if key in self.icons: return self.icons[key]
        
        try:
            path = self.get_path(f"{name}.png")
            if not os.path.exists(path): return None
            
            pil_img = Image.open(path).convert("RGBA")
            if size:
                pil_img = pil_img.resize(size, Image.Resampling.LANCZOS)
                
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size if size else pil_img.size)
            self.icons[key] = ctk_img
            return ctk_img
        except Exception as e:
            print(f"Img Error {name}: {e}")
            return None

    def load_icon(self, name, size=(20, 20)):
        key = f"icon_{name}_{size}"
        if key in self.icons: return self.icons[key]
        
        try:
            path = self.get_path(f"{name}.png")
            if not os.path.exists(path): return None
                
            pil_white = Image.open(path).convert("RGBA")
            r, g, b, alpha = pil_white.split()
            pil_black = Image.merge("RGBA", (
                Image.new("L", pil_white.size, 0),
                Image.new("L", pil_white.size, 0),
                Image.new("L", pil_white.size, 0),
                alpha
            ))

            ctk_img = ctk.CTkImage(light_image=pil_black, dark_image=pil_white, size=size)
            self.icons[key] = ctk_img
            return ctk_img
        except: return None

assets = AssetManager()