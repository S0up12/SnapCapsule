import customtkinter as ctk
from ui.main_window import MainWindow
from database.loader import DataManager
from utils.config_manager import ConfigManager
from utils.cache_manager import cache
import os

def main():
    cfg = ConfigManager()
    data_manager = DataManager(cfg)
    
    # Initialize Cache in standard system location
    cache.init()

    app = MainWindow(data_manager, cfg)
    app.mainloop()

if __name__ == "__main__":
    main()