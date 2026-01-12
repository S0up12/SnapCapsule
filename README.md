
# 📸 SnapCapsule

A beautiful, modern desktop application to view your exported Snapchat data. It reconstructs your chat history like a real messaging app, visualizes your travel history, and creates a browsable gallery for your memories.

## ✨ Features

* **💬 Chat History Viewer:**
    * **Rich Media:** See images and videos directly in the chat bubble.
    * **Cinema Mode:** Click any media to open it in a full-overlay player.
    * **Carousel:** Navigate through chat media using arrow keys.
* **🎞️ Memories Gallery:**
    * **Masonry Grid:** Browse all your downloaded Memories in a responsive grid.
    * **Smart Playback:** Auto-detects audio-only files and plays them smoothly.
* **🎥 Universal Media Player:**
    * **Embedded Overlay:** Plays video/audio directly over the app (no popup windows).
    * **Format Support:** Handles MP4, MOV, AVI, and audio-only files without crashing.
    * **System Fallback:** "Open in System" button for stubborn files.
* **👤 Profile & Insights:**
    * **Travel Log:** A scrollable timeline of visited locations.
    * **Stats:** Friend counts and messaging statistics.
* **⬇️ Integrated Downloader:**
    * Automatically downloads your Memories from the JSON links.
* **🔒 Privacy Focused:**
    * Runs 100% locally on your computer. No data is ever uploaded.

## 🛠️ Installation

### Prerequisites
* **Python 3.10 or higher** installed on your system.

### 1. Setup
Open your terminal/command prompt in this folder and run:

```
# Install required libraries (including the new audio engine)
pip install -r requirements.txt
```

### 2. Prepare Your Data
You need your Snapchat data export (JSON files) and your media files.

1. Request your data from Snapchat (Settings -> My Data).
2. Download the ZIP file (e.g., 'mydata~12345.zip').
3. Unzip it. You should see a folder containing subfolders like json/, chat_media/, etc.

## 🚀 How to Run

1. **Start the app**

    ```
    python src/main.py
    ```

2. **First Time Configuration (Home Tab):**

    * **Select Data Folder:** Browse and select the **unzipped folder** from Step 2 (the one containing the 'json' and 'chat_media' folders).
    * **Download Memories (Optional):** If you haven't downloaded your memories yet, select a destination folder and click **Start Download.** The app will fetch them for you.
    * Click **Save Settings & Load Data**.

3. **Enjoy!**
    * Navigate to **Chats** to read history.
    * Navigate to **Memories** to view you gallery.
    * Click any media to open the **Cinema Mode** player.

## ⚠️ Troubleshooting

* **Audio not playing?:** Ensure ffpyplayer is installed (pip install ffpyplayer).

* **"Missing" in Memories:** This means the app found a record of a memory in the JSON, but could not find the matching file on your computer. Ensure you have pointed the app to the correct folder where your memories were downloaded.

* **Video Thumbnails not showing:** Ensure you have opencv-python installed (pip install opencv-python).

## 📄 License
This project is for personal use only.