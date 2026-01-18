import customtkinter as ctk
import os
import threading
import webbrowser
from tkinter import filedialog
from utils.downloader import MemoryDownloader
from PIL import Image
from ui.theme import *
from utils.assets import assets

class HomeView(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.app = main_app
        self.downloader = None 
        self.is_processing = False
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_setup_card(row=0, column=0)
        self._build_tutorial_card(row=0, column=1)

    def _build_setup_card(self, row, column):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=row, column=column, sticky="nsew", padx=20, pady=20)
        self.card = ctk.CTkFrame(container, fg_color=BG_SIDEBAR, corner_radius=25)
        self.card.pack(expand=True, fill="both", padx=10, pady=10)

        logo_img = assets.load_image("snapcapsule", size=(100, 100))
        if logo_img: 
            ctk.CTkLabel(self.card, text="", image=logo_img).pack(pady=(20, 0))
            
        ctk.CTkLabel(self.card, text="SnapCapsule", font=("Segoe UI", 28, "bold"), text_color=TEXT_MAIN).pack(pady=(0, 5))
        ctk.CTkLabel(self.card, text="Digital time capsule, purely local.", font=("Segoe UI", 14), text_color=TEXT_DIM).pack(pady=(0, 20))

        # Main Action Area
        self.action_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=30)

        self.btn_main = ctk.CTkButton(self.action_frame, text=" Start New Import (ZIP)", 
                                      image=assets.load_icon("download-cloud", size=(20, 20)), 
                                      compound="left", command=self.handle_zip_import, 
                                      fg_color=SNAP_BLUE, hover_color="#007ACC", 
                                      text_color="white", height=45, corner_radius=22,
                                      font=("Segoe UI", 14, "bold"))
        self.btn_main.pack(fill="x", pady=10)

        # Quick Link Frame
        self.quick_link = ctk.CTkFrame(self.action_frame, fg_color=BG_MAIN, corner_radius=15)
        self.quick_link.pack(fill="x", pady=10)
        
        ctk.CTkLabel(self.quick_link, text="OR LINK PREVIOUS FOLDER", font=("Segoe UI", 10, "bold"), text_color=TEXT_DIM).pack(pady=(10, 0))
        self.entry_root = self._build_input_row(self.quick_link, self.app.cfg.get("data_root"))

        # Status Area
        self.lbl_status = ctk.CTkLabel(self.card, text="Ready to process", text_color=TEXT_DIM, font=("Segoe UI", 11))
        self.lbl_status.pack(pady=(15, 0))

        self.progress = ctk.CTkProgressBar(self.card, progress_color=SNAP_YELLOW, height=6)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=30, pady=15)

    def _build_input_row(self, parent, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=(5, 15))
        entry = ctk.CTkEntry(frame, fg_color=BG_SIDEBAR, border_color=BG_CARD, height=35, corner_radius=10)
        entry.insert(0, default_val)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(frame, text="", image=assets.load_icon("folder", size=(18, 18)), 
                      width=40, height=35, fg_color=BG_CARD, corner_radius=10, 
                      command=lambda: self._browse_existing(entry)).pack(side="right")
        return entry

    def handle_zip_import(self):
        """Unified One-Click ZIP Pipeline."""
        if self.is_processing: return
        
        zip_path = filedialog.askopenfilename(title="Select Snapchat Export ZIP", filetypes=[("Snapchat Export", "*.zip")])
        if not zip_path: return
        
        dest_root = filedialog.askdirectory(title="Select Folder to Store your Archive")
        if not dest_root: return

        self.is_processing = True
        self.btn_main.configure(state="disabled", text=" Processing...")
        self.downloader = MemoryDownloader(self.update_status, self.update_progress)
        
        threading.Thread(target=self._run_zip_pipeline, args=(zip_path, dest_root), daemon=True).start()

    def _run_zip_pipeline(self, zip_p, dest_p):
        """Background pipeline: Extract -> Stage -> Auto-Configure."""
        try:
            # Step 1: Extract and Stage
            success = self.downloader.process_data_package(zip_p, dest_p, download_memories=True)
            
            if success:
                # Step 2: Auto-Discovery via DataManager
                actual_folder = self.downloader._find_snap_root(dest_p)
                self.after(0, lambda: self.finalize_import(actual_folder))
            else:
                self.after(0, self.reset_ui)
        except Exception as e:
            self.after(0, lambda: self.update_status(f"Error: {str(e)}"))
            self.after(0, self.reset_ui)

    def finalize_import(self, folder_path):
        """Saves configuration and reloads application state."""
        self.entry_root.delete(0, "end")
        self.entry_root.insert(0, folder_path)
        self.app.cfg.save_config(folder_path, "") # memories_path left empty for auto-discovery
        
        # Trigger global reload
        chat_idx, mems, profile = self.app.data_manager.reload()
        self.app.chat_index, self.app.memories, self.app.profile = chat_idx, mems, profile
        
        # Cleanup view pointers to force fresh render on next tab click
        if self.app.view_chat: self.app.view_chat.populate_friends(chat_idx)
        if self.app.view_memories: self.app.view_memories.load_page(1)
        
        self.update_status("Import Successful!")
        self.reset_ui()

    def _browse_existing(self, entry):
        p = filedialog.askdirectory()
        if p: 
            entry.delete(0, "end")
            entry.insert(0, p)
            self.finalize_import(p)

    def reset_ui(self):
        self.is_processing = False
        self.btn_main.configure(state="normal", text=" Start New Import (ZIP)")

    def update_status(self, text): self.lbl_status.configure(text=text)
    def update_progress(self, val): self.progress.set(val)

    def _build_tutorial_card(self, row, column):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=row, column=column, sticky="nsew", padx=20, pady=20)
        card = ctk.CTkFrame(container, fg_color=BG_SIDEBAR, corner_radius=25)
        card.pack(expand=True, fill="both", padx=10, pady=10)
        scroll = ctk.CTkScrollableFrame(card, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=20)
        path = assets.get_resource_path("tutorial.md")
        self._render_markdown(scroll, path)

    def _render_markdown(self, parent, filename):
        if not os.path.exists(filename): return
        with open(filename, "r", encoding="utf-8") as f: lines = f.readlines()
        icon_link = assets.load_icon("link", size=(16, 16))
        for line in lines:
            line = line.strip()
            if not line: ctk.CTkFrame(parent, fg_color="transparent", height=10).pack(); continue
            if line.startswith("# "): ctk.CTkLabel(parent, text=line[2:], font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN, anchor="w").pack(fill="x", padx=15, pady=(10, 5))
            elif line.startswith("## "): ctk.CTkLabel(parent, text=line[3:], font=("Segoe UI", 14, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", padx=15, pady=(15, 2))
            elif line.startswith("* "): ctk.CTkLabel(parent, text="• " + line[2:], font=("Segoe UI", 13), text_color=TEXT_DIM, justify="left", anchor="w", wraplength=400).pack(fill="x", padx=25, pady=1)
            elif line.startswith("[BUTTON:"):
                try:
                    end_idx = line.index("]")
                    url, label_text = line[8:end_idx], line[end_idx+1:].strip()
                    ctk.CTkButton(parent, text=f" {label_text}", image=icon_link, compound="left", height=30, fg_color=BG_CARD, hover_color=BG_HOVER, text_color=SNAP_BLUE, command=lambda u=url: webbrowser.open(u)).pack(anchor="w", padx=20, pady=5)
                except: pass
            else:
                font = ("Segoe UI", 13)
                if "**" in line: 
                    line = line.replace("**", "")
                    font = ("Segoe UI", 13, "bold")
                ctk.CTkLabel(parent, text=line, font=font, text_color=TEXT_DIM, justify="left", anchor="w", wraplength=400).pack(fill="x", padx=15, pady=1)