import customtkinter as ctk
import os
import sys
from ui.views.profile_view import ProfileView
from ui.views.chat_view import ChatView
from ui.views.memories_view import MemoriesView
from ui.views.home_view import HomeView
from ui.theme import *
from utils.assets import assets

SCROLL_SPEED = 20

class MainWindow(ctk.CTk):
    def __init__(self, data_manager, config_manager):
        super().__init__()
        self.data_manager = data_manager
        self.cfg = config_manager
        
        self.title("SnapCapsule")
        
        # --- SET WINDOW ICON ---
        try:
            icon_path = assets.get_path("snapcapsule.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Warning: Could not set window icon: {e}")

        # --- PROPORTIONAL MINIMUM SIZE ---
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        default_w, default_h = 1200, 800
        x_pos = (screen_w - default_w) // 2
        y_pos = (screen_h - default_h) // 2
        self.geometry(f"{default_w}x{default_h}+{x_pos}+{y_pos}")
        self.minsize(int(screen_w * 0.6), int(screen_h * 0.7))
        
        ctk.set_appearance_mode("Dark")
        
        self.chat_index, self.memories, self.profile = self.data_manager.reload()
        
        self.view_home = None
        self.view_profile = None
        self.view_chat = None
        self.view_memories = None

        self._setup_ui()
        
        self.bind_all("<MouseWheel>", self._on_global_mouse_wheel)
        self.bind_all("<Button-4>", self._on_global_mouse_wheel)
        self.bind_all("<Button-5>", self._on_global_mouse_wheel)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.show_home_view()

    def on_closing(self):
        print("🛑 Shutting down...")
        if self.view_chat: self.view_chat.cleanup()
        self.destroy()
        os._exit(0)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=0, minsize=80) 
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        self.nav_frame = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, width=80)
        self.nav_frame.grid(row=0, column=0, sticky="nsew")
        self.nav_frame.grid_propagate(False)
        
        # --- APP LOGO ---
        logo_img = assets.load_image("snapcapsule", size=(50, 50))
        if logo_img:
            ctk.CTkLabel(self.nav_frame, text="", image=logo_img).pack(pady=(25, 15))
        else:
            ctk.CTkLabel(self.nav_frame, text="👻", font=("Segoe UI", 30)).pack(pady=(20, 10))
        
        self.nav_buttons = {}
        
        nav_items = [
            ("Home", self.show_home_view, "home", "home"),
            ("Chats", self.show_chats_view, "chat", "message-square"),
            ("Profile", self.show_profile_view, "profile", "user"),
            ("Mems", self.show_memories_view, "memories", "save")
        ]

        for text, cmd, key, icon_name in nav_items:
            self._add_nav_btn(text, cmd, key, icon_name)

        self.content_frame = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

    def _add_nav_btn(self, text, cmd, key, icon_name):
        icon = assets.load_icon(icon_name, size=(24, 24))
        btn = ctk.CTkButton(self.nav_frame, 
                            text=text, 
                            image=icon,
                            compound="top",
                            width=60, 
                            height=60, 
                            fg_color="transparent", 
                            hover_color=BG_HOVER, 
                            text_color=TEXT_DIM,
                            command=cmd, 
                            font=("Segoe UI", 11, "bold"))
        btn.pack(pady=10, padx=5)
        self.nav_buttons[key] = btn

    def _update_active_tab(self, key):
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color="transparent", text_color=TEXT_DIM)
        if key in self.nav_buttons:
            btn = self.nav_buttons[key]
            btn.configure(fg_color=BG_HOVER, text_color=SNAP_YELLOW)

    def _hide_all_views(self):
        if self.view_chat and self.view_chat.winfo_ismapped():
            self.view_chat.cleanup()
        for view in [self.view_home, self.view_profile, self.view_chat, self.view_memories]:
            if view: view.grid_forget()

    def show_home_view(self):
        self._hide_all_views()
        self._update_active_tab("home")
        if not self.view_home:
            self.view_home = HomeView(self.content_frame, self)
            self.view_home.grid(row=0, column=0, sticky="nsew")
        else: self.view_home.grid(row=0, column=0, sticky="nsew")

    def show_chats_view(self):
        self._hide_all_views()
        self._update_active_tab("chat")
        if not self.view_chat:
            self.view_chat = ChatView(self.content_frame, self.data_manager, self.profile)
            self.view_chat.grid(row=0, column=0, sticky="nsew")
        else:
            self.view_chat.chat_list = self.chat_index 
            self.view_chat.grid(row=0, column=0, sticky="nsew")

    def show_profile_view(self):
        self._hide_all_views()
        self._update_active_tab("profile")
        if self.view_profile: self.view_profile.destroy()
        self.view_profile = ProfileView(self.content_frame, self.profile)
        self.view_profile.grid(row=0, column=0, sticky="nsew")

    def show_memories_view(self):
        self._hide_all_views()
        self._update_active_tab("memories")
        if not self.view_memories:
            self.view_memories = MemoriesView(self.content_frame, self.memories)
            self.view_memories.grid(row=0, column=0, sticky="nsew")
        else: self.view_memories.grid(row=0, column=0, sticky="nsew")

    def _on_global_mouse_wheel(self, event):
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        if not widget: return
        
        target = None
        w_str = str(widget) 
        
        def is_inside(parent_widget):
            return parent_widget and str(parent_widget) in w_str

        if self.view_memories and self.view_memories.winfo_ismapped():
            target = self.view_memories.scroll_mems
        elif self.view_chat and self.view_chat.winfo_ismapped():
            if is_inside(self.view_chat.scroll_friends):
                target = self.view_chat.scroll_friends
            else:
                target = self.view_chat.scroll_chat
        elif self.view_profile and self.view_profile.winfo_ismapped():
            if hasattr(self.view_profile, 'friends_scroll') and is_inside(self.view_profile.friends_scroll):
                target = self.view_profile.friends_scroll
            elif hasattr(self.view_profile, 'device_scroll') and is_inside(self.view_profile.device_scroll):
                target = self.view_profile.device_scroll
            elif hasattr(self.view_profile, 'name_scroll') and is_inside(self.view_profile.name_scroll):
                target = self.view_profile.name_scroll
            elif hasattr(self.view_profile, 'map_scroll') and is_inside(self.view_profile.map_scroll):
                target = self.view_profile.map_scroll

        if target:
            try:
                steps = 0
                if os.name == 'nt':
                     steps = int(-1 * (event.delta / 120)) * SCROLL_SPEED
                elif event.num == 4:
                     steps = -1 * SCROLL_SPEED
                elif event.num == 5:
                     steps = 1 * SCROLL_SPEED
                
                if steps == 0: return

                # CRITICAL FIX: Removed boundary checks to allow native handling
                target._parent_canvas.yview_scroll(steps, "units")
            except: pass