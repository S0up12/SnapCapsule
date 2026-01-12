import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.media_map = {} 
        self.chats = {}
        self.memories = []
        self.profile = {} 
        
        self.root = ""
        self.json_path = ""
        self.chat_media_path = ""

    def reload(self):
        self.media_map = {}
        self.chats = {}
        self.memories = []
        self.profile = {}
        
        self.root = self.cfg.get("data_root")
        
        if not self.root or not os.path.exists(self.root):
            return {}, [], {}

        self.json_path = os.path.join(self.root, "json", "chat_history.json")
        self.chat_media_path = os.path.join(self.root, "chat_media")
        
        if os.path.exists(self.chat_media_path):
            print(f"⏳ Indexing Chat Media...")
            self._index_media(self.chat_media_path)
        
        if os.path.exists(self.json_path):
            print("⏳ Parsing Chats...")
            self._parse_chats()
        
        print("⏳ Parsing Memories...")
        self._parse_memories_list()

        print("⏳ Parsing Profile Data...")
        self._parse_profile_data()

        mem_path = self.cfg.get("memories_path")
        if mem_path and os.path.exists(mem_path):
             self._link_memories(mem_path)

        return self.chats, self.memories, self.profile

    def _index_media(self, folder_path):
        if not os.path.exists(folder_path): return
        for filename in os.listdir(folder_path):
            try:
                self.media_map[filename] = os.path.join(folder_path, filename)
                if "_" in filename:
                     parts = filename.split("_", 1)
                     if len(parts) > 1:
                         media_id = os.path.splitext(parts[1])[0]
                         self.media_map[media_id] = os.path.join(folder_path, filename)
            except: continue

    def _parse_chats(self):
        if not os.path.exists(self.json_path): return
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for friend, messages in data.items():
            clean_msgs = []
            for msg in messages:
                txt = msg.get("Content") or ""
                media_ids = msg.get("Media IDs", "")
                files = []
                if media_ids:
                    for mid in media_ids.split(" | "):
                        if mid in self.media_map: files.append(self.media_map[mid])

                date_str = msg.get("Created", "")
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    nice_date = dt.strftime("%Y-%m-%d %H:%M")
                except: nice_date = date_str

                clean_msgs.append({"sender": msg.get("From", "Unknown"), "date": nice_date, "text": txt, "media": files})
            self.chats[friend] = clean_msgs[::-1]

    def _parse_memories_list(self):
        mem_json = os.path.join(self.root, "json", "memories_history.json")
        if not os.path.exists(mem_json): return
        
        with open(mem_json, "r", encoding="utf-8") as f:
            raw_list = json.load(f).get("Saved Media", [])

        self.memories = []
        for item in raw_list:
            self.memories.append({
                "date": item.get("Date", ""),
                "type": item.get("Media Type", ""),
                "path": None, 
                "url": item.get("Media Download Url", "")
            })

    def _link_memories(self, folder_path):
        if not os.path.exists(folder_path): return
        mem_index = {f: os.path.join(folder_path, f) for f in os.listdir(folder_path)}
        for mem in self.memories:
            try:
                dt = datetime.strptime(mem['date'], "%Y-%m-%d %H:%M:%S UTC")
                prefix = dt.strftime("%Y-%m-%d_%H-%M-%S")
                for fname in mem_index:
                    if fname.startswith(prefix):
                        mem['path'] = mem_index[fname]
                        break
            except: pass

    def _parse_profile_data(self):
        json_dir = os.path.join(self.root, "json")
        
        # 1. Basic Account Info
        acc_path = os.path.join(json_dir, "account.json")
        if os.path.exists(acc_path):
            with open(acc_path, "r", encoding="utf-8") as f:
                acc = json.load(f)
                self.profile['basic'] = acc.get("Basic Information", {})
                self.profile['device_history'] = acc.get("Device History", [])

        # 2. Account History
        hist_path = os.path.join(json_dir, "account_history.json")
        if os.path.exists(hist_path):
            with open(hist_path, "r", encoding="utf-8") as f:
                hist = json.load(f)
                self.profile['name_history'] = hist.get("Display Name Change", [])

        # 3. Friends Stats (UPDATED)
        friends_path = os.path.join(json_dir, "friends.json")
        if os.path.exists(friends_path):
            with open(friends_path, "r", encoding="utf-8") as f:
                fr = json.load(f)
                
                # STORE THE LIST
                self.profile['friends_list'] = fr.get("Friends", [])
                
                self.profile['stats'] = {
                    "friends": len(self.profile['friends_list']),
                    "deleted": len(fr.get("Deleted Friends", [])),
                    "blocked": len(fr.get("Blocked Users", []))
                }

        # 4. Engagement
        user_prof_path = os.path.join(json_dir, "user_profile.json")
        if os.path.exists(user_prof_path):
            with open(user_prof_path, "r", encoding="utf-8") as f:
                eng = json.load(f).get("Engagement", [])
                eng_dict = {item["Event"]: item["Occurrences"] for item in eng}
                self.profile['engagement'] = eng_dict

        # 5. Travel
        places_path = os.path.join(json_dir, "snap_map_places_history.json")
        if os.path.exists(places_path):
            with open(places_path, "r", encoding="utf-8") as f:
                places = json.load(f).get("Snap Map Places History", [])
                self.profile['places'] = places[:50]