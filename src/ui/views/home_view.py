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

        ctk.CTkLabel(input_container, text="1. Extract Data from ZIP", font=("Segoe UI", 13, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", pady=(0, 5))
        
        dl_frame = ctk.CTkFrame(self.card, fg_color=BG_CARD, corner_radius=15, border_width=2, border_color=BG_HOVER)
        dl_frame.pack(fill="x", padx=30, pady=(10, 15), ipady=10)
        dl_frame.grid_columnconfigure(1, weight=1)
        
        icon_dl = assets.load_icon("download-cloud", size=(20, 20))
        self.btn_dl = ctk.CTkButton(dl_frame, text=" Select ZIP & Process", image=icon_dl, compound="left",
                                    command=self.start_dl, fg_color=BG_SIDEBAR, hover_color=BG_HOVER, 
                                    text_color=TEXT_MAIN, width=180, height=35, corner_radius=18)
        self.btn_dl.grid(row=0, column=0, padx=15, pady=10)
        self.lbl_status = ctk.CTkLabel(dl_frame, text="Ready to process archive", text_color=TEXT_DIM, font=("Segoe UI", 11))
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=10)

        # --- DATA INTEGRITY DASHBOARD ---
        self.integrity_frame = ctk.CTkFrame(self.card, fg_color=BG_MAIN, corner_radius=12)
        self.integrity_frame.pack(fill="x", padx=30, pady=10)
        
        self.lbl_integrity = ctk.CTkLabel(self.integrity_frame, text="Data Health: Waiting for extraction...", 
                                          font=("Segoe UI", 12, "bold"), text_color=TEXT_DIM)
        self.lbl_integrity.pack(pady=10)

        ctk.CTkLabel(input_container, text="Current Data Root:", font=("Segoe UI", 11, "bold"), text_color=TEXT_DIM, anchor="w").pack(fill="x", pady=(10, 0))
        self.entry_root = self._build_input_row(input_container, self.app.cfg.get("data_root"))

        self.progress = ctk.CTkProgressBar(self.card, progress_color=SNAP_YELLOW, height=6)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=30, pady=(20, 20))

        icon_save = assets.load_icon("save", size=(24, 24))
        ctk.CTkButton(self.card, text=" Save Settings & Launch", image=icon_save, compound="left",
                      height=45, width=240, fg_color=SNAP_BLUE, hover_color="#007ACC", text_color="white",
                      font=("Segoe UI", 15, "bold"), corner_radius=22, command=self.save).pack(pady=10)

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
                    line = line.replace("**", "")
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
        if p: 
            entry.delete(0, "end")
            entry.insert(0, p)

    def update_status(self, text): self.lbl_status.configure(text=text)
    def update_progress(self, val): self.progress.set(val)
    
    def save(self):
        root_path = self.entry_root.get()
        self.app.cfg.save_config(root_path, self.app.cfg.get("memories_path"))
        chat_index, memories, profile = self.app.data_manager.reload()
        self.app.chat_index, self.app.memories, self.app.profile = chat_index, memories, profile
        
        # Update Integrity UI
        report = self.app.data_manager.perform_integrity_check()
        chats_found = report['chats']['total'] - report['chats']['missing']
        mems_found = report['memories']['total'] - report['memories']['missing']
        
        if chats_found == 0 and mems_found == 0:
            self.lbl_integrity.configure(text="❌ No data found. Is 'staged_data' in root?", text_color=SNAP_RED)
        else:
            self.lbl_integrity.configure(text=f"✅ Linked: {chats_found} Chats, {mems_found} Memories", text_color="#2ECC71")

        if self.app.view_chat: self.app.view_chat.chat_list = chat_index; self.app.view_chat.populate_friends(chat_index)
        if self.app.view_memories: self.app.view_memories.memories = memories; self.app.view_memories._calculate_stats(); self.app.view_memories.load_page(1)
        if self.app.view_profile: 
            self.app.view_profile.destroy()
            self.app.view_profile = None
        self.btn_dl.configure(text=" Select ZIP & Process", image=assets.load_icon("download-cloud", size=(20, 20)), fg_color=BG_SIDEBAR)
        print("✅ Data reloaded and UI refreshed.")