import customtkinter as ctk
from PIL import Image, ImageOps
import cv2
import os
import time  # <--- CRITICAL FIX
from ui.theme import *
from utils.assets import assets

try:
    from ffpyplayer.player import MediaPlayer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ 'ffpyplayer' not found. Audio disabled.")

class GlobalMediaPlayer(ctk.CTkFrame):
    active_instance = None

    def __init__(self, parent, playlist, current_index=0):
        if GlobalMediaPlayer.active_instance:
            GlobalMediaPlayer.active_instance.close_viewer()
        
        root = parent.winfo_toplevel()
        super().__init__(root, fg_color="#000000")
        
        GlobalMediaPlayer.active_instance = self
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.playlist = playlist
        self.index = current_index
        
        self.playing = False
        self.cap = None
        self.player = None
        self.total_frames = 0
        self.fps = 30
        self.duration = 0
        self.job_id = None
        self.volume = 1.0
        self.is_audio_only = False
        
        self._setup_ui()
        
        try:
            root.bind("<Left>", self.prev_media)
            root.bind("<Right>", self.next_media)
            root.bind("<space>", lambda e: self.toggle_play())
        except: pass
        
        self.after(50, self._load_media)

    def _setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        top_bar.pack(fill="x", padx=10, pady=10)
        
        self.lbl_counter = ctk.CTkLabel(top_bar, 
                                        text=f"{self.index + 1} / {len(self.playlist)}", 
                                        font=("Segoe UI", 12, "bold"), 
                                        text_color=TEXT_DIM)
        self.lbl_counter.pack(side="left", padx=10)

        icon_x = assets.load_icon("x", size=(24, 24))
        ctk.CTkButton(top_bar, text="", image=icon_x, width=30, height=30, 
                      fg_color="transparent", hover_color="#333", 
                      command=self.close_viewer).pack(side="right")
        
        icon_ext = assets.load_icon("external-link", size=(20, 20)) or assets.load_icon("search", size=(20, 20))
        ctk.CTkButton(top_bar, text="", image=icon_ext, width=40, height=30, 
                      fg_color="#222", hover_color="#333", 
                      command=self.open_system).pack(side="right", padx=10)

        carousel_frame = ctk.CTkFrame(self, fg_color="transparent")
        carousel_frame.pack(fill="both", expand=True)

        icon_prev = assets.load_icon("chevron-left", size=(40, 40))
        self.btn_prev = ctk.CTkButton(carousel_frame, text="", image=icon_prev, width=50, height=80,
                                      fg_color="transparent", hover_color="#222", 
                                      command=self.prev_media)
        self.btn_prev.pack(side="left", fill="y")

        self.display_frame = ctk.CTkFrame(carousel_frame, fg_color="transparent")
        self.display_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.lbl_media = ctk.CTkLabel(self.display_frame, text="Loading...", text_color="#555")
        self.lbl_media.pack(expand=True, fill="both")
        
        self.btn_error_open = ctk.CTkButton(self.display_frame, 
                                            text="Open in System Player", 
                                            font=("Segoe UI", 14, "bold"),
                                            fg_color=BG_CARD, 
                                            hover_color=BG_HOVER,
                                            text_color=TEXT_MAIN, # Added this
                                            command=self.open_system)

        icon_next = assets.load_icon("chevron-right", size=(40, 40))
        self.btn_next = ctk.CTkButton(carousel_frame, text="", image=icon_next, width=50, height=80,
                                      fg_color="transparent", hover_color="#222", 
                                      command=self.next_media)
        self.btn_next.pack(side="left", fill="y")

        self.controls_frame = ctk.CTkFrame(self, fg_color="#111", height=50, corner_radius=10)
        
        self.icon_play = assets.load_icon("play", size=(24, 24))
        self.icon_pause = assets.load_icon("pause", size=(24, 24))
        
        self.btn_play = ctk.CTkButton(self.controls_frame, text="", image=self.icon_pause, width=40, height=30, 
                                      fg_color="transparent", hover_color="#333", command=self.toggle_play)
        self.btn_play.pack(side="left", padx=10, pady=10)
        
        self.slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self.on_seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)
        self.slider.set(0)
        
        self.lbl_time = ctk.CTkLabel(self.controls_frame, text="00:00 / 00:00", font=("Segoe UI", 12), width=80)
        self.lbl_time.pack(side="left", padx=5)

        icon_vol = assets.load_icon("volume-2", size=(20, 20))
        ctk.CTkLabel(self.controls_frame, text="", image=icon_vol).pack(side="left", padx=(10, 2))
        
        self.vol_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, width=80, command=self.on_volume)
        self.vol_slider.pack(side="left", padx=10)
        self.vol_slider.set(100)

    def _reset_player(self):
        self.playing = False
        if self.job_id: self.after_cancel(self.job_id)
        if self.cap: self.cap.release()
        if self.player:
            try:
                self.player.toggle_pause()
                self.player.close_player()
            except: pass
            self.player = None
        self.cap = None
        self.is_audio_only = False
        self.controls_frame.pack_forget()
        self.btn_error_open.pack_forget()
        self.lbl_media.configure(image=None, text="Loading...")

    def _load_media(self):
        self._reset_player()
        if not self.playlist:
            self.lbl_media.configure(text="Playlist Empty")
            return

        self.file_path = self.playlist[self.index]
        self.lbl_counter.configure(text=f"{self.index + 1} / {len(self.playlist)}")
        
        if not os.path.exists(self.file_path):
            self._show_error_state("File Missing")
            return

        ext = os.path.splitext(self.file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.webp']:
            self._display_image()
            return

        try:
            if self._is_file_safe():
                self._probe_and_load_video()
            else:
                self._show_error_state("⚠️ File Corrupt or Empty")
        except Exception as e:
            print(f"[ERROR] Media Load Failed: {e}")
            self._show_error_state("⚠️ Playback Failed")

    def _is_file_safe(self):
        if not AUDIO_AVAILABLE: return True
        try:
            p = MediaPlayer(self.file_path, ff_opts={'paused': True})
            time.sleep(0.05)
            meta = p.get_metadata()
            p.close_player()
            dur = meta.get('duration', 0)
            size = meta.get('src_vid_size', (0,0))
            if dur is None and size == (0,0): return False
            return True
        except: return False

    def _show_error_state(self, message):
        icon = assets.load_icon("alert-triangle", size=(64, 64))
        self.lbl_media.configure(text=f"\n{message}", image=icon, compound="top", font=("Segoe UI", 16))
        self.btn_error_open.pack(pady=20)

    def _probe_and_load_video(self):
        is_video = False
        if AUDIO_AVAILABLE:
            try:
                probe = MediaPlayer(self.file_path, ff_opts={'paused': True})
                time.sleep(0.05)
                meta = probe.get_metadata()
                if meta and meta.get('src_vid_size') and meta['src_vid_size'][0] > 0:
                    is_video = True
                probe.close_player()
            except: pass
        if is_video: self._setup_video_mode()
        else: self._setup_audio_mode()

    def _display_image(self):
        try:
            img = Image.open(self.file_path)
            w = self.winfo_width() - 100
            h = self.winfo_height() - 100
            img = ImageOps.contain(img, (w, h), method=Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(img, size=img.size)
            self.lbl_media.configure(image=ctk_img, text="")
            self.lbl_media.image = ctk_img
        except: self._show_error_state("Invalid Image")

    def _setup_video_mode(self):
        try:
            self.cap = cv2.VideoCapture(self.file_path)
            if not self.cap.isOpened(): raise Exception("Video Init Failed")
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
            self.duration = self.total_frames / self.fps
            if AUDIO_AVAILABLE: self.player = MediaPlayer(self.file_path, ff_opts={'vn': True})
            self.controls_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
            self.playing = True
            self.btn_play.configure(image=self.icon_pause)
            self.update_video_frame()
        except: self._show_error_state("Video Error")

    def _setup_audio_mode(self):
        self.is_audio_only = True
        icon_music = assets.load_icon("music", size=(80, 80))
        self.lbl_media.configure(text=" Audio Clip", font=("Segoe UI", 24), image=icon_music, compound="top")
        if AUDIO_AVAILABLE:
            try:
                self.player = MediaPlayer(self.file_path)
                time.sleep(0.1)
                meta = self.player.get_metadata()
                self.duration = meta.get('duration', 60) if meta else 60
                self.controls_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
                self.playing = True
                self.btn_play.configure(image=self.icon_pause)
                self.update_audio_frame()
            except: self._show_error_state("Audio Error")
        else: self.lbl_media.configure(text="Audio Library Missing")

    def update_video_frame(self):
        if not self.cap or not self.playing: return
        try:
            ret, frame = self.cap.read()
            if ret:
                curr = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if curr % 15 == 0 and self.total_frames > 0:
                    self.slider.set((curr/self.total_frames)*100)
                    self._update_time(curr/self.fps)
                h, w, _ = frame.shape
                max_h = self.winfo_height() - 150
                max_w = self.winfo_width() - 100
                scale = min(max_h/h, max_w/w)
                frame = cv2.resize(frame, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_NEAREST)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ctk_img = ctk.CTkImage(Image.fromarray(frame), size=(int(w*scale), int(h*scale)))
                self.lbl_media.configure(image=ctk_img, text="")
                self.lbl_media.image = ctk_img
                self.job_id = self.after(int(1000/self.fps), self.update_video_frame)
            else:
                self.on_seek(0); self.playing = True; self.update_video_frame()
        except: self.playing = False

    def update_audio_frame(self):
        if not self.playing or not self.player: return
        pts = self.player.get_pts()
        if pts is not None:
             if self.duration > 0:
                 self.slider.set((pts/self.duration)*100)
                 self._update_time(pts)
             if pts > self.duration: self.on_seek(0)
        self.job_id = self.after(100, self.update_audio_frame)

    def prev_media(self, event=None):
        if self.index > 0:
            self.index -= 1
            self._load_media()
    
    def next_media(self, event=None):
        if self.index < len(self.playlist) - 1:
            self.index += 1
            self._load_media()

    def toggle_play(self):
        self.playing = not self.playing
        self.btn_play.configure(image=self.icon_pause if self.playing else self.icon_play)
        if self.player: self.player.toggle_pause()
        if self.playing:
            if self.is_audio_only: self.update_audio_frame()
            else: self.update_video_frame()

    def on_seek(self, val):
        val = float(val)
        if self.is_audio_only:
            if self.player: self.player.seek((val/100)*self.duration, relative=False)
        else:
            if self.cap: self.cap.set(cv2.CAP_PROP_POS_FRAMES, int((val/100)*self.total_frames))
            if self.player: self.player.seek(int((val/100)*self.total_frames)/self.fps, relative=False)

    def on_volume(self, val):
        if self.player: self.player.set_volume(float(val)/100)

    def _update_time(self, seconds):
        try: self.lbl_time.configure(text=f"{int(seconds)//60:02}:{int(seconds)%60:02} / {int(self.duration)//60:02}:{int(self.duration)%60:02}")
        except: pass

    def open_system(self):
        if os.path.exists(self.file_path): 
            try: os.startfile(self.file_path)
            except Exception as e: print(f"System open failed: {e}")

    def close_viewer(self):
        self._reset_player()
        try:
            root = self.winfo_toplevel()
            root.unbind("<Left>"); root.unbind("<Right>"); root.unbind("<space>")
        except: pass
        GlobalMediaPlayer.active_instance = None
        self.destroy()

MediaViewer = GlobalMediaPlayer