import customtkinter as ctk
from PIL import Image, ImageOps
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from utils.image_utils import extract_video_thumbnail, add_play_icon
from ui.theme import *
from ui.components.media_viewer import GlobalMediaPlayer
from utils.assets import assets

class SidebarChatButton(ctk.CTkFrame):
    def __init__(self, parent, display_name, username, command):
        super().__init__(parent, fg_color="transparent", corner_radius=6)
        self.command = command
        self.is_selected = False
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # Name
        self.name_lbl = ctk.CTkLabel(self, text=display_name, font=("Segoe UI", 14, "bold"), text_color=TEXT_MAIN, anchor="w")
        self.name_lbl.pack(fill="x", padx=10, pady=(8, 0))
        
        # Username
        self.user_lbl = ctk.CTkLabel(self, text=f"@{username}", font=("Segoe UI", 11), text_color=TEXT_DIM, anchor="w")
        self.user_lbl.pack(fill="x", padx=10, pady=(0, 8))
        
        for w in [self.name_lbl, self.user_lbl]:
            w.bind("<Button-1>", self.on_click)
            w.bind("<Enter>", self.on_enter)
            w.bind("<Leave>", self.on_leave)

    def on_click(self, event=None):
        if self.command: self.command()

    def on_enter(self, event=None):
        if not self.is_selected: self.configure(fg_color=BG_HOVER)

    def on_leave(self, event=None):
        if not self.is_selected: self.configure(fg_color="transparent")

    def set_selected(self, selected):
        self.is_selected = selected
        self.configure(fg_color=BG_CARD if selected else "transparent")

class ChatBubble(ctk.CTkFrame):
    def __init__(self, parent, message, is_me, friend_name, executor, alive_flag, media_callback):
        super().__init__(parent, fg_color="transparent")
        self.pack(pady=5, padx=20, anchor="w", fill="x")
        self.executor = executor
        self.alive_flag = alive_flag
        self.media_callback = media_callback
        
        accent_color = SNAP_RED if is_me else SNAP_BLUE
        sender_text = "ME" if is_me else friend_name.upper()
        
        # Header
        name_lbl = ctk.CTkLabel(self, text=sender_text, font=("Segoe UI", 11, "bold"), text_color=accent_color, anchor="w")
        name_lbl.pack(fill="x", anchor="w")
        
        # Body Container
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="x", anchor="w")
        
        # Colored Line
        bar = ctk.CTkFrame(body_frame, width=3, fg_color=accent_color, height=20, corner_radius=0)
        bar.pack(side="left", fill="y", padx=(0, 10))
        
        # Content
        content_container = ctk.CTkFrame(body_frame, fg_color="transparent")
        content_container.pack(side="left", fill="x")

        # Text
        if message['text']:
            ctk.CTkLabel(content_container, text=message['text'], font=("Segoe UI", 14), 
                         text_color="#E0E0E0", justify="left", anchor="w", wraplength=500).pack(anchor="w")

        # Media Grid
        if message['media']:
            for path in message['media']:
                self.render_media_placeholder(content_container, path)

        # Time Hover
        try:
            dt = datetime.strptime(message['date'], "%Y-%m-%d %H:%M")
            time_str = dt.strftime("%H:%M")
        except: time_str = ""
        self.time_lbl = ctk.CTkLabel(body_frame, text=time_str, font=("Segoe UI", 10), text_color="#555555")
        
        for w in [self, body_frame, content_container]:
            w.bind("<Enter>", lambda e: self.time_lbl.pack(side="left", padx=(10, 0)))
            w.bind("<Leave>", lambda e: self.time_lbl.pack_forget())

    def render_media_placeholder(self, parent, path):
        btn = ctk.CTkButton(parent, text="Loading...", width=200, height=150, 
                            fg_color="#111", hover=False, state="disabled", corner_radius=10)
        btn.pack(pady=5, anchor="w")
        # Async Load
        self.executor.submit(self._load_job, path, btn)

    def _load_job(self, path, btn_widget):
        if not self.alive_flag[0]: return
        try:
            ext = os.path.splitext(path)[1].lower()
            pil_img = None
            is_video = False
            
            if ext in ['.jpg', '.jpeg', '.png']:
                pil_img = Image.open(path)
                pil_img.thumbnail((300, 400))
            elif ext in ['.mp4', '.mov', '.avi']:
                is_video = True
                pil_img = extract_video_thumbnail(path)
                if pil_img: pil_img.thumbnail((300, 400))
            
            if self.alive_flag[0]:
                if pil_img:
                    if is_video: pil_img = add_play_icon(pil_img)
                    btn_widget.after(0, lambda: self._apply_image_main_thread(btn_widget, pil_img, path))
                else:
                    btn_widget.after(0, lambda: self._apply_error_main_thread(btn_widget, is_video, path))
        except Exception:
            pass

    def _apply_image_main_thread(self, btn, pil_img, path):
        if not btn.winfo_exists(): return
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        btn.configure(text="", image=ctk_img, state="normal", width=pil_img.size[0], height=pil_img.size[1],
                      command=lambda: self.media_callback(path))

    def _apply_error_main_thread(self, btn, is_video, path):
        if not btn.winfo_exists(): return
        if is_video:
            icon = assets.load_icon("video", size=(24, 24))
            btn.configure(text=" Play Video", image=icon, compound="left", state="normal", 
                          command=lambda: self.media_callback(path))
        else:
            icon = assets.load_icon("alert-triangle", size=(24, 24))
            btn.configure(text=" Missing File", image=icon, compound="left", fg_color="#330000")

