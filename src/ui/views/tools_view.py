import customtkinter as ctk
import os
import threading
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
            self.log(f"Critical Error: FFmpeg not found. {e}")

        self._setup_ui()

    def _setup_ui(self):
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
        self.main_content.grid_rowconfigure(1, weight=1)

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

        # Run Button
        self.btn_run = ctk.CTkButton(self.action_frame, text="Run Tool", fg_color=SNAP_BLUE, 
                                     hover_color="#007ACC", height=40, font=("Segoe UI", 13, "bold"),
                                     command=self.execute_selected_tool)

        # Populate Tools via Doc Files
        self._add_tool_item(
            name="Media Integrity Restorer",
            doc_id="integrity_restorer",
            command=self.start_repair
        )

    def _add_tool_item(self, name, doc_id, command):
        frame = ctk.CTkFrame(self.tools_container, fg_color=BG_CARD, corner_radius=8)
        frame.pack(fill="x", pady=5, padx=5)
        
        btn = ctk.CTkButton(frame, text=name, anchor="w", fg_color="transparent", 
                            hover_color=BG_HOVER, text_color=TEXT_MAIN, height=45,
                            command=lambda: self.select_tool(name, doc_id, command), 
                            font=("Segoe UI", 13, "bold"))
        btn.pack(side="left", fill="x", expand=True, padx=5)

    def select_tool(self, name, doc_id, command):
        """Loads the tool description from disk and prepares execution."""
        if self.is_processing: return

        self.lbl_active_tool.configure(text=name)
        self.selected_tool_cmd = command
        
        # Load content from .md file
        doc_path = assets.get_tool_doc(doc_id)
        description = "Documentation file missing."
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                description = f.read()

        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.insert("end", f"{description}\n\nReady to proceed...")
        self.terminal.configure(state="disabled")
        
        self.btn_run.pack(pady=(5, 0))
        self.progress.set(0)

    def execute_selected_tool(self):
        if self.selected_tool_cmd and not self.is_processing:
            self.btn_run.pack_forget()
            self.selected_tool_cmd()

    def log(self, message):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"\n> {message}")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")

    def start_repair(self):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.insert("end", "INITIALIZING MEDIA SCAN...\n")
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
                    import shutil
                    shutil.move(str(file_p), str(backup_dir / file_p.name))
                    final_dest = file_p.parent / f"{file_p.stem}{new_ext}"
                    shutil.move(str(repaired_path), str(final_dest))
                    if ts: os.utime(final_dest, (ts, ts))
                    success_count += 1
                
                import shutil
                if temp_dir.exists(): shutil.rmtree(temp_dir)

            except Exception as e:
                self.after(0, lambda f=file_p.name, err=e: self.log(f"FAILED: {f} ({err})"))

        self.after(0, lambda: self.log(f"\nScan Complete. {success_count} files restored."))
        self._finish()

    def _finish(self):
        self.is_processing = False
        self.selected_tool_cmd = None
        self.data_manager.reload()