import customtkinter as ctk
import os
import shutil
import webbrowser
from ui.theme import *
from utils.assets import assets

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager, data_manager): # Added data_manager
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self.data_manager = data_manager
        self.GUTTER = 15
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

        # 2. Data Integrity Section (NEW)
        self._build_integrity_section(container, 2)

        # 3. Storage Sections
        self._add_storage_card(container, 3, "Exported Data Root", 
                               self.cfg.get("data_root"), 
                               "The main directory containing your Snapchat JSON files and chat media.")

        self._add_storage_card(container, 4, "Memories Storage", 
                               self.cfg.get("memories_path"), 
                               "The folder where your downloaded Snap Memories are stored.")

        # 4. Cache Management Section
        self._build_cache_section(container, 5)

    def _build_integrity_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(card, text="Data Integrity Audit", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 5))
        
        # Run Check
        report = self.data_manager.perform_integrity_check()
        
        self._integrity_stat(card, 1, 0, "Chat Media", report["chats"])
        self._integrity_stat(card, 1, 1, "Memories", report["memories"])

        ctk.CTkLabel(card, text="This shows how much of your exported data is actually available as files on your computer.", 
                     font=("Segoe UI", 11), text_color=TEXT_DIM, wraplength=700).grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 15))

    def _integrity_stat(self, parent, row, col, label, data):
        f = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8)
        f.grid(row=row, column=col, padx=15, pady=5, sticky="ew")
        
        total = data["total"]
        missing = data["missing"]
        found = total - missing
        percent = (found / total * 100) if total > 0 else 0
        
        color = SNAP_RED if percent < 90 else SNAP_BLUE

        ctk.CTkLabel(f, text=label, font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN).pack(pady=(10, 0))
        ctk.CTkLabel(f, text=f"{found} / {total}", font=("Segoe UI", 18, "bold"), text_color=color).pack()
        ctk.CTkLabel(f, text=f"{percent:.1f}% Linked", font=("Segoe UI", 11), text_color=TEXT_DIM).pack(pady=(0, 10))

    def _change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.cfg.save_config(self.cfg.get("data_root"), self.cfg.get("memories_path"), appearance_mode=new_mode)

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
        ctk.CTkLabel(path_box, text=display_path, font=("Consolas", 11), text_color=TEXT_DIM, wraplength=600, justify="left").pack(padx=10, pady=5, anchor="w")
        open_btn = ctk.CTkButton(path_row, text="Open", image=assets.load_icon("external-link", size=(16, 16)), width=80, height=32, fg_color=BG_SIDEBAR, hover_color=BG_HOVER, command=lambda p=path: self._open_folder(p))
        open_btn.grid(row=0, column=1, sticky="e")
        if not path or not os.path.exists(path): open_btn.configure(state="disabled")
        ctk.CTkLabel(card, text=description, font=("Segoe UI", 11), text_color=TEXT_DIM, wraplength=750, justify="left").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _build_theme_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text="Appearance", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        current_mode = self.cfg.get("appearance_mode")
        mode_switch = ctk.CTkSegmentedButton(card, values=["Light", "Dark", "System"], command=self._change_appearance_mode)
        mode_switch.set(current_mode)
        mode_switch.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 15))

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
        ctk.CTkButton(info_row, text="Clear Cache", width=100, height=32, fg_color="#330000", hover_color="#550000", command=lambda: self._clear_cache(cache_path)).pack(side="right")
        ctk.CTkLabel(card, text="Clearing the cache will delete video thumbnails. They will be re-generated automatically.", font=("Segoe UI", 11), text_color=TEXT_DIM, wraplength=700, justify="left").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _get_directory_size(self, path):
        if not path or not os.path.exists(path): return "0 bytes"
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames: total_size += os.path.getsize(os.path.join(dirpath, f))
        except: return "Error"
        for unit in ['bytes', 'KB', 'MB', 'GB']:
            if total_size < 1024: return f"{total_size:.1f} {unit}"
            total_size /= 1024
        return f"{total_size:.1f} TB"

    def _clear_cache(self, path):
        if not path or not os.path.exists(path): return
        try:
            shutil.rmtree(path)
            self._setup_ui() 
        except: pass

    def _open_folder(self, path):
        if not path or not os.path.exists(path): return
        try:
            norm_path = os.path.normpath(path)
            if os.name == 'nt': os.startfile(norm_path)
            else: webbrowser.open(f"file://{norm_path}")
        except: pass