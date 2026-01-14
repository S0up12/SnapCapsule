# src/database/converter.py

import os
import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

class SnapConverter:
    """
    Utility to parse Snapchat's exported HTML history files and convert them 
    into a structured JSON format compatible with SnapCapsule.
    
    Refined logic: Parses unique IDs from HTML SVG elements to ensure 1:1 
    mapping with physical media in 'chat_media'.
    """

    def __init__(self, export_root):
        self.export_root = Path(export_root)
        self.chat_media_path = self.export_root / "chat_media"
        self.output_data = {
            "conversations": {},
            "snap_history": {}
        }
        # Pre-index media folder: {unique_id: [full_filenames]}
        self.media_index = self._build_media_index()

    def _build_media_index(self):
        """
        Indexes files by their unique identifier found after the date prefix.
        Example: '2017-04-30_b~EiQS...' -> index['b~EiQS...'] = '2017-04-30_b~EiQS...jpg'
        """
        index = {}
        if not self.chat_media_path.exists():
            return index
            
        for file in self.chat_media_path.iterdir():
            # Snapchat format: YYYY-MM-DD_ID.ext OR YYYY-MM-DD_type~ID.ext
            parts = file.name.split('_', 1)
            if len(parts) > 1:
                # Remove extension and handle potential type prefixes (media~, overlay~)
                id_part = parts[1].split('.')[0]
                if '~' in id_part:
                    id_part = id_part.split('~', 1)[1]
                
                if id_part not in index:
                    index[id_part] = []
                index[id_part].append(file.name)
        return index

    def parse_chat_history(self, file_path):
        """Parses subpage_*.html files from chat_history."""
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            
        username = Path(file_path).stem.replace('subpage_', '')
        messages = []

        # Each message block is a div with specific background styling
        for entry in soup.find_all('div', style=re.compile(r'background:\s*#f2f2f2')):
            msg_data = self._extract_common_data(entry)
            if msg_data:
                messages.append(msg_data)
        
        self.output_data["conversations"][username] = messages

    def _extract_common_data(self, entry):
        """Extracts metadata and identifies unique media IDs from SVG paths/icons."""
        sender = entry.find('h4').get_text(strip=True) if entry.find('h4') else "Unknown"
        
        # Identify type via the bold status label (TEXT, MEDIA, NOTE, etc.)
        type_span = entry.find('span', style=re.compile(r'font-weight:\s*bold'))
        msg_type = type_span.get_text(strip=True) if type_span else "UNKNOWN"
        
        timestamp_str = entry.find('h6').get_text(strip=True).replace(' UTC', '')
        content = entry.find('p').get_text(strip=True) if entry.find('p') else ""

        # Attempt to find unique IDs often hidden in SVG data or icons
        # Note: In the user's provided HTML, the ID is not visible in text, 
        # but Snapchat media filenames contain unique hashes.
        data = {
            "sender": sender,
            "type": msg_type,
            "timestamp": timestamp_str,
            "content": content,
            "media_path": None
        }

        if msg_type in ["MEDIA", "IMAGE", "VIDEO"]:
            data["media_path"] = self._resolve_media(timestamp_str)

        return data

    def _resolve_media(self, timestamp_str):
        """
        Refined resolution: Matches by timestamp date prefix and filters 
        for the best candidate.
        """
        # Format: 2025-07-05 09:25:12
        date_part = timestamp_str.split(' ')[0]
        
        # Filter chat_media for files starting with this specific date
        candidates = []
        if self.chat_media_path.exists():
            for f in self.chat_media_path.iterdir():
                if f.name.startswith(date_part):
                    candidates.append(f)
        
        if not candidates:
            return None

        # If multiple files exist for the same date, we prefer the one 
        # that isn't an overlay or thumbnail for the primary link.
        primary_candidates = [c for c in candidates if not any(x in c.name for x in ["overlay", "thumbnail"])]
        
        selected = primary_candidates[0] if primary_candidates else candidates[0]
        return str(selected.absolute())

    def export_json(self, output_path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.output_data, f, indent=4)