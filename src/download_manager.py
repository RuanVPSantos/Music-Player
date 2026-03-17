"""Download manager for handling music downloads and conversions."""

import glob
import json
import queue
import shutil
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.config import DB_PATH, SONGS_DIR, THUMBS_DIR
from src.models import Music
from src.repository import Repository


class DownloadManager:
    """Manages music downloads and conversions using yt-dlp."""
    
    def __init__(self, status_queue: queue.Queue) -> None:
        self.status_queue = status_queue
        self.download_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="download")
        self.convert_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="convert")
        self.active = False

    def download_and_convert(self, video_id: str, video_url: str, video_title: str, detail: dict, total: int, current: int) -> None:
        """Download and convert a video to MP3."""
        try:
            repo = Repository(DB_PATH)
            
            music_id = str(uuid.uuid4())
            filename = f"{music_id}.mp3"
            temp_file = SONGS_DIR / f"{music_id}.temp"
            out_template = str(SONGS_DIR / f"{music_id}.%(ext)s")
            
            THUMBS_DIR.mkdir(parents=True, exist_ok=True)
            
            self.status_queue.put(("download_start", current, total, video_title))
            
            thumbnail_url = detail.get("thumbnail", "")
            thumbnail_path = ""
            if thumbnail_url:
                try:
                    import requests
                    thumb_filename = f"{music_id}.jpg"
                    thumb_path = THUMBS_DIR / thumb_filename
                    response = requests.get(thumbnail_url, timeout=10)
                    if response.ok:
                        thumb_path.write_bytes(response.content)
                        thumbnail_path = thumb_filename
                except:
                    pass
            
            ytdlp = shutil.which("yt-dlp")
            dl_cmd = [
                ytdlp, "-x", "--audio-format", "mp3",
                "--newline",
                "--progress-template", "download:%(progress._percent_str)s",
                "--progress-template", "postprocess:Convertendo para MP3...",
                "-o", out_template,
                video_url
            ]
            
            process = subprocess.Popen(
                dl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                line = line.strip()
                if "Convertendo" in line or "postprocess" in line.lower():
                    self.status_queue.put(("converting", current, total, video_title))
                elif "%" in line:
                    try:
                        dl_percent = line.split()[0].replace("%", "")
                        self.status_queue.put(("progress", current, total, video_title, dl_percent))
                    except:
                        pass
            
            process.wait()
            if process.returncode != 0:
                self.status_queue.put(("error", current, total, video_title))
                return
            
            final_path = SONGS_DIR / filename
            if not final_path.exists():
                self.status_queue.put(("error", current, total, video_title))
                return
            
            for temp in glob.glob(str(SONGS_DIR / f"{music_id}.*")):
                if not temp.endswith(".mp3"):
                    try:
                        Path(temp).unlink()
                    except:
                        pass
            
            duration = int(detail.get("duration") or 0)
            music = Music(
                id=music_id,
                title=detail.get("title", video_id),
                url=detail.get("webpage_url", video_url),
                duration=duration,
                thumbnail=thumbnail_path or detail.get("thumbnail") or "",
                file_path=filename,
            )
            
            repo.upsert_music(music)
            
            if duration > 2400:
                playlist_tag = None
                for tag in repo.list_tags():
                    if tag.name.lower() == "playlist":
                        playlist_tag = tag
                        break
                
                if not playlist_tag:
                    repo.create_tag("playlist")
                    for tag in repo.list_tags():
                        if tag.name.lower() == "playlist":
                            playlist_tag = tag
                            break
                
                if playlist_tag:
                    repo.add_tag_to_music(music_id, playlist_tag.id)
            
            self.status_queue.put(("complete", current, total, video_title))
        except Exception as e:
            self.status_queue.put(("error", current, total, video_title, str(e)))

    def shutdown(self) -> None:
        """Shutdown executor threads."""
        self.download_executor.shutdown(wait=False)
        self.convert_executor.shutdown(wait=False)
