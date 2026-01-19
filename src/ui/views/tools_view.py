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
        self.selected_tool_cmd = None
        
        try:
            ffmpeg_path = EnvironmentManager.get_ffmpeg()
            self.repairer = MediaRepairCore(ffmpeg_path)
        except Exception as e:
            # We delay the log until the terminal widget is initialized
            print(f"Repair core error: {e}")

        self._setup_ui()

    def _setup_ui(self):
        # Configure layout: Column 0 (Sidebar), Column 1 (Content)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR: TOOL LIST ---
        self.sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, width=280, corner_radius=15)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        self.sidebar.grid_propagate(False)
        
        ctk.CTkLabel(self.sidebar, text="Available Tools", font=("Segoe UI", 18, "bold"), 
                     text_color=TEXT_MAIN).pack(pady=(20, 10), padx=20, anchor="w")

        self.tools_container = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.tools_container.pack(fill="both", expand=True, padx=5, pady=5)

        # --- RIGHT CONTENT: TERMINAL & ACTIONS ---
        self.main_content = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=15)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(1, weight=1) # Terminal expands

        header = ctk.CTkFrame(self.main_content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.lbl_active_tool = ctk.CTkLabel(header, text="Select a tool to begin", 
                                            font=("Segoe UI", 20, "bold"), text_color=TEXT_MAIN)
        self.lbl_active_tool.pack(side="left")

        # Terminal View 
        self.terminal = ctk.CTkTextbox(self.main_content, fg_color="#000", text_color="#2ECC71", 
                                       font=("Consolas", 11), corner_radius=10)
        self.terminal.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.terminal.configure(state="disabled")

        # Progress Area
        self.action_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.progress = ctk.CTkProgressBar(self.action_frame, progress_color=SNAP_YELLOW, height=8)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 15))

        # Button container for action buttons
        self.btn_container = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.btn_container.pack(fill="x")

        self.btn_run = ctk.CTkButton(self.btn_container, text="Run Tool", fg_color=SNAP_BLUE, 
                                     hover_color="#007ACC", height=40, font=("Segoe UI", 13, "bold"),
                                     command=self.execute_selected_tool)
        
        self.btn_revert = ctk.CTkButton(self.btn_container, text="Revert Repairs", fg_color="transparent", 
                                        border_width=1, border_color=SNAP_RED, text_color=SNAP_RED,
                                        hover_color=BG_HOVER, height=40, font=("Segoe UI", 13, "bold"), 
                                        command=self.start_revert)

        # Populate Tools
        self._add_tool_item(
            name="Media Integrity Restorer",
            doc_id="integrity_restorer",
            command=self.start_repair,
            show_revert=True
        )

    def _add_tool_item(self, name, doc_id, command, show_revert=False):
        frame = ctk.CTkFrame(self.tools_container, fg_color=BG_CARD, corner_radius=8)
        frame.pack(fill="x", pady=5, padx=5)
        
        btn = ctk.CTkButton(frame, text=name, anchor="w", fg_color="transparent", 
                            hover_color=BG_HOVER, text_color=TEXT_MAIN, height=45,
                            command=lambda: self.select_tool(name, doc_id, command, show_revert), 
                            font=("Segoe UI", 13, "bold"))
        btn.pack(side="left", fill="x", expand=True, padx=5)

    def select_tool(self, name, doc_id, command, show_revert):
        if self.is_processing: return

        self.lbl_active_tool.configure(text=name)
        self.selected_tool_cmd = command
        
        # Load description from doc files if they exist
        doc_path = assets.get_tool_doc(doc_id)
        description = "Documentation file missing."
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                description = f.read()

        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.insert("end", f"{description}\n\nReady to proceed...")
        self.terminal.configure(state="disabled")
        
        # Show relevant buttons
        self.btn_revert.pack_forget()
        self.btn_run.pack(side="left", expand=True, padx=5)
        if show_revert:
            self.btn_revert.pack(side="left", expand=True, padx=5)
            
        self.progress.set(0)

    def execute_selected_tool(self):
        if self.selected_tool_cmd and not self.is_processing:
            self.selected_tool_cmd()

    def log(self, message):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"\n> {message}")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def _get_active_paths(self):
        paths = []
        root = self.cfg.get("data_root")
        if root:
            chat_p = os.path.join(root, "chat_media")
            if os.path.exists(chat_p): paths.append(Path(chat_p))
        
        mem_p = self.cfg.get("memories_path") or (os.path.join(root, "memories") if root else None)
        if mem_p and os.path.exists(mem_p): paths.append(Path(mem_p))
        return paths

    def start_repair(self):
        paths = self._get_active_paths()
        if not paths:
            self.log("Error: No data folders located.")
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled")
        self.btn_revert.configure(state="disabled")
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.insert("end", "INITIALIZING MEDIA SCAN...\n")
        self.terminal.configure(state="disabled")
        threading.Thread(target=self._run_repair_logic, args=(paths,), daemon=True).start()

    def start_revert(self):
        paths = self._get_active_paths()
        if not paths:
            self.log("Error: No folders located.")
            return

        self.is_processing = True
        self.btn_run.configure(state="disabled")
        self.btn_revert.configure(state="disabled")
        self.log("INITIALIZING ROLLBACK...")
        threading.Thread(target=self._run_revert_logic, args=(paths,), daemon=True).start()

    def _run_revert_logic(self, paths):
        total_restored = 0
        for p in paths:
            backup_dir = p / "repair_backups"
            if not backup_dir.exists(): continue

            backups = list(backup_dir.glob("*"))
            self.log(f"Reverting changes in {p.name}...")
            for original_file in backups:
                try:
                    # Clean up repaired files before restoring original
                    base_name = original_file.stem
                    for ext in [".jpg", ".mp4", ".mp3"]:
                        candidate = p / f"{base_name}{ext}"
                        if candidate.exists() and candidate.resolve() != original_file.resolve():
                            os.remove(candidate)

                    shutil.move(str(original_file), str(p / original_file.name))
                    self.log(f"RESTORED: {original_file.name}")
                    total_restored += 1
                except Exception as e:
                    self.log(f"REVERT FAILED: {original_file.name} ({e})")

            try:
                if not any(backup_dir.iterdir()): shutil.rmtree(backup_dir)
            except: pass

        self.after(0, lambda: self.log(f"\nRollback Complete. {total_restored} files reverted."))
        self.after(0, self._finish)

    def _run_repair_logic(self, paths):
        """Processes files by folder and type with corrected progress tracking."""
        all_files_to_process = []
        for p in paths:
            # Pre-scan all directories to get an accurate total count
            all_files_to_process.extend([(p, f) for f in p.glob("*.jpg")])
            all_files_to_process.extend([(p, f) for f in p.glob("*.mp4")])
        
        total_files = len(all_files_to_process)
        if total_files == 0:
            self.after(0, lambda: self.log("No media files found to analyze."))
            self._finish()
            return

        total_actions = 0
        self.after(0, lambda: self.progress.set(0))

        # Process the pre-scanned list
        for i, (dir_path, file_p) in enumerate(all_files_to_process):
            # Calculate progress based on the position in the total list
            current_progress = (i + 1) / total_files
            self.after(0, lambda p=current_progress: self.progress.set(p))
            
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
                        if m_type in ['video', 'unknown']:
                            repaired_path = temp_dir / f"{file_p.stem}.mp4"; new_ext = ".mp4"
                            if not self.repairer.fix_video(file_p, repaired_path): repaired_path = None
                        elif m_type == 'audio':
                            repaired_path = temp_dir / f"{file_p.stem}.mp3"; new_ext = ".mp3"
                            if not self.repairer.fix_audio(file_p, repaired_path): repaired_path = None
                    elif not header.startswith(self.repairer.JPEG_SIG):
                        repaired_path = temp_dir / file_p.name
                        if not self.repairer.extract_jpg(file_p, repaired_path): repaired_path = None

                elif file_p.suffix.lower() == ".mp4":
                    m_type = self.repairer.check_media_type(file_p)
                    if m_type == 'audio':
                        repaired_path = temp_dir / f"{file_p.stem}.mp3"; new_ext = ".mp3"
                        if not self.repairer.fix_audio(file_p, repaired_path): repaired_path = None
                    elif m_type in ['video', 'unknown']:
                        repaired_path = temp_dir / f"{file_p.stem}_fixed.mp4"; new_ext = ".mp4"
                        if self.repairer.fix_video(file_p, repaired_path):
                            preview_path = file_p.parent / f"{file_p.stem}_image.jpg"
                            if not preview_path.exists():
                                from utils.image_utils import extract_video_thumbnail
                                thumb = extract_video_thumbnail(str(repaired_path))
                                if thumb: thumb.save(preview_path, "JPEG")
                        else: repaired_path = None

                if repaired_path and repaired_path.exists():
                    self.after(0, lambda f=file_p.name, e=new_ext: self.log(f"FIXED: {f} -> {e}"))
                    shutil.move(str(file_p), str(backup_dir / file_p.name))
                    final_dest = file_p.parent / f"{file_p.stem}{new_ext}"
                    shutil.move(str(repaired_path), str(final_dest))
                    # Metadata preservation: Restore the original timestamp
                    if ts: os.utime(final_dest, (ts, ts))
                    total_actions += 1
                
                if temp_dir.exists(): shutil.rmtree(temp_dir)
            except Exception:
                self.after(0, lambda f=file_p.name: self.log(f"SKIP: {f}"))

        self.after(0, lambda: self.log(f"\nTOTAL ACTIONS: {total_actions}"))
        self._finish()