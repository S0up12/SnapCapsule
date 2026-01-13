import customtkinter as ctk
from datetime import datetime
from ui.theme import *
from utils.assets import assets

class ProfileView(ctk.CTkFrame):
    def __init__(self, parent, profile_data):
        super().__init__(parent, fg_color="transparent")
        self.profile = profile_data or {}
        
        # Standardized gutter for perfect alignment
        self.GUTTER = 15 
        
        # Pointers for global scroll handler
        self.map_scroll = None
        self.friends_scroll = None
        self.device_scroll = None
        self.name_scroll = None
        
        self._setup_ui()

    def _setup_ui(self):
        # Configure main layout grid (3 Equal Columns)
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="equal_cols")
        self.grid_rowconfigure(2, weight=1) # Detailed lists expand

        # --- SECTION 1: IDENTITY CARD (TOP) ---
        basic = self.profile.get("basic", {})
        id_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        id_card.grid(row=0, column=0, columnspan=3, sticky="nsew", 
                     padx=self.GUTTER, pady=(self.GUTTER, 0))
        
        id_inner = ctk.CTkFrame(id_card, fg_color="transparent")
        id_inner.pack(padx=25, pady=25, fill="x")
        
        icon_user = assets.load_icon("user", size=(64, 64))
        if icon_user:
            ctk.CTkLabel(id_inner, text="", image=icon_user).pack(side="left", padx=(0, 25))
        
        id_info = ctk.CTkFrame(id_inner, fg_color="transparent")
        id_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(id_info, text=basic.get("Name", "Unknown"), font=("Segoe UI", 26, "bold"), text_color=TEXT_MAIN).pack(anchor="w")
        
        # Username uses dynamic SNAP_YELLOW (Dark Gold in Light Mode)
        ctk.CTkLabel(id_info, text=f"@{basic.get('Username', '')}", font=("Segoe UI", 16), text_color=SNAP_YELLOW).pack(anchor="w", pady=(2, 8))
        
        # Info text uses dynamic TEXT_DIM for high contrast
        info_text = f"Born: {basic.get('Creation Date', '')[:10]}  •  Country: {basic.get('Country', '')}"
        ctk.CTkLabel(id_info, text=info_text, font=("Segoe UI", 13), text_color=TEXT_DIM).pack(anchor="w")

        # --- SECTION 2: SCORE STATS (MIDDLE) ---
        stats_container = ctk.CTkFrame(self, fg_color="transparent")
        stats_container.grid(row=1, column=0, columnspan=3, sticky="ew", padx=self.GUTTER/2, pady=self.GUTTER)
        stats_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="equal_cols")

        eng = self.profile.get("engagement", {})
        self._stat_box(stats_container, 0, "SNAPS SENT", eng.get("Snap Sends", 0))
        self._stat_box(stats_container, 1, "SNAPS RECEIVED", eng.get("Snap Views", 0))
        self._stat_box(stats_container, 2, "CHATS SENT", eng.get("Chats Sent", 0))

        # --- SECTION 3: DETAILED COLUMNS (BOTTOM) ---
        # 1. Friends Column
        self.col_friends = self._create_outer_column(0, f"Friends ({self.profile.get('stats', {}).get('friends', 0)})", "users")
        self.friends_scroll = self._create_scroll_container(self.col_friends)
        self._populate_friends()

        # 2. History Column
        self.col_history = self._create_outer_column(1, "Device History", "smartphone")
        self.device_scroll = self._create_scroll_container(self.col_history)
        self._populate_device_history()
        
        evol_header = ctk.CTkFrame(self.col_history, fg_color="transparent")
        evol_header.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(evol_header, text="Identity Evolution", font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        self.name_scroll = self._create_scroll_container(self.col_history, height=150)
        self._populate_name_history()

        # 3. Travel Column
        self.col_travel = self._create_outer_column(2, "Travel Log", "globe")
        self.map_scroll = self._create_scroll_container(self.col_travel)
        self._populate_travel_log()

    def _create_outer_column(self, col, title, icon_name):
        frame = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=12)
        p_left = self.GUTTER if col == 0 else self.GUTTER/2
        p_right = self.GUTTER if col == 2 else self.GUTTER/2
        frame.grid(row=2, column=col, sticky="nsew", padx=(p_left, p_right), pady=(0, self.GUTTER))
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        icon = assets.load_icon(icon_name, size=(20, 20))
        if icon: ctk.CTkLabel(header, text="", image=icon).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 16, "bold"), text_color=TEXT_MAIN).pack(side="left")
        return frame

    def _create_scroll_container(self, parent, height=None):
        if height:
            scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=height)
        else:
            scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scroll.grid_columnconfigure(0, weight=1)
        return scroll

    def _stat_box(self, parent, col, title, value):
        f = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        f.grid(row=0, column=col, sticky="nsew", padx=self.GUTTER/2)
        ctk.CTkLabel(f, text=f"{value:,}", font=("Segoe UI", 24, "bold"), text_color=SNAP_BLUE).pack(pady=(18, 2))
        ctk.CTkLabel(f, text=title, font=("Segoe UI", 11, "bold"), text_color=TEXT_DIM).pack(pady=(0, 18))

    def _populate_friends(self):
        friends = sorted(self.profile.get("friends_list", []), key=lambda x: x.get("Display Name", "").lower())
        for i, f in enumerate(friends):
            row = ctk.CTkFrame(self.friends_scroll, fg_color=BG_CARD, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            ctk.CTkLabel(row, text=f.get("Display Name", "Unknown"), font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(row, text=f"@{f.get('Username', '')}", font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="right", padx=15)

    def _populate_device_history(self):
        for i, dev in enumerate(self.profile.get("device_history", [])):
            row = ctk.CTkFrame(self.device_scroll, fg_color=BG_CARD, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            ctk.CTkLabel(row, text=f"{dev.get('Make', '')} {dev.get('Model', '')}", font=("Segoe UI", 13, "bold"), text_color=TEXT_MAIN).pack(side="left", padx=15, pady=10)
            ctk.CTkLabel(row, text=dev.get('Start Time', '')[:10], font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="right", padx=15)

    def _populate_name_history(self):
        for i, nc in enumerate(self.profile.get("name_history", [])):
            row = ctk.CTkFrame(self.name_scroll, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=10, pady=1)
            ctk.CTkLabel(row, text=f"“{nc.get('Display Name', '')}”", font=("Segoe UI", 13), text_color=TEXT_MAIN).pack(side="left")
            ctk.CTkLabel(row, text=nc.get('Date', '')[:10], font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="right")

    def _populate_travel_log(self):
        for i, p in enumerate(self.profile.get("places", [])):
            row = ctk.CTkFrame(self.map_scroll, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=5, pady=4)
            date_lbl = ctk.CTkLabel(row, text=p.get("Date", "")[:10], width=85, text_color=TEXT_DIM, font=("Segoe UI", 11, "bold"), fg_color=BG_CARD, corner_radius=6)
            date_lbl.pack(side="left", padx=(5, 12))
            txt_frame = ctk.CTkFrame(row, fg_color="transparent")
            txt_frame.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(txt_frame, text=p.get("Place", "Unknown"), text_color=TEXT_MAIN, anchor="w", font=("Segoe UI", 13, "bold")).pack(fill="x")
            if p.get("Place Location"): 
                ctk.CTkLabel(txt_frame, text=p.get("Place Location"), text_color=TEXT_DIM, anchor="w", font=("Segoe UI", 11)).pack(fill="x")