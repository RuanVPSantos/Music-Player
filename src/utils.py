"""Utility functions for the player application."""

import glob
import json
import shutil
import subprocess
from pathlib import Path

from src.config import PLAYLIST_JSON_PATH, SONGS_DIR, THUMBS_DIR


class FileUtils:
    """Utility functions for file operations."""
    
    @staticmethod
    def cleanup_temp_files() -> None:
        """Remove temporary files on startup."""
        if not SONGS_DIR.exists():
            return
        
        temp_files = []
        for pattern in ["*.webm", "*.m4a", "*.part", "*.temp", "*.ytdl", "*.opus", "*.wav"]:
            temp_files.extend(glob.glob(str(SONGS_DIR / pattern)))
        
        for temp_file in temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass

    @staticmethod
    def migrate_playlist_json(repo) -> None:
        """Migrate playlist.json to database if it exists."""
        if not PLAYLIST_JSON_PATH.exists():
            return
        
        try:
            data = json.loads(PLAYLIST_JSON_PATH.read_text(encoding="utf-8"))
            playlists = data.get("playlists", [])
            
            for item in playlists:
                name = item.get("name", "Playlist").strip()
                url = item.get("url", "").strip()
                if url:
                    try:
                        repo.create_sync_playlist(name, url)
                    except:
                        pass
            
            PLAYLIST_JSON_PATH.rename(PLAYLIST_JSON_PATH.with_suffix(".json.bak"))
        except:
            pass

    @staticmethod
    def show_thumbnail(thumbnail_path: str) -> str:
        """Show thumbnail in external viewer."""
        if not thumbnail_path or thumbnail_path.startswith("http"):
            return "Thumbnail não disponível localmente."
        
        thumb_path = THUMBS_DIR / thumbnail_path
        if not thumb_path.exists():
            return "Thumbnail não encontrada."
        
        viewers = ["feh", "eog", "gwenview", "xviewer", "display", "xdg-open"]
        for viewer in viewers:
            viewer_path = shutil.which(viewer)
            if viewer_path:
                try:
                    subprocess.Popen(
                        [viewer_path, str(thumb_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return f"Thumbnail aberta com {viewer}"
                except:
                    continue
        
        return "Nenhum visualizador encontrado (feh, eog, gwenview, etc.)"
