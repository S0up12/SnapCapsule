import json
import os
from pathlib import Path

class ConfigManager:
    def __init__(self):
        # Resolve standard Windows AppData (Roaming) path
        self.app_data_dir = Path(os.environ.get('APPDATA', Path.home())) / "SnapCapsule"
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.app_data_dir / "config.json"
        
        self.default_config = {
            "data_root": "",
            "memories_path": "",
            "appearance_mode": "System"
        }
        self.config = self.default_config.copy()
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)
                    for key in self.default_config:
                        if key in loaded:
                            self.config[key] = loaded[key]
            except:
                self.config = self.default_config.copy()

    def save_config(self, data_root, memories_path, appearance_mode=None):
        self.config["data_root"] = data_root
        self.config["memories_path"] = memories_path
        if appearance_mode:
            self.config["appearance_mode"] = appearance_mode
        
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        return self.config.get(key, self.default_config.get(key, ""))