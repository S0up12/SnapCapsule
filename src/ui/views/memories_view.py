import customtkinter as ctk
from PIL import Image, ImageOps
import os
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from utils.image_utils import extract_video_thumbnail, add_play_icon
from ui.theme import *
from ui.components.media_viewer import GlobalMediaPlayer
from utils.assets import assets

class MemoryCard(ctk.CTkFrame):
    def __init__(self, parent, memory, width, click_callback, executor):
        super().__init__(parent, fg_color="transparent", width=width, height=200)
        self.pack_propagate(False) 
        self.path = memory.get('path')
        self.click_callback = click_callback
        self.executor = executor
        self.is_destroyed = False # Safety flag for threaded updates
        
        self.btn = ctk.CTkButton(self, text="", fg_color=BG_CARD, hover_color=BG_HOVER,
                                 corner_radius=6, command=lambda: self.click_callback(self.path))
        self.btn.pack(expand=True, fill="both", padx=2, pady=2)
        
        self._set_placeholder_state(is_loading=True)
        self.load_image()

    def destroy(self):
        self.is_destroyed = True
        super().destroy()

    def _set_placeholder_state(self, is_missing=False, is_loading=False):
        if self.is_destroyed or not self.winfo_exists(): return
        
        if is_loading:
            icon_name = "image"
            text = ""
            color = BG_CARD
        else:
            icon_name = "alert-triangle" if is_missing else "file-text"
            text = "Missing" if is_missing else "No Preview"
            color = ("#FADBD8", "#2b1111") if is_missing else BG_CARD
            
        icon = assets.load_icon(icon_name, size=(32, 32))
        self.btn.configure(image=icon, text=text, compound="top", 
                           fg_color=color, font=("Segoe UI", 12, "bold"), text_color=TEXT_DIM)

    def load_image(self):
        if not self.path: return
        self.executor.submit(self._load_job, self.path)

    def _load_job(self, target_path):
        try:
            if not os.path.exists(target_path):
                self.after(0, lambda: self._set_placeholder_state(is_missing=True))
                return

            ext = os.path.splitext(target_path)[1].lower()
            pil_img = None
            is_video = ext in ['.mp4', '.mov', '.avi']
            
            if is_video:
                pil_img = extract_video_thumbnail(target_path)
            else:
                from utils.media_resolver import MediaResolver
                pil_img = MediaResolver.get_display_image(target_path)

            if pil_img and not self.is_destroyed:
                pil_img.thumbnail((300, 300))
                self.after(0, lambda: self._apply_image(pil_img, is_video))
            else:
                self.after(0, lambda: self._set_placeholder_state(is_missing=False))
        except:
            self.after(0, lambda: self._set_placeholder_state(is_missing=True))

    def _apply_image(self, pil_img, is_video):
        if self.is_destroyed or not self.winfo_exists(): return
        w = self.winfo_width()
        if w < 50: w = 200
        
        try:
            pil_img = ImageOps.fit(pil_img, (w, 200), method=Image.Resampling.LANCZOS)
            if is_video: pil_img = add_play_icon(pil_img)
            
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w, 200))
            self.btn.configure(image=ctk_img, text="", fg_color="transparent")
        except:
            self._set_placeholder_state(is_missing=False)

