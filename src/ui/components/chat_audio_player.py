import customtkinter as ctk
import time
from ui.theme import *
from utils.assets import assets

try:
    from ffpyplayer.player import MediaPlayer
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

class ChatAudioPlayer(ctk.CTkFrame):
    # Static variable to track the globally active audio bubble
    _active_player = None

    def __init__(self, parent, file_path):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, height=50)
        self.path = file_path
        self.player = None
        self.playing = False
        self.duration = 0
        self.update_job = None
        
        self.icon_play = assets.load_icon("play", size=(24, 24))
        self.icon_stop = assets.load_icon("pause", size=(24, 24))
        
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
            # Stop any other audio message currently playing
            if ChatAudioPlayer._active_player and ChatAudioPlayer._active_player != self:
                ChatAudioPlayer._active_player.stop()
            self.play()

    def play(self):
        try:
            self.stop()
            # Suppress video/subtitles for pure audio performance
            self.player = MediaPlayer(self.path, ff_opts={'vn': True, 'sn': True, 'paused': False})
            ChatAudioPlayer._active_player = self
            
            # Wait briefly for metadata
            timeout = time.time() + 1.0
            while time.time() < timeout:
                meta = self.player.get_metadata()
                if meta and meta.get('duration'):
                    self.duration = meta['duration']
                    break
                time.sleep(0.01)
            
            self.playing = True
            if self.winfo_exists():
                self.btn_toggle.configure(image=self.icon_stop)
            self._update_loop()
        except Exception as e:
            print(f"Audio playback error: {e}")
            self.stop()

    def stop(self):
        self.playing = False
        if ChatAudioPlayer._active_player == self:
            ChatAudioPlayer._active_player = None

        if self.update_job:
            self.after_cancel(self.update_job)
            self.update_job = None
            
        if self.player:
            self.player.toggle_pause() # Pause first to stop buffer filling
            self.player.close_player()
            self.player = None
            
        if self.winfo_exists():
            self.btn_toggle.configure(image=self.icon_play)
            self.progress.set(0)
            self.lbl_time.configure(text="0:00")

    def _update_loop(self):
        if not self.playing or not self.player or not self.winfo_exists():
            return
        
        pts = self.player.get_pts()
        if pts is not None:
            if self.duration > 0:
                self.progress.set(min(pts / self.duration, 1.0))
                self.lbl_time.configure(text=f"{int(pts)//60}:{int(pts)%60:02}")
            
            if self.duration > 0 and pts >= (self.duration - 0.2):
                self.stop()
                return
        
        self.update_job = self.after(100, self._update_loop)

    def destroy(self):
        self.stop()
        super().destroy()