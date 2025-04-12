import tkinter as tk
from tkinter import ttk, filedialog
import os
import yt_dlp
import threading
import re
import requests
from PIL import Image, ImageTk
from io import BytesIO

class VideoDownloader:
    def __init__(self, master):
        self.master = master
        master.title("YouTube Playlist Downloader")
        master.geometry("800x450")
        master.resizable(False, False) 
        master.configure(bg="#1e1e2f")

        style = ttk.Style()
        style.theme_use('clam')

        style.configure("TLabel", background="#1e1e2f", foreground="#ffffff", font=("Segoe UI", 12)) # حجم الخط
        style.configure("TButton", background="#3a3a4f", foreground="#ffffff", font=("Segoe UI", 11), padding=8) # حجم الخط و padding
        style.map("TButton", background=[("active", "#4f4f6f")])
        style.configure("TEntry", padding=8, font=("Segoe UI", 11))
        style.configure("TFrame", background="#1e1e2f")
        style.configure("TProgressbar", thickness=20, troughcolor="#2e2e40", background="#00ff88") # thickness

        # Playlist URL
        self.playlist_url_label = ttk.Label(master, text="Playlist URL:")
        self.playlist_url_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        url_frame = ttk.Frame(master)
        url_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.playlist_url_entry = ttk.Entry(url_frame, width=70)
        self.playlist_url_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)

        self.paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_playlist_url)
        self.paste_button.pack(side=tk.LEFT)

        # Save Path
        self.save_path_label = ttk.Label(master, text="Save Path:")
        self.save_path_label.grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")

        path_frame = ttk.Frame(master)
        path_frame.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.save_path_entry = ttk.Entry(path_frame, width=70)
        default_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        self.save_path_entry.insert(0, default_downloads)
        self.save_path_entry.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)

        self.browse_button = ttk.Button(path_frame, text="Browse", command=self.browse_folder)
        self.browse_button.pack(side=tk.LEFT)

        # Download Button
        self.download_button = ttk.Button(master, text="Download", command=self.start_download_thread)
        self.download_button.grid(row=4, column=0, pady=20)

        # Status Label
        self.status_label = tk.Label(master, text="", bg="#2e2e40", fg="#00ff88", font=("Segoe UI", 11), anchor="center")
        self.status_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(5, 0))
        self.status_label.grid_remove()

        # Progress Bar
        self.progress_bar = ttk.Progressbar(master, orient="horizontal", length=700, mode="determinate") # عرض اكبر
        self.progress_bar.grid(row=6, column=0, pady=10, padx=20, sticky="ew")
        self.progress_bar.grid_remove()

        # Video Info Frame
        self.video_info_frame = tk.Frame(master, bg="#2e2e40")
        self.video_info_frame.grid(row=7, column=0, pady=(5, 20), padx=20, sticky="ew")
        self.video_info_frame.grid_remove()

        # Video Image
        self.video_image_label = tk.Label(self.video_info_frame, bg="#2e2e40")
        self.video_image_label.pack(side=tk.LEFT, padx=(0, 10))

        # Video Info
        self.video_info_label = tk.Label(self.video_info_frame, text="", bg="#2e2e40", fg="white", font=("Segoe UI", 11), justify="left") # حجم الخط
        self.video_info_label.pack(side=tk.LEFT)

        self.video_count = 0
        self.current_video_index = 0
        self.progress_bar_shown = False

        master.columnconfigure(0, weight=1)
        master.rowconfigure(7, weight=1)
        url_frame.columnconfigure(0, weight=1)
        path_frame.columnconfigure(0, weight=1)

    def sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9-_ ]', '_', name)

    def paste_playlist_url(self):
        try:
            text = self.master.clipboard_get()
            self.playlist_url_entry.insert(tk.INSERT, text)
        except tk.TclError:
            pass

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
            ydl_opts = {'quiet': True}
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
            self.update_video_image(entry)

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
        self.progress_bar.grid_remove()
        self.status_label.grid_remove()
        self.video_info_frame.grid_remove()
        self.progress_bar_shown = False

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
        if self.status_label.winfo_manager() != "grid":
            self.status_label.grid(row=5, column=0, sticky="ew", padx=20, pady=(5, 0))
        self.status_label.config(text=message)
        self.master.update_idletasks()

    def update_video_info(self, info):
        if self.video_info_frame.winfo_manager() != "grid":
            self.video_info_frame.grid(row=7, column=0, pady=(5, 20), padx=20, sticky="ew")
        if not self.progress_bar_shown:
            self.progress_bar.grid(row=6, column=0, pady=10, padx=20, sticky="ew")
            self.progress_bar_shown = True
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

    def update_video_image(self, info):
        thumbnail_url = info.get('thumbnail')
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url, stream=True)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
                image.thumbnail((120, 90))
                photo = ImageTk.PhotoImage(image)
                self.video_image_label.config(image=photo)
                self.video_image_label.image = photo
            except requests.exceptions.RequestException as e:
                print(f"Error loading image: {e}")
                self.video_image_label.config(image='')
        else:
            self.video_image_label.config(image='')
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
