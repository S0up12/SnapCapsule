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

try:
    from ffpyplayer.player import MediaPlayer
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

class SidebarChatButton(ctk.CTkFrame):
    def __init__(self, parent, display_name, username, command):
        super().__init__(parent, fg_color="transparent", corner_radius=6)
        self.command = command
        self.is_selected = False
        self.bind("<Button-1>", self.on_click)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        self.name_lbl = ctk.CTkLabel(self, text=display_name, font=("Segoe UI", 14, "bold"), text_color=TEXT_MAIN, anchor="w")
        self.name_lbl.pack(fill="x", padx=10, pady=(8, 0))
        
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
        
class ChatAudioPlayer(ctk.CTkFrame):
    """Embedded audio player for chat bubbles with transparent controls."""
    def __init__(self, parent, file_path):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, height=50)
        self.path = file_path
        self.player = None
        self.playing = False
        self.duration = 0
        self.update_job = None
        
        # UI Elements
        self.icon_play = assets.load_icon("play", size=(24, 24))
        self.icon_stop = assets.load_icon("pause", size=(24, 24))
        
        # Removed SNAP_BLUE; using transparent background with hover effect
        self.btn_toggle = ctk.CTkButton(self, text="", image=self.icon_play, width=40, height=40,
                                        fg_color="transparent", hover_color=BG_HOVER, corner_radius=20,
                                        command=self.toggle_playback)
        self.btn_toggle.pack(side="left", padx=10, pady=5)
        
        self.progress = ctk.CTkProgressBar(self, progress_color=SNAP_BLUE, height=4)
        self.progress.set(0)
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.lbl_time = ctk.CTkLabel(self, text="0:00", font=("Segoe UI", 10), text_color=TEXT_DIM)
        self.lbl_time.pack(side="right", padx=10)

    def toggle_playback(self):
        if not AUDIO_SUPPORT: return
        
        if self.playing:
            self.stop()
        else:
            self.play()

    def play(self):
        try:
            self.player = MediaPlayer(self.path)
            time.sleep(0.1)
            meta = self.player.get_metadata()
            self.duration = meta.get('duration', 0) if meta else 0
            
            self.playing = True
            self.btn_toggle.configure(image=self.icon_stop)
            self._update_loop()
        except Exception as e:
            print(f"Audio playback error: {e}")

    def stop(self):
        self.playing = False
        if self.player:
            self.player.close_player()
            self.player = None
        if self.update_job:
            self.after_cancel(self.update_job)
            self.update_job = None
            
        self.btn_toggle.configure(image=self.icon_play)
        self.progress.set(0)
        self.lbl_time.configure(text="0:00")

    def _update_loop(self):
        if not self.playing or not self.player: return
        
        pts = self.player.get_pts()
        if pts is not None:
            if self.duration > 0:
                self.progress.set(pts / self.duration)
                self.lbl_time.configure(text=f"{int(pts)//60}:{int(pts)%60:02}")
            
            if pts >= self.duration and self.duration > 0:
                self.stop()
                return
                
        self.update_job = self.after(100, self._update_loop)

