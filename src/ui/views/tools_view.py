import customtkinter as ctk
import os
from ui.theme import *
from utils.assets import assets

class ToolsView(ctk.CTkFrame):
    def __init__(self, parent, config_manager, data_manager):
        super().__init__(parent, fg_color="transparent")
        self.cfg = config_manager
        self.data_manager = data_manager
        self.is_processing = False
        self.selected_tool_cmd = None
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

        # No tools added here for now - list remains empty but layout is preserved

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

        self.terminal = ctk.CTkTextbox(self.main_content, fg_color="#000", text_color="#2ECC71", 
                                       font=("Consolas", 11), corner_radius=10)
        self.terminal.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.terminal.configure(state="disabled")

        self.action_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.progress = ctk.CTkProgressBar(self.action_frame, progress_color=SNAP_YELLOW, height=8)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 15))

        self.btn_container = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.btn_container.pack(fill="x")

        self.btn_run = ctk.CTkButton(self.btn_container, text="Run Tool", fg_color=SNAP_BLUE, 
                                     hover_color="#007ACC", height=40, font=("Segoe UI", 13, "bold"))
        # Hidden initially until a tool is selected

    def log(self, message):
        self.terminal.configure(state="normal")
        self.terminal.insert("end", f"\n> {message}")
        self.terminal.see("end")
        self.terminal.configure(state="disabled")