import customtkinter as ctk
import os
import shutil
import webbrowser
from ui.theme import *
from utils.assets import assets

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager):
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, fg_color=BG_SIDEBAR, corner_radius=15)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        icon_settings = assets.load_icon("settings", size=(24, 24))
        ctk.CTkLabel(header_frame, text="", image=icon_settings).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_frame, text="Settings & Personalization", font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN).pack(side="left")

        # 1. Appearance Section
        self._build_theme_section(container, 1)

        # 2. Storage Sections
        self._add_storage_card(container, 2, "Exported Data Root", 
                               self.cfg.get("data_root"), 
                               "The main directory containing your Snapchat JSON files and chat media.")

        self._add_storage_card(container, 3, "Memories Storage", 
                               self.cfg.get("memories_path"), 
                               "The folder where your downloaded Snap Memories are stored.")

        # 3. Cache Management Section
        self._build_cache_section(container, 4)

    def _build_theme_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Appearance", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # Load the actual current mode from config
        current_mode = self.cfg.get("appearance_mode")
        
        self.mode_switch = ctk.CTkSegmentedButton(card, values=["Light", "Dark", "System"],
                                                 command=self._change_appearance_mode)
        self.mode_switch.set(current_mode)
        self.mode_switch.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 15))

    def _change_appearance_mode(self, new_mode):
        # 1. Apply UI theme immediately
        ctk.set_appearance_mode(new_mode)
        
        # 2. Persist to file
        self.cfg.save_config(
            self.cfg.get("data_root"), 
            self.cfg.get("memories_path"), 
            appearance_mode=new_mode
        )

    def _add_storage_card(self, parent, row, title, path, description):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title, font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        path_row.grid_columnconfigure(0, weight=1)

        path_box = ctk.CTkFrame(path_row, fg_color=BG_MAIN, corner_radius=6)
        path_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        display_path = path if path else "Not configured"
        path_lbl = ctk.CTkLabel(path_box, text=display_path, font=("Consolas", 11), text_color=TEXT_DIM, wraplength=600, justify="left")
        path_lbl.pack(padx=10, pady=5, anchor="w")

        icon_open = assets.load_icon("external-link", size=(16, 16))
        open_btn = ctk.CTkButton(path_row, text="Open", image=icon_open, width=80, height=32, 
                                 fg_color=BG_SIDEBAR, hover_color=BG_HOVER,
                                 command=lambda p=path: self._open_folder(p))
        open_btn.grid(row=0, column=1, sticky="e")

        if not path or not os.path.exists(path):
            open_btn.configure(state="disabled")

        ctk.CTkLabel(card, text=description, font=("Segoe UI", 11), text_color=TEXT_DIM, wraplength=750, justify="left").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _build_cache_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Application Cache", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        cache_path = os.path.join(self.cfg.get("data_root"), "cache") if self.cfg.get("data_root") else ""
        size_str = self._get_directory_size(cache_path)

        info_row = ctk.CTkFrame(card, fg_color="transparent")
        info_row.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        ctk.CTkLabel(info_row, text=f"Current Size: {size_str}", font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        self.clear_btn = ctk.CTkButton(info_row, text="Clear Cache", width=100, height=32, 
                                       fg_color="#330000", hover_color="#550000",
                                       command=lambda: self._clear_cache(cache_path))
        self.clear_btn.pack(side="right")

        ctk.CTkLabel(card, text="Clearing the cache will delete video thumbnails. They will be re-generated automatically.", 
                     font=("Segoe UI", 11), text_color=TEXT_DIM, wraplength=700, justify="left").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _get_directory_size(self, path):
        if not path or not os.path.exists(path):
            return "0 bytes"
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
        except: return "Error"

        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if total_size < 1024:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024
        return f"{total_size:.1f} TB"

    def _clear_cache(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            shutil.rmtree(path)
            self._setup_ui() 
        except Exception as e:
            print(f"Error clearing cache: {e}")

    def _open_folder(self, path):
        if not path or not os.path.exists(path): return
        try:
            norm_path = os.path.normpath(path)
            if os.name == 'nt': os.startfile(norm_path)
            else: webbrowser.open(f"file://{norm_path}")
        except Exception as e: print(f"Error: {e}")