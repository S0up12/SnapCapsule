import json
import os
from utils.logger import get_logger

logger = get_logger(__name__)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "data_root": "",
    "memories_path": "",
    "appearance_mode": "System" # Default to System
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    loaded = json.load(f)
                    # Merge loaded values into the default config
                    for key in DEFAULT_CONFIG:
                        if key in loaded:
                            self.config[key] = loaded[key]
            except Exception:
                logger.warning("Failed to load config from %s; using defaults.", CONFIG_FILE, exc_info=True)
                self.config = DEFAULT_CONFIG.copy()

    def save_config(self, data_root, memories_path, appearance_mode=None):
        self.config["data_root"] = data_root
        self.config["memories_path"] = memories_path
        
        # FIX: Explicitly update the dictionary before writing to file
        if appearance_mode:
            self.config["appearance_mode"] = appearance_mode
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key, ""))
