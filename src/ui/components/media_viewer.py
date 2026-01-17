import customtkinter as ctk
from PIL import Image, ImageOps
import cv2
import os
import time
import subprocess
import uuid
from ui.theme import *
from utils.assets import assets
from utils.repair import EnvironmentManager

try:
    from ffpyplayer.player import MediaPlayer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

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
        self.session_id = None 
        
        self.ffmpeg_exe = EnvironmentManager.get_ffmpeg()
        self.ffplay_exe = self.ffmpeg_exe.replace("ffmpeg", "ffplay") if self.ffmpeg_exe else None
        
        self.playing = False
        self.cap = None
        self.player = None
        self.total_frames = 0
        self.fps = 30
        self.duration = 0
        self.job_id = None
        self.volume = 1.0
        
        self._setup_ui()
        
        root.bind("<Left>", self.prev_media)
        root.bind("<Right>", self.next_media)
        root.bind("<space>", lambda e: self.toggle_play())
        root.bind("<Escape>", lambda e: self.close_viewer())
        
        self.after(50, self._load_media)

    def _setup_ui(self):
        self.lbl_media = ctk.CTkLabel(self, text="Loading...", text_color="#555")
        self.lbl_media.place(relx=0.5, rely=0.45, anchor="center")
        
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.top_bar.place(relx=0, rely=0, relwidth=1)
        
        self.lbl_counter = ctk.CTkLabel(self.top_bar, text="", font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN)
        self.lbl_counter.pack(side="left", padx=20)

        ctk.CTkButton(self.top_bar, text="", image=assets.load_icon("x", size=(20, 20)), width=35, height=35, 
                      fg_color="transparent", hover_color="#333", command=self.close_viewer).pack(side="right", padx=10)
        
        ctk.CTkButton(self.top_bar, text="", image=assets.load_icon("external-link", size=(18, 18)), width=35, height=35, 
                      fg_color="#222", hover_color="#333", command=self.open_system).pack(side="right", padx=10)
        
        self.btn_prev = ctk.CTkButton(self, text="", image=assets.load_icon("chevron-left", size=(30, 30)), 
                                      width=40, height=80, fg_color="transparent", hover_color="#222", command=self.prev_media)
        self.btn_prev.place(relx=0.01, rely=0.5, anchor="w")

        self.btn_next = ctk.CTkButton(self, text="", image=assets.load_icon("chevron-right", size=(30, 30)), 
                                      width=40, height=80, fg_color="transparent", hover_color="#222", command=self.next_media)
        self.btn_next.place(relx=0.99, rely=0.5, anchor="e")

        self.bottom_bar = ctk.CTkFrame(self, fg_color="#000000", height=100, corner_radius=0)
        self.bottom_bar.place(relx=0.5, rely=1.0, relwidth=1.0, anchor="s")

        self.controls_frame = ctk.CTkFrame(self.bottom_bar, fg_color="#111", height=50, corner_radius=10)
        self.controls_frame.pack(fill="x", padx=40, pady=25)

        self.btn_play = ctk.CTkButton(self.controls_frame, text="", image=assets.load_icon("pause", size=(24, 24)), 
                                      width=40, height=35, fg_color="transparent", command=self.toggle_play)
        self.btn_play.pack(side="left", padx=15)
        
        self.slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, command=self.on_seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)
        
        self.lbl_time = ctk.CTkLabel(self.controls_frame, text="00:00 / 00:00", font=("Segoe UI", 12), width=100)
        self.lbl_time.pack(side="left", padx=15)

        # Restored Volume Icon
        self.lbl_vol = ctk.CTkLabel(self.controls_frame, text="", image=assets.load_icon("volume-2", size=(20, 20)))
        self.lbl_vol.pack(side="left", padx=(10, 0))

        self.vol_slider = ctk.CTkSlider(self.controls_frame, from_=0, to=100, width=80, command=self.on_volume)
        self.vol_slider.pack(side="left", padx=15)
        self.vol_slider.set(100)
        self.controls_frame.pack_forget()

    def _cleanup_resources(self):
        self.session_id = None
        self.playing = False
        if self.job_id:
            self.after_cancel(self.job_id)
            self.job_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.player:
            try: self.player.close_player()
            except: pass
            self.player = None
        self.lbl_media.configure(image="", text="Loading...")

    def prev_media(self, event=None):
        if self.index > 0:
            self._cleanup_resources()
            self.index -= 1
            self.after(150, self._load_media)

    def next_media(self, event=None):
        if self.index < len(self.playlist) - 1:
            self._cleanup_resources()
            self.index += 1
            self.after(150, self._load_media)

    def toggle_play(self, event=None):
        if not self.player and not self.cap: return
        self.playing = not self.playing
        self.btn_play.configure(image=assets.load_icon("pause" if self.playing else "play", size=(24, 24)))
        if self.player: self.player.toggle_pause()
        if self.playing: self.update_video_frame(self.session_id, time.perf_counter())

    def _load_media(self):
        self.session_id = str(uuid.uuid4())
        self.controls_frame.pack_forget()
        
        if not self.playlist: return
        self.file_path = self.playlist[self.index]
        self.lbl_counter.configure(text=f"{self.index + 1} / {len(self.playlist)}")
        
        if not os.path.exists(self.file_path):
            self._show_error_state("File Missing")
            return

        if self.file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            self._display_image()
        else:
            self._probe_and_load_video()

    def _display_image(self):
        from utils.media_resolver import MediaResolver
        img = MediaResolver.get_display_image(self.file_path)
        if img:
            w, h = max(100, self.winfo_width() - 100), max(100, self.winfo_height() - 250)
            img = ImageOps.contain(img, (w, h), method=Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.lbl_media.configure(image=ctk_img, text="")
        else:
            self._show_error_state("Invalid Image")

    def _probe_and_load_video(self):
        if AUDIO_AVAILABLE:
            try:
                self.cap = cv2.VideoCapture(self.file_path)
                if not self.cap.isOpened(): raise Exception()
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = max(float(self.cap.get(cv2.CAP_PROP_FPS)), 1.0)
                self.duration = self.total_frames / self.fps
                self.player = MediaPlayer(self.file_path, ff_opts={'vn': True})
                self.controls_frame.pack(fill="x", padx=40, pady=25)
                self.playing = True
                self.update_video_frame(self.session_id, time.perf_counter())
            except:
                self._show_error_state("Playback Failed")
        else:
            self._show_error_state("Library Missing")

    def update_video_frame(self, sid, last_tick):
        if sid != self.session_id or not self.cap or not self.playing: return
        
        target_fps_delay = 1.0 / self.fps
        current_tick = time.perf_counter()
        
        try:
            ret, frame = self.cap.read()
            if ret:
                curr_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                if curr_frame % 10 == 0:
                    self.slider.set((curr_frame/self.total_frames)*100)
                    self._update_time(curr_frame/self.fps)
                
                h, w, _ = frame.shape
                max_h, max_w = max(50, self.winfo_height() - 250), max(50, self.winfo_width() - 150)
                scale = min(max_h/h, max_w/w)
                frame = cv2.resize(frame, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_LINEAR)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                ctk_img = ctk.CTkImage(Image.fromarray(frame), size=(int(w*scale), int(h*scale)))
                self.lbl_media.configure(image=ctk_img, text="")
                
                elapsed = time.perf_counter() - current_tick
                actual_wait = max(1, int((target_fps_delay - elapsed) * 1000))
                self.job_id = self.after(actual_wait, lambda: self.update_video_frame(sid, time.perf_counter()))
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.update_video_frame(sid, time.perf_counter())
        except:
            self.playing = False

    def on_seek(self, val):
        if self.cap and self.session_id:
            pos = int((float(val)/100)*self.total_frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            if self.player: self.player.seek(pos/self.fps, relative=False)

    def on_volume(self, val):
        if self.player: self.player.set_volume(float(val)/100)

    def _update_time(self, seconds):
        try:
            self.lbl_time.configure(text=f"{int(seconds)//60:02}:{int(seconds)%60:02} / {int(self.duration)//60:02}:{int(self.duration)%60:02}")
        except: pass

    def _show_error_state(self, message):
        self.lbl_media.configure(text=f"\n{message}", image=assets.load_icon("alert-triangle", size=(64, 64)), compound="top")

    def open_system(self):
        if self.file_path and os.path.exists(self.file_path):
            try:
                if os.name == 'nt': os.startfile(self.file_path)
                else: subprocess.Popen(['open', self.file_path])
            except Exception as e: print(f"External open error: {e}")

    def close_viewer(self):
        self._cleanup_resources()
        GlobalMediaPlayer.active_instance = None
        self.destroy()