class ChatView(ctk.CTkFrame):
    def __init__(self, parent, data_manager, profile_data=None):
        super().__init__(parent, fg_color="transparent")
        self.data_manager = data_manager # Reference to DataManager for lazy loading
        self.chat_list = data_manager.chat_index # Just the names
        self.profile = profile_data or {}
        
        self.current_messages = [] # Holds currently loaded chat msgs
        self.current_friend_key = None
        
        self.WINDOW_SIZE = 50   
        self.STEP_SIZE = 25     
        self.view_start = 0     
        self.view_end = 0       
        self.total_msgs = 0     
        
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_active = [True]
        
        self.friend_map = self._build_friend_map()
        self.active_btn = None 
        
        self._setup_ui()

    def cleanup(self):
        self.is_active[0] = False
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_active = [True]

    def _build_friend_map(self):
        mapping = {}
        friends_list = self.profile.get("friends_list", [])
        for key in self.chat_list:
            details = {"display": key, "username": key}
            # Try to find friend details
            for f in friends_list:
                f_disp = f.get("Display Name", "")
                f_user = f.get("Username", "")
                if key == f_disp or key == f_user:
                    details["display"] = f_disp
                    details["username"] = f_user
                    break
            mapping[key] = details
        return mapping

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=300) 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, width=300)
        sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Search
        search_frame = ctk.CTkFrame(sidebar, fg_color=BG_MAIN, corner_radius=20, height=40)
        search_frame.pack(fill="x", padx=15, pady=15)
        search_frame.pack_propagate(False)
        
        icon_search = assets.load_icon("search", size=(16, 16))
        ctk.CTkLabel(search_frame, text="", image=icon_search).pack(side="left", padx=(15, 5))
        
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search...", 
                                  fg_color="transparent", border_width=0, 
                                  text_color=TEXT_MAIN, height=35, font=("Segoe UI", 13))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self.update_search)
        
        # Friends List
        self.scroll_friends = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.scroll_friends.pack(fill="both", expand=True)
        self.populate_friends(self.chat_list)

        # Right Panel (Chat)
        self.right_panel = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.right_panel.grid(row=0, column=1, sticky="nsew")
        
        self.header_frame = ctk.CTkFrame(self.right_panel, fg_color=BG_SIDEBAR, height=70, corner_radius=0)
        self.header_frame.pack(fill="x")
        
        header_con = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_con.pack(side="left", padx=20, pady=10)
        
        self.lbl_name = ctk.CTkLabel(header_con, text="Select a chat", font=("Segoe UI", 18, "bold"), text_color=TEXT_MAIN, anchor="w")
        self.lbl_name.pack(anchor="w")
        self.lbl_user = ctk.CTkLabel(header_con, text="", font=("Segoe UI", 12), text_color=TEXT_DIM, anchor="w")
        self.lbl_user.pack(anchor="w")
        
        self.scroll_chat = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_chat.pack(fill="both", expand=True)

    def show_media(self, path):
        if not os.path.exists(path): return
        
        # Collect playlist from CURRENT loaded messages
        playlist = []
        for msg in self.current_messages:
            if msg['media']:
                for p in msg['media']:
                    playlist.append(p)
        
        try:
            idx = playlist.index(path)
        except ValueError:
            idx = 0
            playlist = [path]
            
        GlobalMediaPlayer(self, playlist, idx)

    def update_search(self, event=None):
        q = self.search_entry.get().lower()
        if not q:
            self.populate_friends(self.chat_list)
        else:
            # Filter friends
            filtered = [n for n in self.chat_list if q in n.lower()]
            self.populate_friends(filtered)

    def populate_friends(self, chat_keys):
        # Optimization: Don't destroy all widgets if list is same, but for now strict redraw is safer
        for w in self.scroll_friends.winfo_children(): w.destroy()
        
        # Limit rendered list for performance (Lazy Render Sidebar could be next step, but 100 limit is fine)
        limit = 100 
        for key in chat_keys[:limit]: 
            info = self.friend_map.get(key, {"display": key, "username": key})
            btn = SidebarChatButton(self.scroll_friends, info["display"], info["username"], lambda k=key: self.load_chat(k))
            btn.pack(fill="x", pady=2, padx=5)
            btn.chat_key = key
            
            if self.current_friend_key == key:
                btn.set_selected(True)
                self.active_btn = btn

    def load_chat(self, chat_key):
        self.cleanup()
        
        # UI Selection Update
        if self.active_btn: self.active_btn.set_selected(False)
        for widget in self.scroll_friends.winfo_children():
            if hasattr(widget, 'chat_key') and widget.chat_key == chat_key:
                widget.set_selected(True)
                self.active_btn = widget
                break

        self.current_friend_key = chat_key
        
        # --- LAZY LOAD HERE ---
        self.current_messages = self.data_manager.get_chat_messages(chat_key)
        # ----------------------
        
        self.total_msgs = len(self.current_messages)
        self.view_end = self.total_msgs
        self.view_start = max(0, self.view_end - self.WINDOW_SIZE)
        
        info = self.friend_map.get(chat_key, {"display": chat_key, "username": chat_key})
        self.lbl_name.configure(text=info["display"])
        self.lbl_user.configure(text=f"@{info['username']}")
        
        self.render_window(scroll_pos=1.0) 

    def load_older(self):
        self.view_start = max(0, self.view_start - self.STEP_SIZE)
        self.view_end = min(self.total_msgs, self.view_start + self.WINDOW_SIZE)
        self.render_window(scroll_pos=0.0) # Keep scroll at top

    def load_newer(self):
        self.view_end = min(self.total_msgs, self.view_end + self.STEP_SIZE)
        self.view_start = max(0, self.view_end - self.WINDOW_SIZE)
        self.render_window(scroll_pos=1.0) # Keep scroll at bottom

    def render_window(self, scroll_pos=1.0):
        # Clear chat area
        for w in self.scroll_chat.winfo_children(): w.destroy()
        
        # Slice messages
        msgs = self.current_messages[self.view_start : self.view_end]
        
        # "Load Older" Button
        if self.view_start > 0:
            icon_up = assets.load_icon("arrow-up", size=(16, 16))
            ctk.CTkButton(self.scroll_chat, text=" Load Older", image=icon_up, compound="left",
                          width=200, height=35, fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_MAIN,
                          command=self.load_older).pack(pady=(20, 10))

        last_date = ""
        info = self.friend_map.get(self.current_friend_key, {"display": self.current_friend_key})
        
        for i, msg in enumerate(msgs):
            # Skip empty messages (no text/media)
            if not msg['text'] and not msg['media']: continue
            
            # Date Separator
            d = msg['date'].split(" ")[0]
            if d != last_date:
                f = ctk.CTkFrame(self.scroll_chat, fg_color="transparent")
                f.pack(pady=(20, 10), fill="x")
                try:
                    date_obj = datetime.strptime(d, "%Y-%m-%d")
                    date_txt = date_obj.strftime("%B %d").upper()
                except: date_txt = d
                
                ctk.CTkLabel(f, text=date_txt, font=("Segoe UI", 10, "bold"), text_color="#666").pack()
                last_date = d
            
            is_me = (msg['sender'] != self.current_friend_key)
            ChatBubble(self.scroll_chat, msg, is_me, info["display"], self.executor, self.is_active, 
                       media_callback=self.show_media)
            
            # Allow UI to breathe every few messages
            if i % 10 == 0: self.update()

        # "Load Newer" Button
        if self.view_end < self.total_msgs:
            icon_down = assets.load_icon("arrow-down", size=(16, 16))
            ctk.CTkButton(self.scroll_chat, text=" Load Newer", image=icon_down, compound="left",
                          width=200, height=35, fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_MAIN,
                          command=self.load_newer).pack(pady=(10, 20))

        self.update_idletasks()
        try:
            self.scroll_chat._parent_canvas.yview_moveto(max(0.0, min(1.0, scroll_pos)))
        except: pass