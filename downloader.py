import tkinter as tk
from tkinter import ttk, filedialog
import os
import yt_dlp
import threading
import re

class VideoDownloader:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Playlist Downloader")
        master.geometry("700x480")
        master.configure(bg="#1e1e2f")

        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TLabel", background="#1e1e2f", foreground="#ffffff", font=("Segoe UI", 11))
        style.configure("TButton", background="#3a3a4f", foreground="#ffffff", font=("Segoe UI", 10), padding=6)
        style.map("TButton", background=[("active", "#4f4f6f")])
        style.configure("TEntry", padding=6, font=("Segoe UI", 10))
        style.configure("TFrame", background="#1e1e2f")
        style.configure("TProgressbar", thickness=18)

        # Playlist URL
        self.playlist_url_label = ttk.Label(master, text="Playlist URL:")
        self.playlist_url_label.pack(pady=(20, 5))
        self.playlist_url_entry = ttk.Entry(master, width=80)
        self.playlist_url_entry.pack(pady=5)
        self.playlist_url_entry.bind("<Control-v>", self.paste_playlist_url)

        # Save Path
        self.save_path_label = ttk.Label(master, text="Save Path:")
        self.save_path_label.pack(pady=(15, 5))

        path_frame = ttk.Frame(master)
        path_frame.pack(pady=5)

        self.save_path_entry = ttk.Entry(path_frame, width=62)
        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_path_entry.insert(0, default_downloads)
        self.save_path_entry.pack(side=tk.LEFT, padx=(0, 5))

        self.browse_button = ttk.Button(path_frame, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT)

        # Download Button
        self.download_button = ttk.Button(master, text="Download", command=self.start_download_thread)
        self.download_button.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(master, text="", bg="#2e2e40", fg="#00ff88", font=("Segoe UI", 10), anchor="center")
        self.status_label.pack(fill=tk.X, padx=20, pady=(5, 0))

        # Progress Bar
        self.progress_bar = ttk.Progressbar(master, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Video Info
        self.video_info_label = tk.Label(master, text="", bg="#2e2e40", fg="white", font=("Segoe UI", 10), justify="center")
        self.video_info_label.pack(fill=tk.X, padx=20, pady=(5, 20))

        self.video_count = 0
        self.current_video_index = 0

    def sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9-_ ]', '_', name)

    def paste_playlist_url(self, event):
        self.playlist_url_entry.insert(tk.INSERT, self.master.clipboard_get())
        return "break"

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_path_entry.delete(0, tk.END)
            self.save_path_entry.insert(0, folder)

    def download_playlist(self):
        playlist_url = self.playlist_url_entry.get().strip()
        save_path = self.save_path_entry.get().strip()

        if not playlist_url:
            self.update_status("Please enter a playlist URL.")
            return

        if not save_path:
            save_path = os.getcwd()

        self.update_status("Fetching playlist details...")

        try:
            ydl_opts = {'quiet': True, 'extract_flat': False}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
        except Exception as e:
            self.update_status(f"Error fetching playlist: {e}")
            return

        if 'entries' not in playlist_info or not playlist_info['entries']:
            self.update_status("The playlist is empty or invalid.")
            return

        playlist_title = self.sanitize_filename(playlist_info.get('title', 'Playlist'))
        playlist_folder = os.path.join(save_path, playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)

        video_entries = playlist_info['entries']
        self.video_count = len(video_entries)
        self.update_status(f"Found {self.video_count} videos. Starting download...")

        for index, entry in enumerate(video_entries, start=1):
            self.current_video_index = index
            video_id = entry.get('id')
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            video_title = self.sanitize_filename(entry.get('title', f'video_{index}'))
            self.update_status(f"Downloading video {index}/{self.video_count}: {video_title}")
            self.update_video_info(entry)

            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': os.path.join(playlist_folder, f'{video_title}.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    ydl.download([video_url])
                except Exception as e:
                    self.update_status(f"Failed to download video {index}: {e}")

        self.update_status("All videos have been downloaded successfully!")
        self.progress_bar["value"] = 0

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = float(d['_percent_str'].strip('%'))
            self.update_progress(percent / 100)
        elif d['status'] == 'finished':
            self.update_progress(1)

    def update_progress(self, percent):
        self.progress_bar["value"] = percent * 100
        self.master.update_idletasks()

    def update_status(self, message):
        self.status_label.config(text=message)
        self.master.update_idletasks()

    def update_video_info(self, info):
        title = info.get('title', 'Unknown Title')
        filesize = info.get('filesize_approx', 0)
        resolution = info.get('resolution', 'Unknown')
        if filesize > 1024 * 1024:
            filesize_str = f"{filesize / (1024 * 1024):.2f} MB"
        elif filesize > 1024:
            filesize_str = f"{filesize / 1024:.2f} KB"
        else:
            filesize_str = f"{filesize} B"
        self.video_info_label.config(text=f"Title: {title}\nSize: {filesize_str}\nResolution: {resolution}")
        self.master.update_idletasks()

    def start_download_thread(self):
        self.download_button.config(state="disabled")
        self.progress_bar["value"] = 0
        thread = threading.Thread(target=self.download_playlist)
        thread.daemon = True
        thread.start()
        self.master.after(100, self.check_thread, thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.master.after(100, self.check_thread, thread)
        else:
            self.download_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoDownloader(root)
    root.mainloop()
