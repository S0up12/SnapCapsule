import os
import requests
import json
import shutil
import concurrent.futures
import time
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

class MemoryDownloader:
    def __init__(self, status_callback, progress_callback):
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.cancelled = False
        self._executor = None

    def cancel(self):
        """Signals the download process to abort."""
        self.cancelled = True
        self.status_callback("⛔ Stopping download...")

    def download_memories(self, json_path, download_folder):
        self.cancelled = False
        
        # 1. Validation
        if not os.path.exists(json_path):
            self.status_callback("❌ JSON file not found.")
            logger.warning("Memories JSON not found at %s", json_path)
            return

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Handle list vs dict structure
            memories = data.get("Saved Media", []) if isinstance(data, dict) else data
        except Exception as exc:
            self.status_callback(f"❌ JSON Error: {exc}")
            logger.error("Failed to parse memories JSON at %s", json_path, exc_info=True)
            return

        total_files = len(memories)
        if total_files == 0:
            self.status_callback("✅ No memories found to download.")
            self.progress_callback(1.0)
            return

        if not os.path.exists(download_folder):
            try:
                os.makedirs(download_folder)
            except Exception:
                self.status_callback("❌ Invalid Download Folder.")
                logger.warning("Invalid download folder: %s", download_folder, exc_info=True)
                return

        # 2. Disk Space Check
        # Estimate: ~3MB per photo, ~20MB per video (Conservative avg)
        est_size = 0
        for m in memories:
            if "video" in m.get("Media Type", "").lower(): est_size += 20 * 1024 * 1024
            else: est_size += 3 * 1024 * 1024
        
        total, used, free = shutil.disk_usage(download_folder)
        
        if free < est_size:
            free_mb = free // (1024 * 1024)
            req_mb = est_size // (1024 * 1024)
            self.status_callback(f"⚠️ Low Disk Space! Free: {free_mb}MB, Est. Need: {req_mb}MB")
            logger.warning(
                "Low disk space for downloads at %s (free=%sMB, needed=%sMB)",
                download_folder,
                free_mb,
                req_mb,
            )
            return # Stop execution

        # 3. Start Download
        self.status_callback(f"🚀 Starting download of {total_files} files...")
        
        success = 0
        failed = 0
        skipped = 0
        
        # Using a ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            self._executor = executor
            futures = {executor.submit(self._download_single, m, download_folder): m for m in memories}
            
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                if self.cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                try:
                    item = futures[future]
                    result = future.result()
                    if result == "success": success += 1
                    elif result == "skipped": skipped += 1
                    else: failed += 1
                except Exception:
                    failed += 1
                    logger.debug("Download worker failed for item: %s", item, exc_info=True)
                
                # Update UI
                progress = (i + 1) / total_files
                self.progress_callback(progress)
                self.status_callback(f"Downloading... ✅{success} ⏭️{skipped} ❌{failed}")

        # Final Report
        if self.cancelled:
            self.status_callback("⛔ Download Cancelled")
            self.progress_callback(0)
        else:
            self.status_callback(f"🎉 Done! Saved: {success}, Skipped: {skipped}, Failed: {failed}")
            self.progress_callback(1.0)

    def _download_single(self, item, folder):
        if self.cancelled: return "cancelled"
        
        url = item.get("Media Download Url")
        date_str = item.get("Date")
        
        if not url or not date_str: return "failed"

        try:
            # Generate Filename
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
            timestamp = dt.strftime("%Y-%m-%d_%H-%M-%S")
            is_video = "video" in item.get("Media Type", "").lower()
            ext = ".mp4" if is_video else ".jpg" 
            
            filename = f"{timestamp}{ext}"
            filepath = os.path.join(folder, filename)

            # Check Existing
            if os.path.exists(filepath):
                return "skipped"

            # RETRY LOGIC (Max 3 attempts)
            last_error = None
            for attempt in range(3):
                if self.cancelled: return "cancelled"
                
                try:
                    with requests.get(url, stream=True, timeout=15) as r:
                        if r.status_code == 200:
                            with open(filepath, 'wb') as f:
                                shutil.copyfileobj(r.raw, f)
                            return "success"
                        last_error = f"HTTP {r.status_code}"
                except Exception as exc:
                    last_error = str(exc) or "Network error"
                    logger.debug("Download attempt failed for %s", url, exc_info=True)
                
                # Wait before retry (0.5s, 1.0s, etc if desired)
                time.sleep(1)

            # If loop finishes without success
            if last_error:
                logger.warning("Download failed for %s (%s)", url, last_error)
            return "failed"
                    
        except Exception:
            logger.error("Download failed for %s", url, exc_info=True)
            return "failed"