class MemoriesView(ctk.CTkFrame):
    def __init__(self, parent, memories_data):
        super().__init__(parent, fg_color="transparent")
        self.memories = [m for m in memories_data if m.get('path') and os.path.exists(m['path'])]
        
        self.PAGE_SIZE = 40 # Slightly smaller for stability
        self.current_page = 1
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        self._calculate_stats() 
        self._setup_ui()
        self.after(100, lambda: self.load_page(1))

    def _calculate_stats(self):
        self.total_count = len(self.memories)
        self.video_count = sum(1 for m in self.memories if m['path'].lower().endswith(('.mp4','.mov','.avi')))
        self.photo_count = self.total_count - self.video_count
        self.total_pages = math.ceil(self.total_count / self.PAGE_SIZE) if self.total_count > 0 else 1

    def _setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, height=60, corner_radius=0)
        top_bar.pack(fill="x")
        
        ctk.CTkLabel(top_bar, text="Sort:", text_color=TEXT_DIM).pack(side="left", padx=(15, 5))
        self.sort_var = ctk.StringVar(value="Newest > Oldest")
        ctk.CTkOptionMenu(top_bar, values=["Newest > Oldest", "Oldest > Newest"], 
                          variable=self.sort_var, width=140, 
                          fg_color=BG_CARD, button_color=BG_HOVER, text_color=TEXT_MAIN,
                          command=self.on_sort_changed).pack(side="left", padx=5)
        
        self._add_stat(top_bar, f"{self.total_count}", TEXT_MAIN)
        self._add_stat(top_bar, f"{self.photo_count}", SNAP_BLUE, "camera")
        self._add_stat(top_bar, f"{self.video_count}", SNAP_RED, "video")

        self.nav_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        self.nav_frame.pack(side="right", padx=15)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="", image=assets.load_icon("chevron-left"), 
                                      width=35, height=35, command=self.prev_page)
        self.btn_prev.pack(side="left", padx=2)
        
        self.lbl_page = ctk.CTkLabel(self.nav_frame, text="", font=("Segoe UI", 12, "bold"), text_color=TEXT_MAIN)
        self.lbl_page.pack(side="left", padx=10)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="", image=assets.load_icon("chevron-right"), 
                                      width=35, height=35, command=self.next_page)
        self.btn_next.pack(side="left", padx=2)

        self.scroll_mems = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_mems.pack(fill="both", expand=True)

    def _add_stat(self, parent, text, color, icon_name=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=8)
        if icon_name:
            icon = assets.load_icon(icon_name, size=(16, 16))
            if icon: ctk.CTkLabel(f, text="", image=icon).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(f, text=text, font=("Segoe UI", 12, "bold"), text_color=color).pack(side="left")

    def load_page(self, page_num):
        self.current_page = page_num
        self.lbl_page.configure(text=f"Page {self.current_page} / {self.total_pages}")
        
        # Clear existing content safely
        for child in self.scroll_mems.winfo_children():
            child.destroy()
            
        self.after(10, self._render_content)
        self.scroll_mems._parent_canvas.yview_moveto(0.0)

    def _render_content(self):
        start = (self.current_page - 1) * self.PAGE_SIZE
        chunk = self.memories[start : start + self.PAGE_SIZE]
        if not chunk: return

        # Dynamic grid calculation
        canvas_width = self.scroll_mems.winfo_width() - 40
        if canvas_width < 100: canvas_width = 1000
        cols = max(1, canvas_width // 210)
        card_width = int(canvas_width / cols) - 6

        last_month = None
        current_row = None
        row_count = 0

        for mem in chunk:
            # Month Header logic
            try:
                dt = datetime.strptime(mem['date'], "%Y-%m-%d %H:%M:%S UTC")
                month_key = dt.strftime("%B %Y").upper()
            except: month_key = "UNKNOWN"

            if month_key != last_month:
                h_frame = ctk.CTkFrame(self.scroll_mems, fg_color="transparent", height=50)
                h_frame.pack(fill="x", pady=(10, 0))
                tag = ctk.CTkFrame(h_frame, fg_color=SNAP_RED, corner_radius=5)
                tag.pack(anchor="w", padx=5)
                ctk.CTkLabel(tag, text=month_key, font=("Segoe UI", 12, "bold"), text_color="white").pack(padx=10, pady=2)
                last_month = month_key
                current_row = None 

            if current_row is None or row_count >= cols:
                current_row = ctk.CTkFrame(self.scroll_mems, fg_color="transparent", height=205)
                current_row.pack(fill="x", pady=2)
                current_row.pack_propagate(False)
                row_count = 0

            card = MemoryCard(current_row, mem, card_width, self.open_media, self.executor)
            card.pack(side="left", padx=2)
            row_count += 1

    def on_sort_changed(self, choice):
        self.memories.sort(key=lambda x: x['date'], reverse=(choice == "Newest > Oldest"))
        self.load_page(1)

    def prev_page(self):
        if self.current_page > 1: self.load_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages: self.load_page(self.current_page + 1)

    def open_media(self, path):
        playlist = [m['path'] for m in self.memories]
        try: idx = playlist.index(path)
        except: idx = 0; playlist = [path]
        GlobalMediaPlayer(self, playlist, idx)