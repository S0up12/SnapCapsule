import customtkinter as ctk
from datetime import datetime
from ui.theme import *
from utils.assets import assets  # <--- NEW IMPORT

class ProfileView(ctk.CTkFrame):
    def __init__(self, parent, profile_data):
        super().__init__(parent, fg_color="transparent")
        self.profile = profile_data or {}
        
        # Pointers for global scroll handler
        self.map_scroll = None
        self.friends_scroll = None
        self.device_scroll = None
        self.name_scroll = None
        
        # Column Frames
        self.col_friends = None
        self.col_history = None
        self.col_travel = None
        
        self._setup_ui()

    def _setup_ui(self):
        # --- Main Grid Configuration (3 Columns) ---
        self.grid_columnconfigure(0, weight=1) # Friends
        self.grid_columnconfigure(1, weight=1) # History
        self.grid_columnconfigure(2, weight=1) # Travel
        self.grid_rowconfigure(1, weight=1)    # Content expands vertically

        # --- ROW 0: Identity & Stats (Spans all columns) ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=(20, 10))
        
        self._build_identity_card(top_frame)
        self._build_stats_row(top_frame)

        # --- ROW 1: Content Columns ---
        
        # 1. Left Column: Friends List
        self.col_friends = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=10)
        self.col_friends.grid(row=1, column=0, sticky="nsew", padx=(20, 5), pady=20)
        self.col_friends.grid_columnconfigure(0, weight=1)
        self.col_friends.grid_rowconfigure(1, weight=1) 

        # 2. Middle Column: History (Devices & Names)
        self.col_history = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=10)
        self.col_history.grid(row=1, column=1, sticky="nsew", padx=5, pady=20)
        self.col_history.grid_columnconfigure(0, weight=1)
        self.col_history.grid_rowconfigure(1, weight=1) # Devices expands
        self.col_history.grid_rowconfigure(3, weight=1) # Names expands

        # 3. Right Column: Travel Log
        self.col_travel = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=10)
        self.col_travel.grid(row=1, column=2, sticky="nsew", padx=(5, 20), pady=20)
        self.col_travel.grid_columnconfigure(0, weight=1)
        self.col_travel.grid_rowconfigure(1, weight=1)

        # --- Build Content ---
        self._build_friends_list()
        self._build_device_history()
        self._build_name_history()
        self._build_travel_log()

    # --- Helper to toggle Scrollbar ---
    def _create_list_container(self, parent):
        container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        return container

    def _build_identity_card(self, parent):
        basic = self.profile.get("basic", {})
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        card.pack(fill="x", pady=(0, 10))
        
        # Layout container for Icon + Text
        container = ctk.CTkFrame(card, fg_color="transparent")
        container.pack(fill="x", padx=20, pady=20)
        
        # User Icon
        icon_user = assets.load_icon("user", size=(60, 60))
        if icon_user:
            ctk.CTkLabel(container, text="", image=icon_user).pack(side="left", padx=(0, 20), anchor="n")
        
        # Text Info
        info_frame = ctk.CTkFrame(container, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(info_frame, text=basic.get("Name", "Unknown"), font=("Segoe UI", 24, "bold"), text_color=TEXT_MAIN).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(info_frame, text=f"@{basic.get('Username', '')}", font=("Segoe UI", 16), text_color=SNAP_YELLOW).pack(anchor="w", pady=(0, 5))
        
        info_text = f"Born: {basic.get('Creation Date', '')[:10]}   |   Country: {basic.get('Country', '')}"
        ctk.CTkLabel(info_frame, text=info_text, font=("Segoe UI", 14), text_color=TEXT_DIM, justify="left").pack(anchor="w", pady=(5, 0))

    def _build_stats_row(self, parent):
        eng = self.profile.get("engagement", {})
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=0)
        
        # You can add icons for stats if you wish, e.g., 'camera', 'message-square'
        self._stat_box(row, "Snaps Sent", eng.get("Snap Sends", 0))
        self._stat_box(row, "Snaps Received", eng.get("Snap Views", 0))
        self._stat_box(row, "Chats Sent", eng.get("Chats Sent", 0))

    def _stat_box(self, parent, title, value):
        f = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=10)
        f.pack(side="left", fill="x", expand=True, padx=5)
        
        ctk.CTkLabel(f, text=f"{value:,}", font=("Segoe UI", 22, "bold"), text_color=SNAP_BLUE).pack(pady=(15, 0))
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 12), text_color=TEXT_DIM).pack(pady=(0, 15))

    def _build_friends_list(self):
        count = self.profile.get("stats", {}).get("friends", 0)
        
        # Header with Icon
        header_frame = ctk.CTkFrame(self.col_friends, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        icon_users = assets.load_icon("users", size=(20, 20))
        if icon_users:
            ctk.CTkLabel(header_frame, text="", image=icon_users).pack(side="left", padx=(0, 8))
            
        ctk.CTkLabel(header_frame, text=f"Friends ({count})", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        # List
        self.friends_scroll = self._create_list_container(self.col_friends)
        self.friends_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 5))
        
        friends = sorted(self.profile.get("friends_list", []), key=lambda x: x.get("Display Name", "").lower())

        for f in friends:
            row = ctk.CTkFrame(self.friends_scroll, fg_color=BG_CARD, corner_radius=8)
            row.pack(fill="x", padx=5, pady=3)
            display = f.get("Display Name", "Unknown")
            user = f.get("Username", "")
            ctk.CTkLabel(row, text=display, font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN, anchor="w").pack(side="left", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"@{user}", font=("Segoe UI", 12), text_color=TEXT_DIM, anchor="e").pack(side="right", padx=10)

    def _build_device_history(self):
        # Header with Icon
        header_frame = ctk.CTkFrame(self.col_history, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        icon_phone = assets.load_icon("smartphone", size=(20, 20))
        if icon_phone:
            ctk.CTkLabel(header_frame, text="", image=icon_phone).pack(side="left", padx=(0, 8))
            
        ctk.CTkLabel(header_frame, text="Device History", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        # List
        self.device_scroll = self._create_list_container(self.col_history)
        self.device_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 10))

        history = self.profile.get("device_history", [])
        for dev in history:
            row = ctk.CTkFrame(self.device_scroll, fg_color=BG_CARD, corner_radius=6)
            row.pack(fill="x", padx=5, pady=2)
            model = f"{dev.get('Make', '')} {dev.get('Model', '')}"
            date = dev.get('Start Time', '')[:10]
            ctk.CTkLabel(row, text=model, font=("Segoe UI", 13, "bold"), anchor="w", text_color=TEXT_MAIN).pack(side="left", padx=10, pady=5)
            ctk.CTkLabel(row, text=date, font=("Segoe UI", 12), text_color=TEXT_DIM, anchor="e").pack(side="right", padx=10)

    def _build_name_history(self):
        # Header with Icon
        header_frame = ctk.CTkFrame(self.col_history, fg_color="transparent")
        header_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(10, 5))
        
        icon_file = assets.load_icon("file-text", size=(20, 20))
        if icon_file:
            ctk.CTkLabel(header_frame, text="", image=icon_file).pack(side="left", padx=(0, 8))
            
        ctk.CTkLabel(header_frame, text="Identity Evolution", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        # List
        self.name_scroll = self._create_list_container(self.col_history)
        self.name_scroll.grid(row=3, column=0, sticky="nsew", padx=5, pady=(5, 15))

        history = self.profile.get("name_history", [])
        for nc in history:
            row = ctk.CTkFrame(self.name_scroll, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=1)
            name = nc.get('Display Name', '')
            date = nc.get('Date', '')[:10]
            ctk.CTkLabel(row, text=f"“{name}”", font=("Segoe UI", 13), anchor="w", text_color=TEXT_MAIN).pack(side="left")
            ctk.CTkLabel(row, text=date, font=("Segoe UI", 12), text_color=TEXT_DIM, anchor="e").pack(side="right")

    def _build_travel_log(self):
        # Header with Icon
        header_frame = ctk.CTkFrame(self.col_travel, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        icon_globe = assets.load_icon("globe", size=(20, 20))
        if icon_globe:
            ctk.CTkLabel(header_frame, text="", image=icon_globe).pack(side="left", padx=(0, 8))
            
        ctk.CTkLabel(header_frame, text="Travel Log", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        
        # List
        self.map_scroll = self._create_list_container(self.col_travel)
        self.map_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=(5, 5))
        
        for p in self.profile.get("places", []):
            place_name = p.get("Place", "Unknown")
            location = p.get("Place Location", "")
            date = p.get("Date", "")[:10]
            
            row = ctk.CTkFrame(self.map_scroll, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=4)
            
            date_lbl = ctk.CTkLabel(row, text=date, width=85, text_color=TEXT_DIM, font=("Segoe UI", 11), fg_color=BG_CARD, corner_radius=6)
            date_lbl.pack(side="left", padx=(0, 10))
            
            txt_frame = ctk.CTkFrame(row, fg_color="transparent")
            txt_frame.pack(side="left", fill="x", expand=True)
            
            ctk.CTkLabel(txt_frame, text=place_name, text_color=TEXT_MAIN, anchor="w", font=("Segoe UI", 13, "bold")).pack(fill="x")
            if location: ctk.CTkLabel(txt_frame, text=location, text_color=TEXT_DIM, anchor="w", font=("Segoe UI", 11)).pack(fill="x")