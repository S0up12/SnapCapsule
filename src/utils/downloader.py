import os
import requests
import json
import shutil
import concurrent.futures
import time
import zipfile
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

class MemoryDownloader:
    def __init__(self, status_callback, progress_callback):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancelled = False
        self._executor = None

    def process_data_package(self, zip_path, extract_root, download_memories=True):
        self.cancelled = False
        try:
            self.status_callback("Extracting ZIP archive...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                files = z.namelist()
                for i, file in enumerate(files):
                    if self.cancelled: break
                    z.extract(file, extract_root)
                    self.progress_callback((i + 1) / len(files) * 0.33)
            
            if self.cancelled: return False

            actual_root = self._find_snap_root(extract_root)
            staging_path = os.path.join(actual_root, "staged_data")
            if not os.path.exists(staging_path): 
                os.makedirs(staging_path)
                
            self.status_callback("Syncing and converting logs...")
            self._stage_all_data(actual_root, staging_path)
            
            if download_memories:
                self.download_memories(os.path.join(staging_path, "memories_history.json"), 
                                       os.path.join(actual_root, "memories"))
            
            self.status_callback("Data Staging Complete")
            self.progress_callback(1.0)
            return True
        except Exception as e:
            self.status_callback(f"Process Error: {str(e)}")
            return False
    
    def _find_snap_root(self, extract_root):
        if os.path.exists(os.path.join(extract_root, "json")) or os.path.exists(os.path.join(extract_root, "html")):
            return extract_root
        
        for item in os.listdir(extract_root):
            path = os.path.join(extract_root, item)
            if os.path.isdir(path):
                if os.path.exists(os.path.join(path, "json")) or os.path.exists(os.path.join(path, "html")):
                    return path
        return extract_root

    def _stage_all_data(self, root, stage_dir):
        json_src = os.path.join(root, "json")
        html_src = os.path.join(root, "html")
        chat_media_path = Path(root) / "chat_media"
        
        # Copy native JSONs
        if os.path.exists(json_src):
            for f in os.listdir(json_src):
                if f.endswith(".json"): 
                    shutil.copy2(os.path.join(json_src, f), os.path.join(stage_dir, f))
        
        # Convert HTMLs with Deep Search logic
        if os.path.exists(html_src): 
            self._convert_html_dir(html_src, stage_dir, chat_media_path)

    def _convert_html_dir(self, html_dir, stage_dir, chat_media_path):
        chat_html_dir = os.path.join(html_dir, "chat_history")
        if not os.path.exists(chat_html_dir): return
        staged_chat_path = os.path.join(stage_dir, "chat_history.json")
        
        master_chats = {}
        if os.path.exists(staged_chat_path):
            try:
                with open(staged_chat_path, "r", encoding="utf-8") as f: 
                    master_chats = json.load(f)
            except: pass

        html_files = [f for f in os.listdir(chat_html_dir) if f.endswith(".html")]
        for i, filename in enumerate(html_files):
            raw_name = os.path.splitext(filename)[0].replace("subpage_", "")
            # Integrated resolution logic here
            friend_name, msgs = self._parse_chat_html(os.path.join(chat_html_dir, filename), raw_name, chat_media_path)
            
            if friend_name and msgs:
                target_key = friend_name if friend_name != "Unknown" else raw_name
                existing = master_chats.get(target_key, [])
                
                seen = {f"{m.get('Created')}_{m.get('Content')}" for m in existing}
                new_entries = [m for m in msgs if f"{m.get('Created')}_{m.get('Content')}" not in seen]
                
                master_chats[target_key] = existing + new_entries
            
            self.progress_callback(0.33 + ((i + 1) / len(html_files) * 0.33))
            
        with open(staged_chat_path, "w", encoding="utf-8") as f: 
            json.dump(master_chats, f, indent=4)

    def _parse_chat_html(self, file_path, fallback_name, chat_media_path):
        """Refined parser that resolves media using timestamp matching."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                soup = BeautifulSoup(f, 'html.parser')
            
            messages = []
            message_blocks = soup.find_all(['span'], recursive=True)
            
            for block in message_blocks:
                ts_tag = block.find('h6')
                if not ts_tag: continue
                
                sender_tag = block.find('h4')
                content_tag = block.find('p')
                media_indicator = block.find('span', string=lambda s: s and s.strip() in ["MEDIA", "IMAGE", "VIDEO"])
                
                sender = sender_tag.text.strip() if sender_tag else fallback_name
                content = content_tag.text.strip() if content_tag else ""
                timestamp = ts_tag.text.strip()
                
                media_ids = ""
                # Deep Search Resolution: Match physical media to HTML timestamp
                if media_indicator:
                    media_ids = self._resolve_physical_media(timestamp, chat_media_path)

                msg_data = {
                    "From": sender, 
                    "Created": timestamp, 
                    "Content": content, 
                    "Media IDs": media_ids
                }
                
                if msg_data not in messages:
                    messages.append(msg_data)
            
            return fallback_name, messages
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None, []

    def _resolve_physical_media(self, timestamp_str, chat_media_path):
        """
        Implementation of the matching logic from converter.py.
        Attempts to link HTML records to physical files in chat_media.
        """
        if not chat_media_path.exists():
            return ""
            
        # Format: 2025-07-05 09:25:12 UTC -> 2025-07-05
        date_part = timestamp_str.split(' ')[0]
        
        candidates = []
        for f in chat_media_path.iterdir():
            if f.name.startswith(date_part):
                candidates.append(f)
        
        if not candidates:
            return ""

        # Prefer variants that aren't overlays or thumbnails
        primary = [c for c in candidates if not any(x in c.name for x in ["overlay", "thumbnail"])]
        selected = primary[0] if primary else candidates[0]
        
        # Return as an ID (filename base) for the loader to map
        return os.path.splitext(selected.name)[0]

    def download_memories(self, json_path, download_folder):
        if not os.path.exists(json_path): return
        try:
            with open(json_path, "r", encoding="utf-8") as f: data = json.load(f)
            memories = data.get("Saved Media", []) if isinstance(data, dict) else data
        except: return
        if not os.path.exists(download_folder): os.makedirs(download_folder)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            self._executor = executor
            futures = {executor.submit(self._download_single, m, download_folder): m for m in memories}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if self.cancelled: break
                progress = 0.66 + ((i + 1) / len(memories) * 0.34)
                self.progress_callback(progress)
                self.status_callback(f"Downloading Memories... {int(progress*100)}%")

    def _download_single(self, item, folder):
        url, date_str = item.get("Media Download Url"), item.get("Date")
        if not url or not date_str: return "failed"
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
            filepath = os.path.join(folder, f"{dt.strftime('%Y-%m-%d_%H-%M-%S')}.jpg")
            if os.path.exists(filepath): return "skipped"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                with open(filepath, 'wb') as f: f.write(r.content)
                return "success"
        except: return "failed"