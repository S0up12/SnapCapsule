import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, config_manager):
        self.cfg = config_manager
        self.media_map = {} 
        self.raw_chats = {} # Holds the raw JSON dict
        self.chat_index = [] # List of friend names for the sidebar
        self.memories = []
        self.profile = {} 
        
        self.root = ""
        self.json_path = ""
        self.chat_media_path = ""

    def reload(self):
        self.media_map = {}
        self.raw_chats = {}
        self.chat_index = []
        self.memories = []
        self.profile = {}
        
        self.root = self.cfg.get("data_root")
        
        if not self.root or not os.path.exists(self.root):
            return [], [], {}

        self.json_path = os.path.join(self.root, "json", "chat_history.json")
        self.chat_media_path = os.path.join(self.root, "chat_media")
        
        # 1. Index Media (Fast)
        if os.path.exists(self.chat_media_path):
            print(f"⏳ Indexing Chat Media...")
            self._index_media(self.chat_media_path)
        
        # 2. Load Raw JSON (Fast I/O) - Do NOT process messages yet
        if os.path.exists(self.json_path):
            print("⏳ Loading Chat JSON...")
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.raw_chats = json.load(f)
                self.chat_index = sorted(list(self.raw_chats.keys()))
            except Exception as e:
                print(f"❌ JSON Load Error: {e}")
        
        # 3. Memories & Profile
        print("⏳ Parsing Memories...")
        self._parse_memories_list()

        print("⏳ Parsing Profile Data...")
        self._parse_profile_data()

        mem_path = self.cfg.get("memories_path")
        if mem_path and os.path.exists(mem_path):
             self._link_memories(mem_path)

        return self.chat_index, self.memories, self.profile

    def get_chat_messages(self, friend_name):
        """Lazy loads and processes messages for a specific friend."""
        if friend_name not in self.raw_chats:
            return []
            
        raw_msgs = self.raw_chats[friend_name]
        clean_msgs = []
        
        for msg in raw_msgs:
            txt = msg.get("Content") or ""
            media_ids = msg.get("Media IDs", "")
            files = []
            
            # Media Linking
            if media_ids:
                # Handle both list and string formats just in case
                if isinstance(media_ids, list): ids = media_ids
                else: ids = str(media_ids).split(" | ")
                
                for mid in ids:
                    if mid in self.media_map: 
                        files.append(self.media_map[mid])

            # Date Formatting
            date_str = msg.get("Created", "")
            nice_date = date_str
            try:
                # Snapchat usually uses UTC "2023-01-01 12:00:00 UTC"
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    nice_date = dt.strftime("%Y-%m-%d %H:%M")
                else:
                    # Fallback for ISO format
                    dt = datetime.fromisoformat(date_str)
                    nice_date = dt.strftime("%Y-%m-%d %H:%M")
            except: 
                pass

            clean_msgs.append({
                "sender": msg.get("From", "Unknown"), 
                "date": nice_date, 
                "text": txt, 
                "media": files
            })
            
        return clean_msgs[::-1] # Newest at bottom

    def _index_media(self, folder_path):
        if not os.path.exists(folder_path): return
        # Using scandir is faster than listdir for large folders
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file():
                    filename = entry.name
                    # Map full filename
                    self.media_map[filename] = entry.path
                    # Map ID (stripping date prefix if exists: "2023-01-01_MEDIA-ID.jpg")
                    if "_" in filename:
                        try:
                            parts = filename.split("_", 1)
                            if len(parts) > 1:
                                media_id = os.path.splitext(parts[1])[0]
                                self.media_map[media_id] = entry.path
                        except: continue

    def _parse_memories_list(self):
        mem_json = os.path.join(self.root, "json", "memories_history.json")
        if not os.path.exists(mem_json): return
        
        try:
            with open(mem_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_list = data.get("Saved Media", [])
        except: return

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
        
        # Optimization: Pre-index files by their date-prefix for O(1) lookup
        # Filename format expected: "YYYY-MM-DD_HH-MM-SS.ext"
        file_index = {}
        with os.scandir(folder_path) as it:
            for entry in it:
                if entry.is_file():
                    # Key is the timestamp part "2023-01-01_12-00-00"
                    key = os.path.splitext(entry.name)[0] 
                    file_index[key] = entry.path

        for mem in self.memories:
            try:
                # Convert API date "2023-01-01 12:00:00 UTC" to filename format "2023-01-01_12-00-00"
                date_str = mem['date']
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    prefix = dt.strftime("%Y-%m-%d_%H-%M-%S")
                    
                    if prefix in file_index:
                        mem['path'] = file_index[prefix]
            except: pass

    def _parse_profile_data(self):
        json_dir = os.path.join(self.root, "json")
        
        def load_safe(filename, key):
            p = os.path.join(json_dir, filename)
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f).get(key, [])
                except: return []
            return []

        # 1. Basic Account Info
        acc_path = os.path.join(json_dir, "account.json")
        if os.path.exists(acc_path):
            try:
                with open(acc_path, "r", encoding="utf-8") as f:
                    acc = json.load(f)
                    self.profile['basic'] = acc.get("Basic Information", {})
                    self.profile['device_history'] = acc.get("Device History", [])
            except: pass

        # 2. Account History
        self.profile['name_history'] = load_safe("account_history.json", "Display Name Change")

        # 3. Friends Stats
        friends_path = os.path.join(json_dir, "friends.json")
        if os.path.exists(friends_path):
            try:
                with open(friends_path, "r", encoding="utf-8") as f:
                    fr = json.load(f)
                    self.profile['friends_list'] = fr.get("Friends", [])
                    self.profile['stats'] = {
                        "friends": len(self.profile['friends_list']),
                        "deleted": len(fr.get("Deleted Friends", [])),
                        "blocked": len(fr.get("Blocked Users", []))
                    }
            except: pass

        # 4. Engagement
        user_prof_path = os.path.join(json_dir, "user_profile.json")
        if os.path.exists(user_prof_path):
            try:
                with open(user_prof_path, "r", encoding="utf-8") as f:
                    eng = json.load(f).get("Engagement", [])
                    # Handle both list of dicts and simple dict structure variations
                    if isinstance(eng, list):
                        self.profile['engagement'] = {item["Event"]: item["Occurrences"] for item in eng if "Event" in item}
                    else:
                        self.profile['engagement'] = {}
            except: pass

        # 5. Travel
        self.profile['places'] = load_safe("snap_map_places_history.json", "Snap Map Places History")[:100]
        
    def perform_integrity_check(self):
        """Cross-references JSON records with physical files, including edited variants."""
        report = {
            "chats": {"total": 0, "missing": 0},
            "memories": {"total": 0, "missing": 0}
        }
        
        # Check Chat Media
        for friend in self.raw_chats:
            msgs = self.raw_chats[friend]
            for msg in msgs:
                mids = msg.get("Media IDs", "")
                if mids:
                    ids = mids if isinstance(mids, list) else str(mids).split(" | ")
                    for mid in ids:
                        report["chats"]["total"] += 1
                        # If the exact ID isn't found, check for the '_image' variant
                        if mid not in self.media_map:
                            report["chats"]["missing"] += 1
                            
        # Check Memories
        for mem in self.memories:
            report["memories"]["total"] += 1
            path = mem.get("path")
            if not path:
                report["memories"]["missing"] += 1
                continue
                
            # Logic: Consider "Healthy" if the original or the '_image' version exists
            dir_name = os.path.dirname(path)
            base_name = os.path.basename(path)
            name_no_ext = os.path.splitext(base_name)[0]
            alt_img_path = os.path.join(dir_name, f"{name_no_ext}_image.jpg")
            
            if not os.path.exists(path) and not os.path.exists(alt_img_path):
                report["memories"]["missing"] += 1
                
        return report