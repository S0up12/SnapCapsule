import customtkinter as ctk
import os
import threading
import shutil
from pathlib import Path
from ui.theme import *
from utils.assets import assets
from utils.repair import MediaRepairCore, EnvironmentManager

class ToolsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager, data_manager):
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self.data_manager = data_manager
        self.repairer = None
        self.is_processing = False
        
        try:
            ffmpeg_path = EnvironmentManager.get_ffmpeg()
            self.repairer = MediaRepairCore(ffmpeg_path)
        except Exception as e:
            self.log(f"Critical Error: FFmpeg not found. {e}")

        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        container = ctk.CTkScrollableFrame(self, fg_color=BG_SIDEBAR, corner_radius=15)
        container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        container.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(header, text="", image=assets.load_icon("tool", size=(24, 24))).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text="System Repair Tools", font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN).pack(side="left")

        # Repair Card
        card = ctk.CTkFrame(container, fg_color=BG_CARD, corner_radius=12)
        card.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(card, text="Media Integrity Restorer", font=("Segoe UI", 16, "bold"), text_color=SNAP_BLUE).pack(anchor="w", padx=20, pady=(20, 5))
        desc = ("Scans Chat Media and Memories for corrupt files.\n"
                "• Fixes videos incorrectly named as .jpg\n"
                "• Extracts audio notes incorrectly named as .mp4\n"
                "• Repairs broken JPEG headers\n"
                "Safety: Originals are backed up to 'repair_backups' folders.")
        ctk.CTkLabel(card, text=desc, font=("Segoe UI", 12), text_color=TEXT_DIM, justify="left").pack(anchor="w", padx=20, pady=(0, 20))

        # Terminal Log
        self.terminal = ctk.CTkTextbox(card, height=200, fg_color="#000", text_color="#2ECC71", font=("Consolas", 11))
        self.terminal.pack(fill="x", padx=20, pady=10)
        self.terminal.configure(state="disabled")

        self.progress = ctk.CTkProgressBar(card, progress_color=SNAP_YELLOW)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=20, pady=10)

        self.btn_run = ctk.CTkButton(card, text="Run Deep Scan & Repair", fg_color=SNAP_BLUE, hover_color="#007ACC",
                                     height=40, font=("Segoe UI", 13, "bold"), command=self.start_repair)
        self.btn_run.pack(pady=(0, 25))

    def log(self, message):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"> {message}\n")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def start_repair(self):
        if self.is_processing: return
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")
        
        paths = []
        root = self.cfg.get("data_root")
        if root:
            chat_p = os.path.join(root, "chat_media")
            if os.path.exists(chat_p): paths.append(Path(chat_p))
        
        mem_p = self.cfg.get("memories_path") or (os.path.join(root, "memories") if root else None)
        if mem_p and os.path.exists(mem_p): paths.append(Path(mem_p))

        if not paths:
            self.log("Error: No data folders located. Please check Home settings.")
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled")
        threading.Thread(target=self._run_repair_logic, args=(paths,), daemon=True).start()

    def _run_repair_logic(self, paths):
        all_files = []
        for p in paths:
            all_files.extend(list(p.glob("*.jpg")) + list(p.glob("*.mp4")))
        
        if not all_files:
            self.after(0, lambda: self.log("No media files found to analyze."))
            self._finish()
            return

        total = len(all_files)
        success_count = 0

        for i, file_p in enumerate(all_files):
            self.after(0, lambda i=i: self.progress.set((i+1)/total))
            try:
                ts = self.repairer.parse_date(file_p.name)
                repaired_path = None
                new_ext = file_p.suffix.lower()
                temp_dir = file_p.parent / "repair_temp"
                backup_dir = file_p.parent / "repair_backups"
                temp_dir.mkdir(exist_ok=True); backup_dir.mkdir(exist_ok=True)

                if file_p.suffix.lower() == ".jpg":
                    with open(file_p, 'rb') as f: header = f.read(32)
                    if self.repairer.MP4_SIG in header:
                        m_type = self.repairer.check_media_type(file_p)
                        if m_type == 'video':
                            repaired_path = temp_dir / f"{file_p.stem}.mp4"; new_ext = ".mp4"
                            if not self.repairer.fix_video(file_p, repaired_path): repaired_path = None
                        else:
                            repaired_path = temp_dir / f"{file_p.stem}.mp3"; new_ext = ".mp3"
                            if not self.repairer.fix_audio(file_p, repaired_path): repaired_path = None
                    elif not header.startswith(self.repairer.JPEG_SIG):
                        repaired_path = temp_dir / file_p.name
                        if not self.repairer.extract_jpg(file_p, repaired_path): repaired_path = None

                elif file_p.suffix.lower() == ".mp4":
                    if self.repairer.check_media_type(file_p) == 'audio':
                        repaired_path = temp_dir / f"{file_p.stem}.mp3"; new_ext = ".mp3"
                        if not self.repairer.fix_audio(file_p, repaired_path): repaired_path = None

                if repaired_path and repaired_path.exists():
                    self.after(0, lambda f=file_p.name, e=new_ext: self.log(f"FIXED: {f} -> {e}"))
                    shutil.move(str(file_p), str(backup_dir / file_p.name))
                    final_dest = file_p.parent / f"{file_p.stem}{new_ext}"
                    shutil.move(str(repaired_path), str(final_dest))
                    if ts: os.utime(final_dest, (ts, ts))
                    success_count += 1
                
                if temp_dir.exists(): shutil.rmtree(temp_dir)

            except Exception as e:
                self.after(0, lambda f=file_p.name, err=e: self.log(f"FAILED: {f} ({err})"))

        self.after(0, lambda: self.log(f"\nScan Complete. {success_count} files restored."))
        self._finish()

    def _finish(self):
        self.is_processing = False
        self.btn_run.configure(state="normal")
        self.data_manager.reload()