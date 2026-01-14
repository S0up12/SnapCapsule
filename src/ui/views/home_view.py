import customtkinter as ctk
import os
import threading
import webbrowser
from tkinter import filedialog
from utils.downloader import MemoryDownloader
from ui.theme import *
from utils.assets import assets
from utils.logger import get_logger

logger = get_logger(__name__)

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
        container.pack_propagate(False)
        
        self.card = ctk.CTkFrame(container, fg_color=BG_SIDEBAR, corner_radius=25, width=600)
        self.card.pack(expand=True, fill="both", padx=10, pady=10)

        # LOGO
        logo_img = assets.load_image("snapcapsule", size=(100, 100))
        if logo_img:
            ctk.CTkLabel(self.card, text="", image=logo_img).pack(pady=(20, 0))
        else:
            icon_ghost = assets.load_icon("ghost", size=(60,60)) 
            if icon_ghost:
                ctk.CTkLabel(self.card, text="", image=icon_ghost).pack(pady=(20, 0))
            else:
                ctk.CTkLabel(self.card, text="👻", font=("Segoe UI", 50)).pack(pady=(20, 0))
            
        ctk.CTkLabel(self.card, text="SnapCapsule", font=("Segoe UI", 28, "bold"), text_color=TEXT_MAIN).pack(pady=(0, 5))
        ctk.CTkLabel(self.card, text="Your digital time capsule, purely local.", font=("Segoe UI", 14), text_color=TEXT_DIM).pack(pady=(0, 20))

        # INPUTS
        input_container = ctk.CTkFrame(self.card, fg_color="transparent")
        input_container.pack(fill="x", padx=30) 

        ctk.CTkLabel(input_container, text="1. Select Snapchat Data Folder (Unzipped)", font=("Segoe UI", 13, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", pady=(0, 5))
        self.entry_root = self._build_input_row(input_container, self.app.cfg.get("data_root"))
        
        ctk.CTkFrame(input_container, fg_color="transparent", height=15).pack()

        ctk.CTkLabel(input_container, text="2. Memories Folder (Optional)", font=("Segoe UI", 13, "bold"), text_color=SNAP_BLUE, anchor="w").pack(fill="x", pady=(0, 5))
        self.entry_dest = self._build_input_row(input_container, self.app.cfg.get("memories_path"))

        # DOWNLOAD
        dl_frame = ctk.CTkFrame(self.card, fg_color=BG_CARD, corner_radius=15, border_width=2, border_color=BG_HOVER)
        dl_frame.pack(fill="x", padx=30, pady=(20, 15), ipady=10)
        dl_frame.grid_columnconfigure(1, weight=1)
        
        icon_dl = assets.load_icon("download-cloud", size=(20, 20))
        self.btn_dl = ctk.CTkButton(dl_frame, text=" Download Memories", image=icon_dl, compound="left",
                                    command=self.toggle_download, fg_color=BG_SIDEBAR, hover_color=BG_HOVER, 
                                    text_color=TEXT_MAIN, width=180, height=35, corner_radius=18, border_width=1, border_color=BG_HOVER)
        self.btn_dl.grid(row=0, column=0, padx=15, pady=10)
        
        self.lbl_status = ctk.CTkLabel(dl_frame, text="Ready to fetch missing files", text_color=TEXT_DIM, font=("Segoe UI", 11))
        self.lbl_status.grid(row=0, column=1, sticky="w", padx=10)
        
        self.progress = ctk.CTkProgressBar(self.card, progress_color=SNAP_YELLOW, height=6)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=30, pady=(0, 20))

        # FOOTER
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
        if not os.path.exists(filename):
            ctk.CTkLabel(parent, text="Tutorial file not found.", text_color="red").pack()
            return

        with open(filename, "r", encoding="utf-8") as f:
            lines = f.readlines()

        icon_link = assets.load_icon("link", size=(16, 16))

        for line in lines:
            line = line.strip()
            if not line:
                ctk.CTkFrame(parent, fg_color="transparent", height=10).pack()
                continue
            
            if line.startswith("# "):
                ctk.CTkLabel(parent, text=line[2:], font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN, anchor="w").pack(fill="x", padx=15, pady=(10, 5))
            elif line.startswith("## "):
                # FIX: Uses standardized dynamic SNAP_YELLOW
                ctk.CTkLabel(parent, text=line[3:], font=("Segoe UI", 14, "bold"), text_color=SNAP_YELLOW, anchor="w").pack(fill="x", padx=15, pady=(15, 2))
            elif line.startswith("* "):
                ctk.CTkLabel(parent, text="• " + line[2:], font=("Segoe UI", 13), text_color=TEXT_DIM, justify="left", anchor="w", wraplength=400).pack(fill="x", padx=25, pady=1)
            elif line.startswith("[BUTTON:"):
                try:
                    end_idx = line.index("]")
                    url = line[8:end_idx]
                    label_text = line[end_idx+1:].strip()
                    ctk.CTkButton(parent, text=f" {label_text}", image=icon_link, compound="left", 
                                  height=30, fg_color=BG_CARD, hover_color=BG_HOVER, text_color=SNAP_BLUE,
                                  command=lambda u=url: webbrowser.open(u)).pack(anchor="w", padx=20, pady=5)
                except Exception:
                    logger.debug("Failed to render markdown button line: %s", line, exc_info=True)
            else:
                font = ("Segoe UI", 13)
                if "**" in line:
                    line = line.replace("**", "")
                    font = ("Segoe UI", 13, "bold")
                ctk.CTkLabel(parent, text=line, font=font, text_color=TEXT_DIM, justify="left", anchor="w", wraplength=400).pack(fill="x", padx=15, pady=1)

    def _build_input_row(self, parent, default_val):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x")
        
        # FIX: Removed hardcoded "white" text to support dynamic theme colors
        entry = ctk.CTkEntry(frame, fg_color=BG_MAIN, border_color=BG_CARD, height=40, corner_radius=10)
        entry.insert(0, default_val)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        icon_folder = assets.load_icon("folder", size=(20, 20))
        ctk.CTkButton(frame, text="", image=icon_folder, width=50, height=40, fg_color=BG_CARD, hover_color=BG_HOVER, corner_radius=10,
                      command=lambda: self._browse(entry)).pack(side="right")
        return entry

    def _browse(self, entry):
        p = filedialog.askdirectory()
        if p: 
            entry.delete(0, "end")
            entry.insert(0, p)

    def toggle_download(self):
        if self.is_downloading:
            if self.downloader:
                self.downloader.cancel()
                self.btn_dl.configure(text=" Stopping...", state="disabled")
        else:
            if not self.entry_dest.get().strip():
                self._ask_download_location()
            else:
                self.start_dl()

    def _ask_download_location(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Download Location")
        dialog.geometry("400x220")
        dialog.attributes("-topmost", True)
        
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
        y = self.winfo_rooty() + (self.winfo_height() // 2) - 110
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(dialog, text="Where to save?", font=("Segoe UI", 18, "bold")).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="You haven't selected a memories folder.", text_color="gray").pack(pady=(0, 20))

        def use_default():
            dialog.destroy()
            root = self.entry_root.get()
            if root:
                dest = os.path.join(root, "memories")
                self.entry_dest.delete(0, "end")
                self.entry_dest.insert(0, dest)
                self.start_dl()

        def browse_custom():
            dialog.destroy()
            p = filedialog.askdirectory()
            if p:
                self.entry_dest.delete(0, "end")
                self.entry_dest.insert(0, p)
                self.start_dl()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        # ICONS REPLACED HERE
        icon_star = assets.load_icon("shuffle", size=(16, 16)) # "Choose for me" often implies shuffling or magic
        icon_folder = assets.load_icon("folder", size=(16, 16))
        
        ctk.CTkButton(btn_frame, text=" Choose for Me", image=icon_star, compound="left", command=use_default, fg_color=SNAP_BLUE, height=40).pack(fill="x", pady=5)
        ctk.CTkButton(btn_frame, text=" Select Folder...", image=icon_folder, compound="left", command=browse_custom, fg_color=BG_CARD, hover_color=BG_HOVER, height=40).pack(fill="x", pady=5)

    def start_dl(self):
        root = self.entry_root.get()
        dest = self.entry_dest.get()
        
        if not root or not os.path.exists(root):
             self.lbl_status.configure(text="Invalid Data Source Folder")
             return

        json_p = os.path.join(root, "json", "memories_history.json")
        if not os.path.exists(json_p):
             self.lbl_status.configure(text="memories_history.json not found")
             return

        self.downloader = MemoryDownloader(self.update_status, self.update_progress)
        self.is_downloading = True
        
        # Icon for Cancel
        icon_x = assets.load_icon("x", size=(16, 16))
        self.btn_dl.configure(text=" Cancel Download", image=icon_x, fg_color="#550000", hover_color="#770000")
        
        threading.Thread(target=self.downloader.download_memories, args=(json_p, dest), daemon=True).start()

    def update_status(self, text):
        # NOTE: Downloader sends text with emojis. We allow this for status messages as they are text strings.
        self.lbl_status.configure(text=text)

    def update_progress(self, val):
        self.progress.set(val)
        if val >= 1.0 or (val == 0.0 and self.is_downloading): 
            self.after(1000, self.reset_ui_state)

    def reset_ui_state(self):
        self.is_downloading = False
        icon_dl = assets.load_icon("download-cloud", size=(20, 20))
        self.btn_dl.configure(text=" Download Memories", image=icon_dl, fg_color=BG_SIDEBAR, hover_color=BG_HOVER, state="normal")

    def save(self):
        # 1. Save the new paths to config.json
        self.app.cfg.save_config(self.entry_root.get(), self.entry_dest.get())
        
        # 2. Reload data from the new paths
        # DataManager.reload returns (chat_index, memories, profile)
        chat_index, memories, profile = self.app.data_manager.reload()
        
        # 3. Update the main application state
        self.app.chat_index = chat_index
        self.app.memories = memories
        self.app.profile = profile
        
        # 4. Refresh individual views if they exist
        if self.app.view_chat: 
            # Corrected: Pass the list (chat_index), not a dict.keys() call
            self.app.view_chat.chat_list = chat_index
            self.app.view_chat.populate_friends(chat_index)
            
        if self.app.view_memories: 
            self.app.view_memories.memories = memories
            # Refresh the memory view layout
            for w in self.app.view_memories.winfo_children():
                w.destroy()
            self.app.view_memories._setup_ui()

        if self.app.view_profile:
            # Simplest way to refresh profile is to destroy and let it recreate
            self.app.view_profile.destroy()
            self.app.view_profile = None
            
        logger.info("Configuration saved and data reloaded")
