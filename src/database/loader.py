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

    def reload(self):
        self.media_map = {}
        self.raw_chats = {}
        self.chat_index = []
        self.memories = []
        self.profile = {}
        
        self.root = self.cfg.get("data_root")
        if not self.root or not os.path.exists(self.root):
            return [], [], {}

        staged_path = os.path.join(self.root, "staged_data")
        data_src = staged_path if os.path.exists(staged_path) else self.root

        # Index media first so chat loading can link immediately
        self.chat_media_path = os.path.join(self.root, "chat_media")
        mem_path = self.cfg.get("memories_path") or os.path.join(self.root, "memories")
        
        if os.path.exists(self.chat_media_path):
            self._index_media_directory(self.chat_media_path)
        if os.path.exists(mem_path):
            self._index_media_directory(mem_path)
        
        # Load Chat History
        json_path = os.path.join(data_src, "chat_history.json")
        if not os.path.exists(json_path):
            json_path = os.path.join(data_src, "json", "chat_history.json")

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.raw_chats = json.load(f)
                self.chat_index = sorted(list(self.raw_chats.keys()))
            except Exception as e:
                print(f"JSON Load Error: {e}")
        
        self._parse_memories_list(data_src)
        self._parse_profile_data(data_src)
        self._link_memories_from_map()

        return self.chat_index, self.memories, self.profile

    def _index_media_directory(self, folder_path):
        """Builds a map of filenames and unique Snapchat IDs to full paths."""
        if not os.path.exists(folder_path): return
    
        with os.scandir(folder_path) as it:
            for entry in it:
                if not entry.is_file(): continue
            
                name = entry.name
                path = entry.path
                name_no_ext = os.path.splitext(name)[0]
            
                # Map full filename and name without extension
                self.media_map[name] = path
                self.media_map[name_no_ext] = path
            
                # Handle Snapchat ID extraction (ID is usually after the first underscore)
                if "_" in name:
                    parts = name.split("_", 1)
                    mid_with_ext = parts[1]
                    mid = os.path.splitext(mid_with_ext)[0]

                    # Strip common suffixes to get the base ID
                    clean_id = mid.replace("media~", "").replace("overlay~", "").replace("_image", "").replace("_caption", "")
                    
                    # Store clean ID if not present, or if this is the primary image
                    if clean_id not in self.media_map or "_image" in name:
                        self.media_map[clean_id] = path

    def get_chat_messages(self, friend_name):
        if friend_name not in self.raw_chats: return []
        raw_msgs = self.raw_chats[friend_name]
        clean_msgs = []
        
        for msg in raw_msgs:
            txt = msg.get("Content") or ""
            media_ids = msg.get("Media IDs", "")
            files = []
            
            if media_ids:
                # Handle both list format and string 'ID | ID' format
                ids = media_ids if isinstance(media_ids, list) else str(media_ids).split(" | ")
                for mid in ids:
                    mid = mid.strip()
                    if mid in self.media_map:
                        files.append(self.media_map[mid])
            
            date_str = msg.get("Created", "")
            nice_date = date_str
            try:
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                else:
                    dt = datetime.fromisoformat(date_str)
                nice_date = dt.strftime("%Y-%m-%d %H:%M")
            except: pass
            
            clean_msgs.append({
                "sender": msg.get("From", "Unknown"), 
                "date": nice_date, 
                "text": txt, 
                "media": files
            })
            
        return clean_msgs[::-1]

    def _parse_memories_list(self, data_src):
        possible_paths = [os.path.join(data_src, "memories_history.json"), os.path.join(data_src, "json", "memories_history.json")]
        mem_json = next((p for p in possible_paths if os.path.exists(p)), "")
        if not mem_json: return
        try:
            with open(mem_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                raw_list = data.get("Saved Media", [])
        except: return
        self.memories = [{"date": i.get("Date", ""), "type": i.get("Media Type", ""), "path": None, "url": i.get("Media Download Url", "")} for i in raw_list]

    def _link_memories_from_map(self):
        for mem in self.memories:
            try:
                date_str = mem['date']
                if "UTC" in date_str:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
                    prefix = dt.strftime("%Y-%m-%d_%H-%M-%S")
                    if prefix in self.media_map:
                        mem['path'] = self.media_map[prefix]
            except: pass

    def _parse_profile_data(self, data_src):
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
        report = {"chats": {"total": 0, "missing": 0}, "memories": {"total": 0, "missing": 0}}
        for friend in self.raw_chats:
            msgs = self.raw_chats[friend]
            for msg in msgs:
                mids = msg.get("Media IDs", "")
                if mids:
                    ids = mids if isinstance(mids, list) else str(mids).split(" | ")
                    for mid in ids:
                        mid = mid.strip()
                        report["chats"]["total"] += 1
                        if mid not in self.media_map: report["chats"]["missing"] += 1
        for mem in self.memories:
            report["memories"]["total"] += 1
            path = mem.get("path")
            if not path or not os.path.exists(path):
                report["memories"]["missing"] += 1
        return report