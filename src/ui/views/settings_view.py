import customtkinter as ctk
import os
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
        ctk.CTkLabel(header_frame, text="Storage & Export Settings", font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN).pack(side="left")

        # Data Root Info
        self._add_storage_card(container, 1, "Exported Data Root", 
                               self.cfg.get("data_root"), 
                               "The main directory containing your Snapchat JSON files and chat media. "
                               "This is where the app looks for your chat history, profile, and friends list.")

        # Memories Path Info
        self._add_storage_card(container, 2, "Memories Storage", 
                               self.cfg.get("memories_path"), 
                               "The specific folder where your downloaded Snap Memories (photos and videos) are stored. "
                               "The app links these files to your account history based on their timestamps.")

        # Cache Info
        cache_path = os.path.join(self.cfg.get("data_root"), "cache") if self.cfg.get("data_root") else ""
        self._add_storage_card(container, 3, "Application Cache", 
                               cache_path, 
                               "Used to store generated video thumbnails and temporary UI assets to improve performance. "
                               "This folder is created automatically within your Data Root.")

    def _add_storage_card(self, parent, row, title, path, description):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=10)
        card.grid_columnconfigure(0, weight=1)

        # Title Row with Icon
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(title_frame, text=title, font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE).pack(side="left")
        
        # Path display container (Input-style row)
        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        path_row.grid_columnconfigure(0, weight=1)

        # Clickable Path Box
        path_box = ctk.CTkFrame(path_row, fg_color=BG_MAIN, corner_radius=6)
        path_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        display_path = path if path else "Not configured"
        path_lbl = ctk.CTkLabel(path_box, text=display_path, font=("Consolas", 11), text_color=TEXT_DIM, wraplength=600, justify="left")
        path_lbl.pack(padx=10, pady=5, anchor="w")

        # Open Folder Button
        icon_folder = assets.load_icon("external-link", size=(16, 16))
        open_btn = ctk.CTkButton(path_row, text="Open", image=icon_folder, width=80, height=32, 
                                 fg_color=BG_SIDEBAR, hover_color=BG_HOVER,
                                 command=lambda p=path: self._open_folder(p))
        open_btn.grid(row=0, column=1, sticky="e")

        # Disable button if path is empty
        if not path or not os.path.exists(path):
            open_btn.configure(state="disabled", text_color="#555")

        # Description
        ctk.CTkLabel(card, text=description, font=("Segoe UI", 12), text_color=TEXT_MAIN, wraplength=750, justify="left").grid(row=2, column=0, sticky="w", padx=15, pady=(5, 15))

    def _open_folder(self, path):
        """Opens the specified path in the system file explorer."""
        if not path or not os.path.exists(path):
            return
            
        try:
            # Normalize path for the OS
            norm_path = os.path.normpath(path)
            if os.name == 'nt':
                os.startfile(norm_path)
            else:
                webbrowser.open(norm_path)
        except Exception as e:
            print(f"Error opening folder: {e}")