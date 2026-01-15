import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.media_map = {} 
        self.raw_chats = {} 
        self.chat_index = [] 
        self.memories = []
        self.profile = {} 
        
        self.root = ""
        self.json_path = ""
        self.chat_media_path = ""

    def reload(self):
        """Reloads all data from the configured data root, prioritizing staged data."""
        self.media_map = {}
        self.raw_chats = {}
        self.chat_index = []
        self.memories = []
        self.profile = {}
        
        self.root = self.cfg.get("data_root")
        if not self.root or not os.path.exists(self.root):
            return [], [], {}

        # Priority: staged_data folder created during ZIP processing
        staged_path = os.path.join(self.root, "staged_data")
        data_src = staged_path if os.path.exists(staged_path) else self.root

        # Target staged chat_history first, then fallback to nested json/
        possible_chat_paths = [
            os.path.join(data_src, "chat_history.json"),
            os.path.join(data_src, "json", "chat_history.json")
        ]
        
        self.json_path = ""
        for p in possible_chat_paths:
            if os.path.exists(p):
                self.json_path = p
                break
            
        self.chat_media_path = os.path.join(self.root, "chat_media")
        
        # 1. Index Media (Fast)
        if os.path.exists(self.chat_media_path):
            print(f"⏳ Indexing Chat Media...")
            self._index_media(self.chat_media_path)
        
        # 2. Load Raw JSON
        if self.json_path:
            print(f"⏳ Loading Chat JSON from: {self.json_path}")
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.raw_chats = json.load(f)
                self.chat_index = sorted(list(self.raw_chats.keys()))
            except Exception as e:
                print(f"❌ JSON Load Error: {e}")
        
        # 3. Memories & Profile (Explicitly passing data_src)
        print("⏳ Parsing Memories...")
        self._parse_memories_list(data_src)

        print("⏳ Parsing Profile Data...")
        self._parse_profile_data(data_src)

        mem_path = self.cfg.get("memories_path") or os.path.join(self.root, "memories")
        if os.path.exists(mem_path):
             self._link_memories(mem_path)

        return self.chat_index, self.memories, self.profile

    def get_chat_messages(self, friend_name):
        if friend_name not in self.raw_chats: return []
        raw_msgs = self.raw_chats[friend_name]
        clean_msgs = []
        for msg in raw_msgs:
            txt = msg.get("Content") or ""
            media_ids = msg.get("Media IDs", "")
            files = []
            if media_ids:
                ids = media_ids if isinstance(media_ids, list) else str(media_ids).split(" | ")
                for mid in ids:
                    if mid in self.media_map: files.append(self.media_map[mid])
            date_str = msg.get("Created", "")
            nice_date = date_str
            try:
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    nice_date = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    dt = datetime.fromisoformat(date_str)
                    nice_date = dt.strftime("%Y-%m-%d %H:%M")
            except: pass
            clean_msgs.append({"sender": msg.get("From", "Unknown"), "date": nice_date, "text": txt, "media": files})
        return clean_msgs[::-1]

    def _index_media(self, folder_path):
        if not os.path.exists(folder_path): return
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file():
                    filename = entry.name
                    self.media_map[filename] = entry.path
                    if "_" in filename:
                        try:
                            parts = filename.split("_", 1)
                            if len(parts) > 1:
                                media_id = os.path.splitext(parts[1])[0]
                                self.media_map[media_id] = entry.path
                        except: continue

    def _parse_memories_list(self, data_src):
        # Check flat staged root first, then standard json/ directory
        mem_json = os.path.join(data_src, "memories_history.json")
        if not os.path.exists(mem_json):
            mem_json = os.path.join(data_src, "json", "memories_history.json")
        
        if not os.path.exists(mem_json): return
        try:
            with open(mem_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_list = data.get("Saved Media", [])
        except: return
        self.memories = [{"date": i.get("Date", ""), "type": i.get("Media Type", ""), "path": None, "url": i.get("Media Download Url", "")} for i in raw_list]

    def _link_memories(self, folder_path):
        if not os.path.exists(folder_path): return
        file_index = {}
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file():
                    file_index[os.path.splitext(entry.name)[0]] = entry.path
        for mem in self.memories:
            try:
                date_str = mem['date']
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    prefix = dt.strftime("%Y-%m-%d_%H-%M-%S")
                    if prefix in file_index: mem['path'] = file_index[prefix]
            except: pass

    def _parse_profile_data(self, data_src):
        # Determine if we are reading from flat staged folder or nested json/
        json_dir = data_src if os.path.exists(os.path.join(data_src, "account.json")) else os.path.join(data_src, "json")
        
        def load_safe(filename, key):
            p = os.path.join(json_dir, filename)
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f: return json.load(f).get(key, [])
                except: return []
            return []

        acc_path = os.path.join(json_dir, "account.json")
        if os.path.exists(acc_path):
            try:
                with open(acc_path, "r", encoding="utf-8") as f:
                    acc = json.load(f)
                    # Support both standard and root-level account structures
                    self.profile['basic'] = acc.get("Basic Information", acc)
                    self.profile['device_history'] = acc.get("Device History", [])
            except: pass
            
        self.profile['name_history'] = load_safe("account_history.json", "Display Name Change")
        friends_path = os.path.join(json_dir, "friends.json")
        if os.path.exists(friends_path):
            try:
                with open(friends_path, "r", encoding="utf-8") as f:
                    fr = json.load(f)
                    self.profile['friends_list'] = fr.get("Friends", [])
                    self.profile['stats'] = {"friends": len(self.profile['friends_list']), "deleted": len(fr.get("Deleted Friends", [])), "blocked": len(fr.get("Blocked Users", []))}
            except: pass

        user_prof_path = os.path.join(json_dir, "user_profile.json")
        if os.path.exists(user_prof_path):
            try:
                with open(user_prof_path, "r", encoding="utf-8") as f:
                    eng = json.load(f).get("Engagement", [])
                    self.profile['engagement'] = {item["Event"]: item["Occurrences"] for item in eng if isinstance(item, dict) and "Event" in item} if isinstance(eng, list) else {}
            except: pass

        self.profile['places'] = load_safe("snap_map_places_history.json", "Snap Map Places History")[:100]

    def perform_integrity_check(self):
        """Cross-references JSON records with physical files to fix blank Settings views."""
        report = {"chats": {"total": 0, "missing": 0}, "memories": {"total": 0, "missing": 0}}
        for friend in self.raw_chats:
            msgs = self.raw_chats[friend]
            for msg in msgs:
                mids = msg.get("Media IDs", "")
                if mids:
                    ids = mids if isinstance(mids, list) else str(mids).split(" | ")
                    for mid in ids:
                        report["chats"]["total"] += 1
                        if mid not in self.media_map: report["chats"]["missing"] += 1
        for mem in self.memories:
            report["memories"]["total"] += 1
            path = mem.get("path")
            if not path or not os.path.exists(path):
                report["memories"]["missing"] += 1
        return report