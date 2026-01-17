import customtkinter as ctk
import os
import threading
import shutil
from pathlib import Path
from ui.theme import *
from utils.assets import assets
# Import from the new location in utils
from utils.repair import MediaRepairCore, EnvironmentManager 

class ToolsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager, data_manager):
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self.data_manager = data_manager
        self.repairer = None
        self.is_processing = False
        
        # Initialize repair core with FFmpeg environment path
        try:
            ffmpeg_path = EnvironmentManager.get_ffmpeg()
            self.repairer = MediaRepairCore(ffmpeg_path)
        except Exception as e:
            print(f"Repair tool initialization failed: {e}")

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, fg_color=BG_SIDEBAR, corner_radius=15)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)

        # Header using the new 'tool' icon
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        icon_tool = assets.load_icon("tool", size=(24, 24))
        ctk.CTkLabel(header, text="", image=icon_tool).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text="Media Repair Toolbox", font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN).pack(side="left")

        # Tool Description Card
        card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=12)
        card.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(card, text="Snapchat Media Restorer", font=("Segoe UI", 16, "bold"), text_color=SNAP_BLUE).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(card, text="Safely fixes .jpg files that are actually MP4s or have broken headers.\nOriginal files are moved to 'repair_backups' before replacement.", 
                     font=("Segoe UI", 12), text_color=TEXT_DIM, justify="left").pack(anchor="w", padx=20, pady=(0, 20))

        # Status & Progress
        self.lbl_status = ctk.CTkLabel(card, text="Ready", font=("Segoe UI", 12, "bold"), text_color=TEXT_DIM)
        self.lbl_status.pack(pady=(0, 5))

        self.progress = ctk.CTkProgressBar(card, progress_color=SNAP_YELLOW)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=40, pady=(0, 20))

        # Action Button
        self.btn_run = ctk.CTkButton(card, text="Start Repair Process", fg_color=SNAP_BLUE, hover_color="#007ACC",
                                     height=40, font=("Segoe UI", 13, "bold"), command=self.start_repair)
        self.btn_run.pack(pady=(0, 25))

    def start_repair(self):
        if self.is_processing: return
        
        # Try explicit memories path first
        target_dir = self.cfg.get("memories_path")
        
        # Fallback to data_root/memories if memories_path is not set
        if not target_dir or not os.path.exists(target_dir):
            root = self.cfg.get("data_root")
            if root and os.path.exists(root):
                potential_path = os.path.join(root, "memories")
                if os.path.exists(potential_path):
                    target_dir = potential_path
        
        if not target_dir or not os.path.exists(target_dir):
            self.lbl_status.configure(
                text="Error: Could not find media folder. Please set 'Media Storage' in Home or Settings.", 
                text_color=SNAP_RED
            )
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled")
        self.lbl_status.configure(text="Initializing...", text_color=TEXT_MAIN)
        threading.Thread(target=self._run_repair_logic, args=(Path(target_dir),), daemon=True).start()

    def _run_repair_logic(self, target_path):
        """Fail-safe logic to repair files in the source folder."""
        files = list(target_path.glob("*.jpg"))
        if not files:
            self.after(0, lambda: self.lbl_status.configure(text="No .jpg files found"))
            self.is_processing = False
            self.after(0, lambda: self.btn_run.configure(state="normal"))
            return

        # Fail-safe directories
        backup_dir = target_path / "repair_backups"
        temp_dir = target_path / "repair_temp"
        backup_dir.mkdir(exist_ok=True)
        temp_dir.mkdir(exist_ok=True)

        total = len(files)
        success_count = 0

        for i, file_p in enumerate(files):
            self.after(0, lambda i=i: (self.progress.set((i+1)/total), 
                                       self.lbl_status.configure(text=f"Processing: {file_p.name}")))
            
            try:
                with open(file_p, 'rb') as f:
                    header = f.read(32)
                
                ts = self.repairer.parse_date(file_p.name)
                repaired_path = None
                new_ext = ".jpg"

                if self.repairer.MP4_SIG in header:
                    repaired_path = temp_dir / f"{file_p.stem}.mp4"
                    if self.repairer.fix_video(file_p, repaired_path):
                        new_ext = ".mp4"
                elif not header.startswith(self.repairer.JPEG_SIG):
                    repaired_path = temp_dir / file_p.name
                    if not self.repairer.extract_jpg(file_p, repaired_path):
                        repaired_path = None

                # SAFE REPLACEMENT: Only act if the repaired file actually exists
                if repaired_path and repaired_path.exists():
                    # 1. Move original to backup
                    shutil.move(str(file_p), str(backup_dir / file_p.name))
                    # 2. Move fixed file to original folder (with potentially new extension)
                    final_dest = target_path / f"{file_p.stem}{new_ext}"
                    shutil.move(str(repaired_path), str(final_dest))
                    # 3. Restore original timestamp
                    if ts:
                        os.utime(final_dest, (ts, ts))
                    success_count += 1

            except Exception as e:
                print(f"Failed to process {file_p.name}: {e}")

        # Cleanup temp workspace
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            
        self.after(0, self._finalize_ui, success_count)

    def _finalize_ui(self, count):
        self.is_processing = False
        self.btn_run.configure(state="normal")
        self.lbl_status.configure(text=f"Done! {count} files fixed. Backups in 'repair_backups'", text_color="#2ECC71")
        # Refresh the app database so the new files show up in the gallery
        self.data_manager.reload()