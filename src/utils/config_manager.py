import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "data_root": "",
    "memories_path": ""
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config = json.load(f)
            except:
                self.config = DEFAULT_CONFIG

    def save_config(self, data_root, memories_path):
        self.config["data_root"] = data_root
        self.config["memories_path"] = memories_path
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        return self.config.get(key, "")