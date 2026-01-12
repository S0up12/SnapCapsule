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
        self.path = memory['path']
        self.click_callback = click_callback
        self.executor = executor
        self.is_loaded = False
        
        self.btn = ctk.CTkButton(self, text="", fg_color="#1a1a1a", hover_color="#252525",
                                 corner_radius=6, command=lambda: self.click_callback(self.path))
        self.btn.pack(expand=True, fill="both", padx=2, pady=2)
        
        self._set_placeholder_state(is_loading=True, force=True)
        self.load_image()

    def _set_placeholder_state(self, is_missing=False, is_loading=False, force=False):
        if not force and not self.winfo_exists(): return
        
        if is_loading:
            icon_name = "image"
            text = ""
            color = "#1a1a1a"
        else:
            icon_name = "alert-triangle" if is_missing else "file-text"
            text = "Missing" if is_missing else "No Preview"
            color = "#2b1111" if is_missing else "#1a1a1a"
            
        icon = assets.load_icon(icon_name, size=(32, 32))
        
        self.btn.configure(image=icon, text=text, compound="top", 
                           fg_color=color, font=("Segoe UI", 12, "bold"), text_color="#666")
        self.btn.image = icon

    def load_image(self):
        if self.is_loaded or not self.path: return
        self.is_loaded = True
        self.executor.submit(self._load_job)

    def _load_job(self):
        try:
            if not os.path.exists(self.path):
                self.after(0, lambda: self._set_placeholder_state(is_missing=True))
                return

            ext = os.path.splitext(self.path)[1].lower()
            pil_img = None
            is_video = False
            
            if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                pil_img = Image.open(self.path)
                pil_img.thumbnail((300, 300))
            elif ext in ['.mp4', '.mov', '.avi']:
                is_video = True
                pil_img = extract_video_thumbnail(self.path)
                if pil_img: pil_img.thumbnail((300, 300))

            if pil_img:
                self.after(0, lambda: self._apply_image(pil_img, is_video))
            else:
                self.after(0, lambda: self._set_placeholder_state(is_missing=False))
        except:
            self.after(0, lambda: self._set_placeholder_state(is_missing=True))

    def _apply_image(self, pil_img, is_video):
        if not self.winfo_exists(): return
        w = self.winfo_width()
        if w < 50: w = 200
        
        try:
            pil_img = ImageOps.fit(pil_img, (w, 200), method=Image.Resampling.LANCZOS)
            if is_video: pil_img = add_play_icon(pil_img)
            
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(w, 200))
            self.btn.configure(image=ctk_img, text="", fg_color="transparent")
            self.btn.image = ctk_img
        except:
            self._set_placeholder_state(is_missing=False)

class RowFrame(ctk.CTkFrame):
    """Simple container for a row of cards."""
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent", height=200)
        self.pack_propagate(False)

class MonthHeader(ctk.CTkFrame):
    def __init__(self, parent, text):
        super().__init__(parent, fg_color="transparent", height=40)
        self.pack_propagate(False)
        tag = ctk.CTkFrame(self, fg_color=SNAP_RED, corner_radius=5, height=30)
        tag.pack(anchor="w", padx=5, pady=10)
        ctk.CTkLabel(tag, text=text, font=("Segoe UI", 12, "bold"), text_color="white").pack(padx=10, pady=2)

