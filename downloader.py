import os
import yt_dlp
import sys

def download_playlist():
    playlist_url = input("Enter the YouTube playlist URL: ").strip()

    try:
        ydl_opts = {
            'quiet': True, 
            'extract_flat': True,
            'dump_single_json': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            playlist_info = ydl.extract_info(playlist_url, download=False)
    except Exception as e:
        print(f"Error fetching playlist details: {e}")
        return

    if 'entries' not in playlist_info or not playlist_info['entries']:
        print("The playlist is empty or invalid.")
        return

    video_urls = [entry['url'] for entry in playlist_info['entries']]
    print(f"The playlist contains {len(video_urls)} videos.")

    proceed = input("Do you want to download them? (yes/no): ").strip().lower()
    if proceed != "yes":
        print("Download canceled.")
        return

    save_path = input("Enter the folder path to save the videos: ").strip()
    if not save_path:
        print("No path provided. Using the current directory.")
        save_path = os.getcwd()

    if not os.path.exists(save_path):
        try:
            os.makedirs(save_path)
        except Exception as e:
            print(f"Error creating directory: {e}")
            return

    print(f"Starting download of playlist: {playlist_info.get('title', 'Unknown Playlist')}")

    ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
    'quiet': True,
    'progress_hooks': [
        lambda d: sys.stdout.write(f"\rDownloading: {d['filename']} - {d['_percent_str']} completed") if d['status'] == 'downloading' else None
    ]
    }


    for index, url in enumerate(video_urls, start=1):
        try:
            print(f"\nDownloading video {index}/{len(video_urls)}: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Failed to download video {index}: {e}")

    print("\nAll videos have been downloaded successfully!")

if __name__ == "__main__":
    download_playlist()