class ChatBubble(ctk.CTkFrame):
    def __init__(self, parent, message, is_me, friend_name, executor, alive_flag, media_callback):
        super().__init__(parent, fg_color="transparent")
        self.pack(pady=5, padx=20, anchor="w", fill="x")
        self.executor = executor
        self.alive_flag = alive_flag
        self.media_callback = media_callback
        
        self.msg_id = f"{message['date']}_{message['text'][:10]}" 
        
        accent_color = SNAP_RED if is_me else SNAP_BLUE
        sender_text = "ME" if is_me else friend_name.upper()
        
        name_lbl = ctk.CTkLabel(self, text=sender_text, font=("Segoe UI", 11, "bold"), text_color=accent_color, anchor="w")
        name_lbl.pack(fill="x", anchor="w")
        
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="x", anchor="w")
        
        bar = ctk.CTkFrame(body_frame, width=3, fg_color=accent_color, height=20, corner_radius=0)
        bar.pack(side="left", fill="y", padx=(0, 10))
        
        self.content_container = ctk.CTkFrame(body_frame, fg_color="transparent")
        self.content_container.pack(side="left", fill="x")

        self.add_message_content(message)

        try:
            dt = datetime.strptime(message['date'], "%Y-%m-%d %H:%M")
            time_str = dt.strftime("%H:%M")
        except: time_str = ""
        self.time_lbl = ctk.CTkLabel(body_frame, text=time_str, font=("Segoe UI", 10), text_color="#555555")
        
        for w in [self, body_frame, self.content_container]:
            w.bind("<Enter>", lambda e: self.time_lbl.pack(side="left", padx=(10, 0)))
            w.bind("<Leave>", lambda e: self.time_lbl.pack_forget())

    def add_message_content(self, message):
        if message['text']:
            ctk.CTkLabel(self.content_container, 
                         text=message['text'], 
                         font=("Segoe UI", 14), 
                         text_color=TEXT_MAIN, 
                         justify="left", 
                         anchor="w", 
                         wraplength=500).pack(anchor="w")

        if message['media']:
            for path in message['media']:
                self.render_media_placeholder(self.content_container, path)

    def render_media_placeholder(self, parent, path):
        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.mp3', '.wav', '.m4a']:
            audio_player = ChatAudioPlayer(parent, path)
            audio_player.pack(pady=5, anchor="w", fill="x")
            return

        btn = ctk.CTkButton(parent, text="Loading...", width=200, height=150, 
                            fg_color="#111", hover=False, state="disabled", corner_radius=10)
        btn.pack(pady=5, anchor="w")
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
        except: pass

    def _apply_image_main_thread(self, btn, pil_img, path):
        if not btn.winfo_exists(): return
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        btn.configure(text="", image=ctk_img, state="normal", width=pil_img.size[0], height=pil_img.size[1],
                      command=lambda: self.media_callback(path))

    def _apply_audio_ui(self, btn, path):
        if not btn.winfo_exists(): return
        icon = assets.load_icon("music", size=(24, 24))
        btn.configure(text=" Voice Message", image=icon, compound="left", state="normal", 
                      width=180, height=45, fg_color=BG_CARD, hover_color=BG_HOVER,
                      text_color=TEXT_MAIN, command=lambda: self.media_callback(path))

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
        self.data_manager = data_manager
        self.chat_list = data_manager.chat_index 
        self.profile = profile_data or {}
        
        self.current_messages = [] 
        self.current_friend_key = None
        
        self.WINDOW_SIZE = 75   
        self.STEP_SIZE = 30     
        self.view_start = 0     
        self.view_end = 0       
        self.total_msgs = 0     
        
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_active = [True]
        self.is_rendering = False
        
        self.friend_map = self._build_friend_map()
        self.active_btn = None 
        
        self._setup_ui()
        self._monitor_scroll()

    def cleanup(self):
        self.is_active[0] = False
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_active = [True]

    def _monitor_scroll(self):
        if not self.winfo_exists(): return
        
        if not self.is_rendering and self.current_friend_key:
            try:
                top, bottom = self.scroll_chat._parent_canvas.yview()
                
                if top < 0.05 and self.view_start > 0:
                    self.trigger_load_older()
                elif bottom > 0.95 and self.view_end < self.total_msgs:
                    self.load_newer()
            except: pass
            
        self.after(200, self._monitor_scroll)

    def _build_friend_map(self):
        mapping = {}
        friends_list = self.profile.get("friends_list", [])
        for key in self.chat_list:
            details = {"display": key, "username": key}
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
        
        sidebar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, width=300)
        sidebar.grid(row=0, column=0, sticky="nsew")
        
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
        
        self.scroll_friends = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.scroll_friends.pack(fill="both", expand=True)
        self.populate_friends(self.chat_list)

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
        
        self.loader_frame = ctk.CTkFrame(self.right_panel, fg_color=BG_MAIN, height=30)
        self.lbl_loader = ctk.CTkLabel(self.loader_frame, text="Loading previous messages...", 
                                       text_color=SNAP_YELLOW, font=("Segoe UI", 12))
        self.lbl_loader.pack(pady=5)
        
        self.scroll_chat = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_chat.pack(fill="both", expand=True)

        self.initial_loader = ctk.CTkFrame(self.right_panel, fg_color=BG_MAIN)
        self.lbl_init_load = ctk.CTkLabel(self.initial_loader, text="Loading History...", 
                                          font=("Segoe UI", 16, "bold"), text_color=SNAP_YELLOW)
        self.lbl_init_load.place(relx=0.5, rely=0.4, anchor="center")

    def show_media(self, path):
        if not os.path.exists(path): return
        playlist = []
        msgs = self.current_messages[self.view_start : self.view_end]
        for msg in msgs:
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
        query = self.search_entry.get().strip().lower()
        
        if not query:
            self.populate_friends(self.chat_list)
        else:
            filtered = []
            for key in self.chat_list:
                info = self.friend_map.get(key, {})
                display = info.get("display", "").lower()
                username = info.get("username", "").lower()
                if query in display or query in username:
                    filtered.append(key)
            self.populate_friends(filtered)

    def populate_friends(self, chat_keys):
        for w in self.scroll_friends.winfo_children(): w.destroy()
        for key in chat_keys[:100]: 
            info = self.friend_map.get(key, {"display": key, "username": key})
            btn = SidebarChatButton(self.scroll_friends, info["display"], info["username"], lambda k=key: self.load_chat(k))
            btn.pack(fill="x", pady=2, padx=5)
            btn.chat_key = key
            
            if self.current_friend_key == key:
                btn.set_selected(True)
                self.active_btn = btn

    def load_chat(self, chat_key):
        self.cleanup()
        self.is_rendering = True 
        self.initial_loader.place(x=0, y=70, relwidth=1, relheight=1)
        self.initial_loader.lift()
        
        if self.active_btn: self.active_btn.set_selected(False)
        for widget in self.scroll_friends.winfo_children():
            if hasattr(widget, 'chat_key') and widget.chat_key == chat_key:
                widget.set_selected(True)
                self.active_btn = widget
                break

        self.current_friend_key = chat_key
        self.after(50, self._perform_load_chat)

    def _perform_load_chat(self):
        self.scroll_chat._parent_canvas.yview_moveto(0.0)
        self.scroll_chat.update_idletasks()
        self.current_messages = self.data_manager.get_chat_messages(self.current_friend_key)
        self.total_msgs = len(self.current_messages)
        self.view_end = self.total_msgs
        self.view_start = max(0, self.view_end - self.WINDOW_SIZE)
        info = self.friend_map.get(self.current_friend_key, {"display": self.current_friend_key, "username": self.current_friend_key})
        self.lbl_name.configure(text=info["display"])
        self.lbl_user.configure(text=f"@{info['username']}")
        self.render_window(target_anchor="bottom")

    def trigger_load_older(self):
        if self.is_rendering: return
        self.is_rendering = True
        self.loader_frame.pack(before=self.scroll_chat, fill="x", pady=(5, 0))
        self.after(400, self._perform_load_older)

    def _perform_load_older(self):
        anchor_id = self._find_visible_anchor(at_top=True)
        old_start = self.view_start
        self.view_start = max(0, self.view_start - self.STEP_SIZE)
        self.view_end = min(self.total_msgs, self.view_start + self.WINDOW_SIZE)
        if old_start == self.view_start: 
            self._finish_rendering()
            return
        self.render_window(target_anchor=anchor_id)

    def load_newer(self):
        if self.is_rendering: return
        self.is_rendering = True
        anchor_id = self._find_visible_anchor(at_top=False)
        old_end = self.view_end
        self.view_end = min(self.total_msgs, self.view_end + self.STEP_SIZE)
        self.view_start = max(0, self.view_end - self.WINDOW_SIZE)
        if old_end == self.view_end: 
            self._finish_rendering()
            return
        self.render_window(target_anchor=anchor_id)

    def _finish_rendering(self):
        self.loader_frame.pack_forget()
        self.is_rendering = False

    def _find_visible_anchor(self, at_top=True):
        try:
            children = self.scroll_chat.winfo_children()
            if not children: return None
            target_idx = 0 if at_top else len(children) - 1
            widget = children[target_idx]
            if hasattr(widget, 'msg_id'): return widget.msg_id
            for w in children:
                if hasattr(w, 'msg_id'): return w.msg_id
        except: pass
        return None

    def render_window(self, target_anchor=None):
        for w in self.scroll_chat.winfo_children(): w.destroy()
        msgs = self.current_messages[self.view_start : self.view_end]
        last_date = ""
        last_sender = None
        last_minute = None
        info = self.friend_map.get(self.current_friend_key, {"display": self.current_friend_key})
        anchor_widget = None
        last_bubble = None
        for i, msg in enumerate(msgs):
            if not msg['text'] and not msg['media']: continue
            d = msg['date'].split(" ")[0]
            if d != last_date:
                f = ctk.CTkFrame(self.scroll_chat, fg_color="transparent")
                f.pack(pady=(20, 10), fill="x")
                try:
                    date_obj = datetime.strptime(d, "%Y-%m-%d")
                    txt = date_obj.strftime("%B %d").upper()
                except: txt = d
                ctk.CTkLabel(f, text=txt, font=("Segoe UI", 10, "bold"), text_color="#666").pack()
                last_date = d
                last_sender = None
                last_minute = None
            current_sender = msg['sender']
            current_time = msg['date'] 
            if last_bubble and current_sender == last_sender and current_time == last_minute:
                last_bubble.add_message_content(msg)
                bubble = last_bubble
            else:
                is_me = (current_sender != self.current_friend_key)
                bubble = ChatBubble(self.scroll_chat, msg, is_me, info["display"], self.executor, self.is_active, 
                           media_callback=self.show_media)
                last_bubble = bubble
                last_sender = current_sender
                last_minute = current_time
            if target_anchor == "bottom" and i == len(msgs)-1:
                anchor_widget = bubble
            elif target_anchor and bubble.msg_id == target_anchor:
                anchor_widget = bubble
            if i % 10 == 0: self.update()
        self.update_idletasks()
        if target_anchor == "bottom":
            def complete_load():
                try: self.scroll_chat._parent_canvas.yview_moveto(1.0)
                except: pass
                self.initial_loader.place_forget()
                self._finish_rendering()
            self.after(200, complete_load)
        elif anchor_widget:
            try:
                widget_y = anchor_widget.winfo_y()
                scroll_h = self.scroll_chat._parent_canvas.bbox("all")[3]
                fraction = widget_y / scroll_h
                self.scroll_chat._parent_canvas.yview_moveto(fraction)
            except: pass
            self._finish_rendering()
        else:
            self._finish_rendering()