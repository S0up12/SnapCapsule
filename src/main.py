import customtkinter as ctk
from ui.main_window import MainWindow
from database.loader import DataManager
from utils.config_manager import ConfigManager
from utils.cache_manager import cache
import os

def main():
    # Load Config
    cfg = ConfigManager()
    
    # Initialize Data Manager
    data_manager = DataManager(cfg)
    
    # Initialize Thumbnail Cache
    # We use the configured data root as the base, or default to current dir
    root_path = cfg.get("data_root")
    if not root_path:
        root_path = os.getcwd()
    
    cache.init(root_path)

    # Start App
    app = MainWindow(data_manager, cfg)
    app.mainloop()

if __name__ == "__main__":
    main()