class MemoriesView(ctk.CTkFrame):
    def __init__(self, parent, memories_data):
        super().__init__(parent, fg_color="transparent")
        self.memories = memories_data
        
        self.PAGE_SIZE = 50
        self.current_page = 1
        self.total_pages = 1
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.last_width = 0
        
        self.total_count = len(self.memories)
        self.video_count = sum(1 for m in self.memories if m.get('path') and os.path.splitext(m['path'])[1].lower() in ['.mp4','.mov'])
        self.photo_count = self.total_count - self.video_count
        
        self.total_pages = math.ceil(self.total_count / self.PAGE_SIZE) if self.total_count > 0 else 1
        
        self._setup_ui()
        self.after(50, lambda: self.load_page(1))

    def destroy(self):
        self.executor.shutdown(wait=False)
        super().destroy()

    def _setup_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, height=50, corner_radius=0)
        top_bar.pack(fill="x")
        
        ctk.CTkLabel(top_bar, text="Sort:", text_color=TEXT_DIM).pack(side="left", padx=(15, 5))
        self.sort_var = ctk.StringVar(value="Newest > Oldest")
        ctk.CTkOptionMenu(top_bar, values=["Newest > Oldest", "Oldest > Newest"], 
                          variable=self.sort_var, width=140, fg_color=BG_CARD, button_color=BG_HOVER,
                          command=self.on_sort_changed).pack(side="left", padx=5)
        
        self._add_stat(top_bar, f"{self.total_count}", TEXT_MAIN)
        self._add_stat(top_bar, f"{self.photo_count}", SNAP_BLUE, "camera")
        self._add_stat(top_bar, f"{self.video_count}", SNAP_RED, "video")

        self.nav_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        self.nav_frame.pack(side="right", padx=10)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="<", width=30, command=self.prev_page, fg_color=BG_CARD, hover_color=BG_HOVER)
        self.btn_prev.pack(side="left", padx=2)
        
        self.page_entry = ctk.CTkEntry(self.nav_frame, width=40, font=("Segoe UI", 12), justify="center", fg_color=BG_SIDEBAR, border_width=0)
        self.page_entry.pack(side="left", padx=(5, 0))
        self.page_entry.bind("<Return>", self.jump_to_page)
        self.page_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.page_entry.bind("<FocusOut>", self._on_entry_focus_out)
        
        self.lbl_total = ctk.CTkLabel(self.nav_frame, text=f"/ {self.total_pages}", width=40, font=("Segoe UI", 12))
        self.lbl_total.pack(side="left", padx=(0, 5))
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text=">", width=30, command=self.next_page, fg_color=BG_CARD, hover_color=BG_HOVER)
        self.btn_next.pack(side="left", padx=2)

        self.scroll_mems = ctk.CTkScrollableFrame(self, fg_color="transparent", 
                                                  scrollbar_button_color=SNAP_RED, 
                                                  scrollbar_button_hover_color="#c92248")
        self.scroll_mems.pack(fill="both", expand=True)
        self.scroll_mems.bind("<Configure>", self.on_resize)

        bottom_bar = ctk.CTkFrame(self, fg_color="transparent", height=40)
        bottom_bar.pack(fill="x", pady=10)
        
        self.btn_prev_b = ctk.CTkButton(bottom_bar, text="< Previous Page", width=120, command=self.prev_page, fg_color=BG_SIDEBAR, hover_color=BG_HOVER)
        self.btn_prev_b.pack(side="left", padx=20)
        
        self.btn_next_b = ctk.CTkButton(bottom_bar, text="Next Page >", width=120, command=self.next_page, fg_color=SNAP_BLUE, hover_color="#007ACC", text_color="white")
        self.btn_next_b.pack(side="right", padx=20)

    def _on_entry_focus_in(self, event):
        self.page_entry.configure(fg_color=BG_MAIN, border_width=1)

    def _on_entry_focus_out(self, event):
        self.page_entry.configure(fg_color=BG_SIDEBAR, border_width=0)
        if self.page_entry.get() != str(self.current_page):
            self.page_entry.delete(0, "end")
            self.page_entry.insert(0, str(self.current_page))

    def _add_stat(self, parent, text, color, icon_name=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=8)
        if icon_name:
            icon = assets.load_icon(icon_name, size=(16, 16))
            if icon: ctk.CTkLabel(f, text="", image=icon).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(f, text=text, font=("Segoe UI", 12, "bold"), text_color=color).pack(side="left")

    def open_media(self, path):
        playlist = [m['path'] for m in self.memories if m.get('path')]
        try: idx = playlist.index(path)
        except: idx = 0; playlist = [path]
        GlobalMediaPlayer(self, playlist, idx)

    def on_sort_changed(self, choice):
        reverse = (choice == "Newest > Oldest")
        self.memories.sort(key=lambda x: x['date'], reverse=reverse)
        self.load_page(1)

    def prev_page(self):
        if self.current_page > 1: self.load_page(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages: self.load_page(self.current_page + 1)

    def jump_to_page(self, event=None):
        self.focus()
        try:
            target = int(self.page_entry.get())
            if 1 <= target <= self.total_pages: self.load_page(target)
            else: self._reset_input()
        except ValueError: self._reset_input()

    def _reset_input(self):
        self.page_entry.delete(0, "end")
        self.page_entry.insert(0, str(self.current_page))

    def on_resize(self, event):
        if abs(event.width - self.last_width) > 30:
            self.last_width = event.width
            self.render_current_page_items()

    def load_page(self, page_num):
        self.current_page = page_num
        self._reset_input()
        self.lbl_total.configure(text=f"/ {self.total_pages}")
        
        state_prev = "normal" if page_num > 1 else "disabled"
        state_next = "normal" if page_num < self.total_pages else "disabled"
        
        self.btn_prev.configure(state=state_prev)
        self.btn_next.configure(state=state_next)
        self.btn_prev_b.configure(state=state_prev)
        self.btn_next_b.configure(state=state_next)

        self.render_current_page_items()
        self.scroll_mems._parent_canvas.yview_moveto(0.0)

    def render_current_page_items(self):
        # 1. Clear Scroll Frame
        for w in self.scroll_mems.winfo_children(): w.destroy()
            
        # 2. Get Data
        start = (self.current_page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        chunk = self.memories[start:end]
        if not chunk: return

        # 3. Calculate Layout
        w = self.scroll_mems.winfo_width()
        if w < 100: w = 1000
        
        cols = max(1, w // 204)
        card_width = int((w - (cols * 4)) / cols) 

        # 4. Build Rows (PACK STRATEGY)
        current_row_frame = None
        current_row_count = 0
        last_month_key = None
        
        for mem in chunk:
            try:
                dt = datetime.strptime(mem['date'], "%Y-%m-%d %H:%M:%S UTC")
                month_key = dt.strftime("%Y-%m")
                display_text = dt.strftime("%B %Y").upper()
            except:
                dt = None
                month_key = "Unknown"
                display_text = "UNKNOWN"

            if month_key != last_month_key:
                current_row_frame = None 
                current_row_count = 0
                header = MonthHeader(self.scroll_mems, display_text)
                header.pack(fill="x", pady=(10, 0))
                last_month_key = month_key

            if current_row_frame is None or current_row_count >= cols:
                current_row_frame = RowFrame(self.scroll_mems)
                current_row_frame.pack(fill="x", pady=2)
                current_row_count = 0
            
            card = MemoryCard(current_row_frame, mem, card_width, self.open_media, self.executor)
            card.pack(side="left", padx=2) 
            current_row_count += 1

        # 5. Add Bottom Padding
        ctk.CTkLabel(self.scroll_mems, text="", height=50).pack(pady=20)
        # FORCE UPDATE
        self.scroll_mems.update_idletasks()