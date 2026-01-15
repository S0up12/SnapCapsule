import os
import requests
import json
import shutil
import concurrent.futures
import time
import zipfile
from datetime import datetime
from bs4 import BeautifulSoup

class MemoryDownloader:
    def __init__(self, status_callback, progress_callback):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancelled = False
        self._executor = None

    def process_data_package(self, zip_path, extract_root, download_memories=True):
        self.cancelled = False
        try:
            # 1. Unzip
            self.status_callback("📦 Extracting ZIP archive...")
            with zipfile.ZipFile(zip_path, 'r') as z:
                files = z.namelist()
                for i, file in enumerate(files):
                    if self.cancelled: break
                    z.extract(file, extract_root)
                    self.progress_callback((i + 1) / len(files) * 0.33)
            
            if self.cancelled: return False

            # 2. Locate folder containing the logs (e.g. "mydata~123/")
            actual_root = self._find_snap_root(extract_root)

            # 3. Create staged_data INSIDE that folder
            staging_path = os.path.join(actual_root, "staged_data")
            if not os.path.exists(staging_path): 
                os.makedirs(staging_path)
                
            self.status_callback("⚡ Syncing JSON and HTML logs...")
            self._stage_all_data(actual_root, staging_path)
            
            if download_memories:
                self.download_memories(os.path.join(staging_path, "memories_history.json"), 
                                       os.path.join(actual_root, "memories"))
            
            self.status_callback("🎉 Data Staging Complete!")
            self.progress_callback(1.0)
            return True
        except Exception as e:
            self.status_callback(f"❌ Process Error: {str(e)}")
            return False
    
    def _find_snap_root(self, extract_root):
        """Locates the folder containing 'json' or 'html' directories."""
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
        
        # Copy native JSONs
        if os.path.exists(json_src):
            for f in os.listdir(json_src):
                if f.endswith(".json"): 
                    shutil.copy2(os.path.join(json_src, f), os.path.join(stage_dir, f))
        
        # Convert HTMLs
        if os.path.exists(html_src): 
            self._convert_html_dir(html_src, stage_dir)

    def _convert_html_dir(self, html_dir, stage_dir):
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
            # Pass the filename as a fallback friend name
            raw_name = os.path.splitext(filename)[0].replace("subpage_", "")
            friend_name, msgs = self._parse_chat_html(os.path.join(chat_html_dir, filename), raw_name)
            
            if friend_name and msgs:
                # Use the friend name determined by the parser or the filename
                target_key = friend_name if friend_name != "Unknown" else raw_name
                existing = master_chats.get(target_key, [])
                
                # Deduplication logic
                seen = {f"{m.get('Created')}_{m.get('Content')}" for m in existing}
                new_entries = [m for m in msgs if f"{m.get('Created')}_{m.get('Content')}" not in seen]
                
                master_chats[target_key] = existing + new_entries
            
            self.progress_callback(0.33 + ((i + 1) / len(html_files) * 0.33))
            
        with open(staged_chat_path, "w", encoding="utf-8") as f: 
            json.dump(master_chats, f, indent=4)

    def _parse_chat_html(self, file_path, fallback_name):
        """Deep Search Parser that identifies 'MEDIA' tags to link files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                soup = BeautifulSoup(f, 'html.parser')
            
            messages = []
            # Modern Snap HTML groups messages in spans containing h4, p, and h6
            message_blocks = soup.find_all(['span'], recursive=True)
            
            for block in message_blocks:
                ts_tag = block.find('h6')
                if not ts_tag: continue
                
                sender_tag = block.find('h4')
                content_tag = block.find('p')
                # Identify if this is a Media message by looking for the "MEDIA" label
                media_indicator = block.find('span', string="MEDIA")
                
                sender = sender_tag.text.strip() if sender_tag else fallback_name
                content = content_tag.text.strip() if content_tag else ""
                timestamp = ts_tag.text.strip()
                
                media_ids = ""
                # If "MEDIA" is found, generate an ID matching the filename format: YYYY-MM-DD_HH-MM-SS
                if media_indicator:
                    try:
                        # Convert "2025-03-25 20:31:32 UTC" -> "2025-03-25_20-31-32"
                        clean_ts = timestamp.replace(" UTC", "")
                        dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                        media_ids = dt.strftime("%Y-%m-%d_%H-%M-%S")
                    except:
                        pass

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