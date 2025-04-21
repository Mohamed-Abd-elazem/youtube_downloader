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
        self.setWindowTitle("YouTube Downloader")
        self.setFixedSize(900, 500)
        
        # Add download control variables
        self.is_downloading = False
        self.download_thread = None
        self.ydl = None
        
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
        url_group = QGroupBox("Video/Playlist URL")
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
        self.download_btn = QPushButton("Download")
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
        
    def update_download_button_state(self, is_downloading):
        if is_downloading:
            self.download_btn.setText("Cancel")
            self.download_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff4444;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
                QPushButton:pressed {
                    background-color: #cc0000;
                }
            """)
        else:
            self.download_btn.setText("Download")
            self.download_btn.setStyleSheet("")  # Reset to default style
        
    def paste_playlist_url(self):
        clipboard = QApplication.clipboard()
        self.url_entry.setText(clipboard.text())
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Location")
        if folder:
            self.path_entry.setText(folder)
            
    def sanitize_filename(self, name):
        return re.sub(r'[^a-zA-Z0-9-_ ]', '_', name)

    def check_url_type(self, url):
        """
        Check if the URL is for a single video or a playlist
        Returns: tuple of (url_type, info)
        """
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' in info:  # It's a playlist
                    return 'playlist', info
                else:  # It's a single video
                    return 'video', info
        except Exception as e:
            return 'error', str(e)
        
    def start_download_thread(self):
        if self.is_downloading:
            # Stop the download
            self.is_downloading = False
            if self.ydl:
                try:
                    # Safely terminate the download
                    self.ydl._finish_sequence = True
                    self.ydl._cancel_download = True
                    if self.download_thread and self.download_thread.is_alive():
                        self.download_thread.join(timeout=1)
                except:
                    pass
            self.status_signal.emit("Download cancelled.")
            self.reset_ui()
            return
            
        # Start new download
        self.is_downloading = True
        self.update_download_button_state(True)
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        
        self.download_thread = threading.Thread(target=self.download_playlist)
        self.download_thread.daemon = True
        self.download_thread.start()

    def reset_ui(self):
        """Reset UI to initial state"""
        self.is_downloading = False
        self.update_download_button_state(False)
        self.progress_bar.hide()
        self.video_info_widget.hide()
        self.status_label.clear()
        self.download_btn.setEnabled(True)
        self.url_entry.setEnabled(True)
        self.path_entry.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.paste_btn.setEnabled(True)
        self.ydl = None

    def download_single_video(self, video_url, save_path, index=1, total=1):
        """
        Helper function to download a single video
        """
        try:
            if not self.is_downloading:
                raise Exception("Download cancelled")
                
            # Get video info
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                video_info = ydl.extract_info(video_url, download=False)
                
            video_title = self.sanitize_filename(video_info.get('title', f'video_{index}'))
            self.status_signal.emit(f"Downloading video {index}/{total}: {video_title}")
            self.video_info_signal.emit(video_info)
            
            # Download options
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
                'outtmpl': os.path.join(save_path, f'{video_title}.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
            }
            
            # Download the video
            if self.is_downloading:
                self.ydl = yt_dlp.YoutubeDL(ydl_opts)
                self.ydl.download([video_url])
                
        except Exception as e:
            if str(e) == "Download cancelled":
                raise
            self.status_signal.emit(f"Failed to download video {index}: {str(e)}")
            raise
        
    def download_playlist(self):
        try:
            # Disable UI elements during download
            self.url_entry.setEnabled(False)
            self.path_entry.setEnabled(False)
            self.browse_btn.setEnabled(False)
            self.paste_btn.setEnabled(False)
            
            url = self.url_entry.text().strip()
            save_path = self.path_entry.text().strip()
            
            if not url:
                self.status_signal.emit("Please enter a URL.")
                self.reset_ui()
                return
                
            if not save_path:
                save_path = os.getcwd()
                
            self.status_signal.emit("Checking URL type...")
            
            # Check URL type
            url_type, info = self.check_url_type(url)
            
            if url_type == 'error':
                self.status_signal.emit(f"Error: {info}")
                self.reset_ui()
                return
            
            try:
                if url_type == 'playlist':
                    # Download playlist
                    playlist_title = self.sanitize_filename(info.get('title', 'Playlist'))
                    download_path = os.path.join(save_path, playlist_title)
                    os.makedirs(download_path, exist_ok=True)
                    
                    video_entries = info['entries']
                    self.video_count = len(video_entries)
                    self.status_signal.emit(f"Found {self.video_count} videos in playlist. Starting download...")
                    
                    for index, entry in enumerate(video_entries, start=1):
                        if not self.is_downloading:
                            raise Exception("Download cancelled")
                            
                        self.current_video_index = index
                        video_id = entry.get('id')
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        self.download_single_video(video_url, download_path, index, self.video_count)
                        
                else:  # video
                    # Download single video
                    self.video_count = 1
                    self.current_video_index = 1
                    self.status_signal.emit("Downloading single video...")
                    self.download_single_video(url, save_path, 1, 1)
                    
                if self.is_downloading:
                    self.status_signal.emit("Download completed successfully!")
                    
            except Exception as e:
                if str(e) == "Download cancelled":
                    self.status_signal.emit("Download cancelled.")
                else:
                    self.status_signal.emit(f"Error during download: {str(e)}")
            
        finally:
            self.reset_ui()
        
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