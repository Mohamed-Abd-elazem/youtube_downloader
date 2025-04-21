import sys
import os
import yt_dlp
import threading
import re
import requests
from PIL import Image
from io import BytesIO
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class VideoDownloader(QMainWindow):
    progress_signal = pyqtSignal(float)
    status_signal = pyqtSignal(str)
    video_info_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Playlist Downloader")
        self.setFixedSize(900, 500)
        self.setup_ui()
        
        # Initialize variables
        self.video_count = 0
        self.current_video_index = 0
        
    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # URL Section
        url_group = QGroupBox("Playlist URL")
        url_layout = QHBoxLayout()
        
        self.url_entry = QLineEdit()
        self.paste_btn = QPushButton("Paste")
        self.paste_btn.clicked.connect(self.paste_playlist_url)
        
        url_layout.addWidget(self.url_entry)
        url_layout.addWidget(self.paste_btn)
        url_group.setLayout(url_layout)
        
        # Save Path Section
        path_group = QGroupBox("Save Location")
        path_layout = QHBoxLayout()
        
        self.path_entry = QLineEdit()
        self.path_entry.setText(os.path.join(os.path.expanduser("~"), "Downloads"))
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.path_entry)
        path_layout.addWidget(self.browse_btn)
        path_group.setLayout(path_layout)
        
        # Download Button
        self.download_btn = QPushButton("Download Playlist")
        self.download_btn.clicked.connect(self.start_download_thread)
        self.download_btn.setFixedHeight(40)
        
        # Status Label
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.hide()
        
        # Video Info Section
        self.video_info_widget = QWidget()
        video_info_layout = QHBoxLayout(self.video_info_widget)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        
        self.video_info_label = QLabel()
        
        video_info_layout.addWidget(self.thumbnail_label)
        video_info_layout.addWidget(self.video_info_label)
        video_info_layout.addStretch()
        
        self.video_info_widget.hide()
        
        # Add widgets to main layout
        main_layout.addWidget(url_group)
        main_layout.addWidget(path_group)
        main_layout.addWidget(self.download_btn)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.video_info_widget)
        main_layout.addStretch()
        
        # Connect signals
        self.progress_signal.connect(self.update_progress)
        self.status_signal.connect(self.update_status)
        self.video_info_signal.connect(self.update_video_info)
        
        # Apply styling
        self.apply_styles()
        
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a2e;
            }
            QWidget {
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QGroupBox {
                background-color: #16213e;
                border: 1px solid #1f4068;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
            }
            QGroupBox::title {
                color: #4ecca3;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit {
                background-color: #1f4068;
                border: none;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QPushButton {
                background-color: #4ecca3;
                color: #1a1a2e;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45b393;
            }
            QPushButton:pressed {
                background-color: #3da183;
            }
            QProgressBar {
                background-color: #1f4068;
                border: none;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4ecca3;
                border-radius: 3px;
            }
            QLabel {
                color: #ffffff;
            }
            #status_label {
                color: #4ecca3;
                font-size: 13px;
            }
        """)
        
    def paste_playlist_url(self):
        clipboard = QApplication.clipboard()
        self.url_entry.setText(clipboard.text())
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Location")
        if folder:
            self.path_entry.setText(folder)
            
    def sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9-_ ]', '_', name)
        
    def start_download_thread(self):
        self.download_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        thread = threading.Thread(target=self.download_playlist)
        thread.daemon = True
        thread.start()
        
    def download_playlist(self):
        playlist_url = self.url_entry.text().strip()
        save_path = self.path_entry.text().strip()
        
        if not playlist_url:
            self.status_signal.emit("Please enter a playlist URL.")
            self.download_btn.setEnabled(True)
            return
            
        if not save_path:
            save_path = os.getcwd()
            
        self.status_signal.emit("Fetching playlist details...")
        
        try:
            ydl_opts = {'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
        except Exception as e:
            self.status_signal.emit(f"Error fetching playlist: {str(e)}")
            self.download_btn.setEnabled(True)
            return
            
        if 'entries' not in playlist_info or not playlist_info['entries']:
            self.status_signal.emit("The playlist is empty or invalid.")
            self.download_btn.setEnabled(True)
            return
            
        playlist_title = self.sanitize_filename(playlist_info.get('title', 'Playlist'))
        playlist_folder = os.path.join(save_path, playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)
        
        video_entries = playlist_info['entries']
        self.video_count = len(video_entries)
        self.status_signal.emit(f"Found {self.video_count} videos. Starting download...")
        
        for index, entry in enumerate(video_entries, start=1):
            self.current_video_index = index
            video_id = entry.get('id')
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            video_title = self.sanitize_filename(entry.get('title', f'video_{index}'))
            self.status_signal.emit(f"Downloading video {index}/{self.video_count}: {video_title}")
            self.video_info_signal.emit(entry)
            
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
                    self.status_signal.emit(f"Failed to download video {index}: {str(e)}")
                    
        self.status_signal.emit("All videos have been downloaded successfully!")
        self.progress_bar.hide()
        self.video_info_widget.hide()
        self.download_btn.setEnabled(True)
        
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            percent = float(d['_percent_str'].strip('%'))
            self.progress_signal.emit(percent)
        elif d['status'] == 'finished':
            self.progress_signal.emit(100)
            
    @pyqtSlot(float)
    def update_progress(self, percent):
        self.progress_bar.setValue(int(percent))
        
    @pyqtSlot(str)
    def update_status(self, message):
        self.status_label.setText(message)
        
    @pyqtSlot(dict)
    def update_video_info(self, info):
        self.video_info_widget.show()
        
        # Update thumbnail
        thumbnail_url = info.get('thumbnail')
        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url)
                image = Image.open(BytesIO(response.content))
                image.thumbnail((160, 90))
                qimage = QImage(image.tobytes(), image.width, image.height, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                self.thumbnail_label.setPixmap(pixmap)
            except:
                self.thumbnail_label.clear()
                
        # Update info text
        title = info.get('title', 'Unknown Title')
        filesize = info.get('filesize_approx', 0)
        resolution = info.get('resolution', 'Unknown')
        
        if filesize > 1024 * 1024:
            filesize_str = f"{filesize / (1024 * 1024):.2f} MB"
        elif filesize > 1024:
            filesize_str = f"{filesize / 1024:.2f} KB"
        else:
            filesize_str = f"{filesize} B"
            
        info_text = f"Title: {title}\nSize: {filesize_str}\nResolution: {resolution}"
        self.video_info_label.setText(info_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoDownloader()
    window.show()
    sys.exit(app.exec_())