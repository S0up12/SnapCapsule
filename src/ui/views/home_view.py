import customtkinter as ctk
import os
import threading
import webbrowser
from tkinter import filedialog
from utils.downloader import MemoryDownloader
from ui.theme import *
from utils.assets import assets

class HomeView(ctk.CTkFrame):
    def __init__(self, parent, main_app):
        super().__init__(parent, fg_color="transparent")
        self.app = main_app
        self.downloader = None 
        self.is_downloading = False
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_setup_card(row=0, column=0)
        self._build_tutorial_card(row=0, column=1)

    def _build_setup_card(self, row, column):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=row, column=column, sticky="nsew", padx=20, pady=20)
        self.card = ctk.CTkFrame(container, fg_color=BG_SIDEBAR, corner_radius=25)
        self.card.pack(expand=True, fill="both", padx=10, pady=10)

        logo_img = assets.load_image("snapcapsule", size=(100, 100))
        if logo_img: ctk.CTkLabel(self.card, text="", image=logo_img).pack(pady=(20, 0))
            
        ctk.CTkLabel(self.card, text="SnapCapsule", font=("Segoe UI", 28, "bold"), text_color=TEXT_MAIN).pack(pady=(0, 5))
        ctk.CTkLabel(self.card, text="Your digital time capsule, purely local.", font=("Segoe UI", 14), text_color=TEXT_DIM).pack(pady=(0, 20))

        input_container = ctk.CTkFrame(self.card, fg_color="transparent")
        input_container.pack(fill="x", padx=30) 

        # OPTION A: ZIP FLOW
        ctk.CTkLabel(input_container, text="Option A: Extract from ZIP", font=("Segoe UI", 13, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", pady=(10, 5))
        self.btn_dl = ctk.CTkButton(input_container, text=" Select ZIP & Process", image=assets.load_icon("download-cloud", size=(20, 20)), 
                                    compound="left", command=self.start_dl, fg_color=BG_CARD, hover_color=BG_HOVER, 
                                    text_color=TEXT_MAIN, height=35, corner_radius=18)
        self.btn_dl.pack(fill="x", pady=(0, 10))

        # OPTION B: EXISTING FOLDER FLOW
        ctk.CTkLabel(input_container, text="Option B: Link Existing Folder", font=("Segoe UI", 13, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", pady=(10, 5))
        self.entry_root = self._build_input_row(input_container, self.app.cfg.get("data_root"))
        
        # RE-STAGE BUTTON
        self.btn_restage = ctk.CTkButton(input_container, text=" Re-scan & Stage Log Data", 
                                        image=assets.load_icon("activity", size=(18, 18)), 
                                        compound="left", command=self.confirm_restage, 
                                        fg_color="transparent", border_width=1, border_color=BG_HOVER,
                                        text_color=TEXT_DIM, height=30, corner_radius=15)
        self.btn_restage.pack(fill="x", pady=(10, 0))

        self.lbl_status = ctk.CTkLabel(self.card, text="Ready to process data", text_color=TEXT_DIM, font=("Segoe UI", 11))
        self.lbl_status.pack(pady=(15, 0))

        self.lbl_integrity = ctk.CTkLabel(self.card, text="Data Health: Waiting for selection...", font=("Segoe UI", 12, "bold"), text_color=TEXT_DIM)
        self.lbl_integrity.pack(pady=5)

        self.progress = ctk.CTkProgressBar(self.card, progress_color=SNAP_YELLOW, height=6)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=30, pady=(15, 15))

        ctk.CTkButton(self.card, text=" Save Settings & Launch", image=assets.load_icon("save", size=(24, 24)), compound="left",
                      height=45, width=240, fg_color=SNAP_BLUE, hover_color="#007ACC", text_color="white",
                      font=("Segoe UI", 15, "bold"), corner_radius=22, command=self.save).pack(pady=10)
        
    def confirm_restage(self):
        """Asks for confirmation before overwriting staged data."""
        root_path = self.entry_root.get()
        if not root_path or not os.path.exists(root_path): return

        # Simple confirmation dialog
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Re-scan")
        dialog.geometry("400x200")
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Overwrite Staged Data?", font=("Segoe UI", 16, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="Existing 'staged_data' will be replaced with fresh logs.", text_color="gray", wraplength=350).pack(pady=10)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        def proceed():
            dialog.destroy()
            self.force_restage()

        ctk.CTkButton(btn_frame, text="Cancel", fg_color=BG_CARD, command=dialog.destroy).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="Proceed", fg_color=SNAP_RED, command=proceed).pack(side="left", expand=True, padx=5)

    def force_restage(self):
        root_path = self.entry_root.get()
        self.lbl_status.configure(text="⚡ Re-scanning local data...", text_color=SNAP_BLUE)
        self.downloader = MemoryDownloader(self.update_status, self.update_progress)
        
        def run():
            actual_root = self.downloader._find_snap_root(root_path)
            final_stage = os.path.join(actual_root, "staged_data")
            os.makedirs(final_stage, exist_ok=True)
            self.downloader._stage_all_data(actual_root, final_stage)
            self.after(0, self.save)

        threading.Thread(target=run, daemon=True).start()
    
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
            elif line.startswith("## "): ctk.CTkLabel(parent, text=line[3:], font=("Segoe UI", 14, "bold"), text_color=SNAP_YELLOW[1] if isinstance(SNAP_YELLOW, tuple) else SNAP_YELLOW, anchor="w").pack(fill="x", padx=15, pady=(15, 2))
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
                    line = line.replace("**", "") # FIX: Separated from font assignment
                    font = ("Segoe UI", 13, "bold")
                ctk.CTkLabel(parent, text=line, font=font, text_color=TEXT_DIM, justify="left", anchor="w", wraplength=400).pack(fill="x", padx=15, pady=1)

    def start_dl(self):
        zip_path = filedialog.askopenfilename(title="Select Snapchat 'mydata~*.zip'", filetypes=[("Snapchat Export", "*.zip")])
        if not zip_path: return
        dest_root = filedialog.askdirectory(title="Where should the data be stored?")
        if not dest_root: return
        self.downloader = MemoryDownloader(self.update_status, self.update_progress)
        self.is_downloading = True
        self.btn_dl.configure(text=" Cancel Process", image=assets.load_icon("x", size=(16, 16)), fg_color="#550000")
        def run_pipeline():
            success = self.downloader.process_data_package(zip_path, dest_root, download_memories=True)
            if success:
                actual_data_folder = self.downloader._find_snap_root(dest_root)
                self.after(0, lambda: self.entry_root.delete(0, "end"))
                self.after(0, lambda: self.entry_root.insert(0, actual_data_folder))
                self.after(0, self.save)
        threading.Thread(target=run_pipeline, daemon=True).start()

    def _build_input_row(self, parent, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x")
        entry = ctk.CTkEntry(frame, fg_color=BG_MAIN, border_color=BG_CARD, height=40, corner_radius=10)
        entry.insert(0, default_val)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(frame, text="", image=assets.load_icon("folder", size=(20, 20)), width=50, height=40, fg_color=BG_CARD, corner_radius=10, command=lambda: self._browse(entry)).pack(side="right")
        return entry

    def _browse(self, entry):
        p = filedialog.askdirectory()
        if p: entry.delete(0, "end"), entry.insert(0, p)

    def update_status(self, text): self.lbl_status.configure(text=text)
    def update_progress(self, val): self.progress.set(val)
    
    def save(self):
        root_path = self.entry_root.get()
        if not root_path or not os.path.exists(root_path):
            self.lbl_status.configure(text="❌ Invalid folder path", text_color=SNAP_RED)
            return
        
        staged_path = os.path.join(root_path, "staged_data")
        if not os.path.exists(staged_path):
            self.force_restage()
        else:
            self._finalize_save()
            
    def _finalize_save(self):
        self.app.cfg.save_config(self.entry_root.get(), self.app.cfg.get("memories_path"))
        chat_index, memories, profile = self.app.data_manager.reload()
        self.app.chat_index, self.app.memories, self.app.profile = chat_index, memories, profile
        
        report = self.app.data_manager.perform_integrity_check()
        chats_found = report['chats']['total'] - report['chats']['missing']
        self.lbl_integrity.configure(text=f"✅ Linked: {chats_found} Chats, {len(memories)} Memories", text_color="#2ECC71")
        self.lbl_status.configure(text="✅ Sync Complete", text_color="#2ECC71")

        if self.app.view_chat: self.app.view_chat.populate_friends(chat_index)
        if self.app.view_memories: self.app.view_memories.load_page(1)
        if self.app.view_profile: 
            self.app.view_profile.destroy()
            self.app.view_profile = None
        self.btn_dl.configure(text=" Select ZIP & Process", image=assets.load_icon("download-cloud", size=(20, 20)), fg_color=BG_CARD)
        print("✅ Data reloaded and UI refreshed.")