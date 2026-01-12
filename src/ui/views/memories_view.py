import customtkinter as ctk
from PIL import Image, ImageOps
import os
from datetime import datetime
from utils.image_utils import extract_video_thumbnail, add_play_icon
from ui.theme import *
from ui.components.media_viewer import GlobalMediaPlayer
from utils.assets import assets  # <--- NEW IMPORT

class MemoryCard(ctk.CTkFrame):
    def __init__(self, parent, memory, width, click_callback):
        super().__init__(parent, fg_color="transparent", width=width, height=200)
        self.pack_propagate(False) 
        self.path = memory['path']
        self.current_width = width
        self.click_callback = click_callback
        
        if self.path and os.path.exists(self.path):
            self.render_preview(self.path)
        else:
            self.render_placeholder(is_missing=True)

    def render_placeholder(self, is_missing=False):
        # UPDATED: Use Icons
        icon_name = "alert-triangle" if is_missing else "file-text"
        label_text = "Missing" if is_missing else "No Preview"
        
        bg = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        bg.pack(expand=True, fill="both")
        
        # Icon Button (Centered)
        icon = assets.load_icon(icon_name, size=(32, 32))
        
        btn = ctk.CTkButton(bg, 
                            text=label_text, 
                            image=icon, 
                            compound="top",
                            fg_color="transparent", 
                            hover_color="#252525", 
                            text_color="#666",
                            font=("Segoe UI", 12, "bold"),
                            command=lambda: self.click_callback(self.path))
        btn.place(relx=0, rely=0, relwidth=1, relheight=1)

    def render_preview(self, path):
        ext = os.path.splitext(path)[1].lower()
        pil_img = None
        is_video = False
        try:
            if ext in ['.jpg', '.jpeg', '.png']:
                pil_img = Image.open(path)
            elif ext in ['.mp4', '.mov']:
                is_video = True
                pil_img = extract_video_thumbnail(path)

            if pil_img:
                pil_img = ImageOps.fit(pil_img, (self.current_width, 200), method=Image.Resampling.LANCZOS)
                if is_video: pil_img = add_play_icon(pil_img)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(self.current_width, 200))
                self.image_ref = ctk_img 
                
                btn = ctk.CTkButton(self, text="", image=ctk_img, fg_color="transparent", hover=False, 
                                    command=lambda: self.click_callback(self.path), corner_radius=0)
                btn.pack(expand=True, fill="both")
            else:
                self.render_placeholder(is_missing=False)
        except: 
            self.render_placeholder(is_missing=False)

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
        self.page = 0
        self.grid_items = [] 
        self.last_width = 0
        self.total_count = 0
        self.video_count = 0
        self.photo_count = 0
        self._calculate_stats()
        self.scroll_mems = None
        self.btn_load = None
        self._setup_ui()
        if self.memories: self.load_chunk()

    def _calculate_stats(self):
        self.total_count = len(self.memories)
        self.video_count = 0
        self.photo_count = 0
        for mem in self.memories:
            path = mem.get('path', '')
            if not path: continue
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.mp4', '.mov']: self.video_count += 1
            elif ext in ['.jpg', '.jpeg', '.png']: self.photo_count += 1

    def _setup_ui(self):
        filter_frame = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, height=45, corner_radius=0)
        filter_frame.pack(fill="x")
        
        ctk.CTkLabel(filter_frame, text="Sort:", text_color=TEXT_DIM).pack(side="left", padx=(15, 5))
        self.sort_var = ctk.StringVar(value="Newest > Oldest")
        sort_menu = ctk.CTkOptionMenu(filter_frame, values=["Newest > Oldest", "Oldest > Newest"], 
                                      variable=self.sort_var, width=140, fg_color=BG_CARD, button_color=BG_HOVER,
                                      command=self.on_sort_changed)
        sort_menu.pack(side="left", padx=5)
        
        stats_frame = ctk.CTkFrame(filter_frame, fg_color="transparent")
        stats_frame.pack(side="right", padx=20)
        
        # UPDATED: Pass Icon names
        self._add_stat(stats_frame, f"Total: {self.total_count}", TEXT_MAIN, None)
        self._add_stat(stats_frame, f"{self.photo_count}", SNAP_BLUE, "camera")
        self._add_stat(stats_frame, f"{self.video_count}", SNAP_RED, "video")

        self.scroll_mems = ctk.CTkScrollableFrame(self, fg_color="transparent", 
                                                  scrollbar_button_color=SNAP_RED, 
                                                  scrollbar_button_hover_color="#c92248")
        self.scroll_mems.pack(fill="both", expand=True)
        self.scroll_mems.grid_columnconfigure(0, weight=1)
        self.scroll_mems.bind("<Configure>", self.on_resize)
        
        self.btn_load = ctk.CTkButton(self.scroll_mems, text="Load More", width=200, height=40,
                                      command=self.load_chunk, fg_color=BG_CARD, hover_color=BG_HOVER, text_color=TEXT_MAIN)

    def _add_stat(self, parent, text, color, icon_name=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(side="left", padx=8)
        
        # Add Icon if provided
        if icon_name:
            icon = assets.load_icon(icon_name, size=(16, 16))
            if icon:
                ctk.CTkLabel(f, text="", image=icon).pack(side="left", padx=(0, 5))
            
        ctk.CTkLabel(f, text=text, font=("Segoe UI", 12, "bold"), text_color=color).pack(side="left")

    # --- CAROUSEL LOGIC ---
    def open_media(self, path):
        # 1. Build Playlist (Only items with valid paths)
        playlist = [m['path'] for m in self.memories if m.get('path')]
        
        # 2. Find Index
        try:
            idx = playlist.index(path)
        except ValueError:
            idx = 0
            playlist = [path]
            
        # 3. Launch
        GlobalMediaPlayer(self, playlist, idx)

    def on_sort_changed(self, choice):
        reverse = (choice == "Newest > Oldest")
        self.memories.sort(key=lambda x: x['date'], reverse=reverse)
        for item in self.grid_items: item['widget'].destroy()
        self.grid_items = []
        if self.btn_load: self.btn_load.grid_forget()
        self.page = 0
        self.scroll_mems._parent_canvas.yview_moveto(0.0)
        self.load_chunk()

    def load_chunk(self):
        self.btn_load.grid_forget()
        self.update_idletasks()
        start = self.page * 50
        end = start + 50
        chunk = self.memories[start:end]
        w = self.scroll_mems.winfo_width()
        if w < 100: w = 1000 
        cols = max(1, w // 204)
        card_width = int((w - (cols * 4)) / cols)

        for mem in chunk:
            try:
                dt = datetime.strptime(mem['date'], "%Y-%m-%d %H:%M:%S UTC")
                month_key = dt.strftime("%Y-%m")
                display_text = dt.strftime("%B %Y").upper()
            except:
                dt = None
                month_key = "Unknown"
                display_text = "UNKNOWN DATE"

            last_month = None
            if self.grid_items:
                last_item = self.grid_items[-1]
                if last_item['type'] == 'card' and last_item['date_obj']:
                    last_month = last_item['date_obj'].strftime("%Y-%m")
            
            if month_key != last_month:
                header = MonthHeader(self.scroll_mems, display_text)
                self.grid_items.append({'type': 'header', 'widget': header, 'date_obj': dt})

            # Pass self.open_media as callback
            card = MemoryCard(self.scroll_mems, mem, card_width, click_callback=self.open_media)
            self.grid_items.append({'type': 'card', 'widget': card, 'date_obj': dt})
        
        self.page += 1
        self.reorganize()
        self.update_idletasks()

    def reorganize(self):
        w = self.scroll_mems.winfo_width()
        if w < 100: return
        PAD = 2
        cols = max(1, w // 204)
        card_width = int((w - (cols * (PAD*2))) / cols)
        current_row = 0
        current_col = 0
        
        for item in self.grid_items:
            widget = item['widget']
            if item['type'] == 'header':
                if current_col > 0:
                    current_row += 1
                    current_col = 0
                widget.grid(row=current_row, column=0, columnspan=cols, sticky="ew", padx=0, pady=(10, 0))
                current_row += 1
            else:
                if hasattr(widget, 'configure'):
                    widget.configure(width=card_width)
                    if hasattr(widget, 'current_width'): widget.current_width = card_width
                widget.grid(row=current_row, column=current_col, padx=PAD, pady=PAD, sticky="n")
                current_col += 1
                if current_col >= cols:
                    current_col = 0
                    current_row += 1
        if len(self.memories) > len(self.grid_items):
            if current_col > 0: current_row += 1
            self.btn_load.grid(row=current_row, column=0, columnspan=cols, pady=20)
            self.btn_load.lift()

    def on_resize(self, event):
        if abs(event.width - self.last_width) > 30:
            self.last_width = event.width
            self.reorganize()