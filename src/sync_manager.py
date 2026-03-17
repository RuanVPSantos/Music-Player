"""Sync manager for handling playlist synchronization."""

import json
import queue
import shutil
import subprocess
import threading

from src.config import DB_PATH, SONGS_DIR
from src.download_manager import DownloadManager
from src.repository import Repository


class SyncManager:
    """Manages synchronization of playlists from external sources."""
    
    def __init__(self, status_queue: queue.Queue, download_manager: DownloadManager) -> None:
        self.status_queue = status_queue
        self.download_manager = download_manager

    def sync_playlists_async(self) -> None:
        """Start playlist synchronization in background thread."""
        def sync_worker():
            repo = Repository(DB_PATH)
            
            ytdlp = shutil.which("yt-dlp")
            if not ytdlp:
                self.status_queue.put(("error_general", "yt-dlp não encontrado."))
                return

            sync_playlists = repo.list_sync_playlists()
            if not sync_playlists:
                self.status_queue.put(("error_general", "Nenhuma playlist de sync configurada."))
                return

            SONGS_DIR.mkdir(parents=True, exist_ok=True)
            
            self.status_queue.put(("loading", "Criando índice de URLs existentes..."))
            existing_urls = set()
            for row in repo.conn.execute("SELECT url FROM musics").fetchall():
                existing_urls.add(row[0])
            
            for sync_pl in sync_playlists:
                url = sync_pl.url.strip()
                if not url:
                    continue

                self.status_queue.put(("loading", "Carregando informações da playlist..."))
                
                meta_cmd = [ytdlp, "--flat-playlist", "--dump-single-json", url]
                meta_res = subprocess.run(meta_cmd, capture_output=True, text=True, check=False)
                if meta_res.returncode != 0:
                    self.status_queue.put(("error_general", f"Falha ao ler playlist: {url}"))
                    continue

                try:
                    payload = json.loads(meta_res.stdout or "{}")
                except json.JSONDecodeError:
                    self.status_queue.put(("error_general", f"Falha no JSON da playlist: {url}"))
                    continue

                entries = payload.get("entries", [])
                total_videos = len(entries)
                
                if total_videos == 0:
                    self.status_queue.put(("error_general", "Playlist vazia."))
                    continue
                
                for idx, entry in enumerate(entries, 1):
                    video_id = entry.get("id")
                    if not video_id:
                        continue

                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    video_title = entry.get("title", video_id)[:40]
                    
                    if video_url in existing_urls:
                        self.status_queue.put(("skip", idx, total_videos, video_title))
                        continue
                    
                    detail_cmd = [ytdlp, "--skip-download", "--dump-single-json", video_url]
                    detail_res = subprocess.run(detail_cmd, capture_output=True, text=True, check=False)
                    if detail_res.returncode != 0:
                        continue

                    try:
                        detail = json.loads(detail_res.stdout or "{}")
                    except json.JSONDecodeError:
                        continue

                    try:
                        self.download_manager.download_executor.submit(
                            self.download_manager.download_and_convert,
                            video_id, video_url, video_title, detail, total_videos, idx
                        )
                    except RuntimeError:
                        break
            
            self.status_queue.put(("sync_complete", "Sincronização iniciada! Downloads em andamento..."))
        
        threading.Thread(target=sync_worker, daemon=True).start()
