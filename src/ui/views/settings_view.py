import customtkinter as ctk
import os
import shutil
import webbrowser
from ui.theme import *
from utils.assets import assets

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager, data_manager):
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self.data_manager = data_manager
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, fg_color=BG_SIDEBAR, corner_radius=15)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)

        # --- HEADER AREA ---
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        icon_settings = assets.load_icon("settings", size=(24, 24))
        ctk.CTkLabel(header_frame, text="", image=icon_settings).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header_frame, text="Settings & Management", font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN).pack(side="left")

        # Top-Right Appearance Toggle
        mode_switch = ctk.CTkSegmentedButton(header_frame, values=["Light", "Dark", "System"], 
                                             command=self._change_appearance_mode, width=180)
        mode_switch.set(self.cfg.get("appearance_mode"))
        mode_switch.pack(side="right")

        # --- SECTION 1: DATA HEALTH & INSIGHTS ---
        # Bundles integrity audit and database status
        self._build_health_section(container, 1)

        # --- SECTION 2: FILE SYSTEM LOCATIONS ---
        self._build_locations_section(container, 2)

        # --- SECTION 3: MAINTENANCE & SECURITY ---
        self._build_maintenance_section(container, 3)

    def _build_health_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(card, text="Data Health Dashboard", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(15, 5))
        
        # Integrity Stats
        report = self.data_manager.perform_integrity_check()
        self._integrity_stat(card, 1, 0, "Chat Media Status", report["chats"], "Images and videos referenced in conversations")
        self._integrity_stat(card, 1, 1, "Memories Status", report["memories"], "Your archived Snap History gallery")

    def _integrity_stat(self, parent, row, col, label, data, detail):
        f = ctk.CTkFrame(parent, fg_color=BG_MAIN, corner_radius=8)
        f.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        
        found = data["total"] - data["missing"]
        percent = (found / data["total"] * 100) if data["total"] > 0 else 0
        color = SNAP_RED if percent < 90 else SNAP_BLUE

        ctk.CTkLabel(f, text=label, font=("Segoe UI", 11, "bold"), text_color=TEXT_MAIN).pack(pady=(8, 0))
        ctk.CTkLabel(f, text=f"{found} / {data['total']}", font=("Segoe UI", 18, "bold"), text_color=color).pack()
        ctk.CTkLabel(f, text=f"{percent:.1f}% Linked Successfully", font=("Segoe UI", 10), text_color=TEXT_DIM).pack()
        ctk.CTkLabel(f, text=detail, font=("Segoe UI", 9), text_color=TEXT_DIM, wraplength=180).pack(pady=(5, 10))

    def _build_locations_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Data Sources", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        path_container = ctk.CTkFrame(card, fg_color="transparent")
        path_container.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 15))

        self._add_clickable_path(path_container, "Core Archive", self.cfg.get("data_root"), 
                                 "Snapchat unzipped export containing JSON logs")
        self._add_clickable_path(path_container, "Media Storage", self.cfg.get("memories_path"), 
                                 "Local folder containing downloaded .mp4 and .jpg memories")

    def _build_maintenance_section(self, parent, row):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="Maintenance & Security", font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        action_row = ctk.CTkFrame(card, fg_color=BG_MAIN, corner_radius=8)
        action_row.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        
        cache_path = os.path.join(self.cfg.get("data_root"), "cache") if self.cfg.get("data_root") else ""
        size_str = self._get_directory_size(cache_path)
        
        ctk.CTkLabel(action_row, text=f" Thumbnail Cache: {size_str}", image=assets.load_icon("image", size=(16, 16)),
                     compound="left", font=("Segoe UI", 11, "bold"), text_color=TEXT_DIM).pack(side="left", padx=15, pady=15)
        
        btn_container = ctk.CTkFrame(action_row, fg_color="transparent")
        btn_container.pack(side="right", padx=10)

        ctk.CTkButton(btn_container, text="Clear Cache", width=100, height=28, fg_color=BG_CARD, hover_color=BG_HOVER,
                      font=("Segoe UI", 11, "bold"), command=lambda: self._clear_cache(cache_path)).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_container, text="Reset App", width=100, height=28, fg_color="#330000", hover_color="#550000",
                      font=("Segoe UI", 11, "bold"), command=self._confirm_reset).pack(side="left", padx=5)

        ctk.CTkLabel(card, text="🛡️ All data processing is strictly local. No data is sent to external servers.", 
                     font=("Segoe UI", 11), text_color="#2ECC71").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _add_clickable_path(self, parent, label, path, detail):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=4)
        
        ctk.CTkLabel(row, text=f"{label}:", font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        display_text = path if path else "Not configured"
        path_lbl = ctk.CTkLabel(row, text=display_text, font=("Consolas", 11), text_color=SNAP_BLUE, cursor="hand2")
        path_lbl.pack(side="left", padx=5)
        
        ctk.CTkLabel(row, text=f"({detail})", font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="left")

        if path and os.path.exists(path):
            path_lbl.bind("<Button-1>", lambda e: self._open_folder(path))

    def _change_appearance_mode(self, new_mode):
        ctk.set_appearance_mode(new_mode)
        self.cfg.save_config(self.cfg.get("data_root"), self.cfg.get("memories_path"), appearance_mode=new_mode)

    def _confirm_reset(self):
        if os.path.exists("config.json"):
            os.remove("config.json")
            self.winfo_toplevel().destroy()
            os._exit(0)

    def _get_directory_size(self, path):
        if not path or not os.path.exists(path): return "0 bytes"
        total = 0
        for dirpath, _, filenames in os.walk(path):
            for f in filenames: total += os.path.getsize(os.path.join(dirpath, f))
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total < 1024: return f"{total:.1f} {unit}"
            total /= 1024
        return f"{total:.1f} TB"

    def _clear_cache(self, path):
        if path and os.path.exists(path):
            shutil.rmtree(path)
            self._setup_ui()

    def _open_folder(self, path):
        norm_path = os.path.normpath(path)
        if os.name == 'nt': os.startfile(norm_path)
        else: webbrowser.open(f"file://{norm_path}")