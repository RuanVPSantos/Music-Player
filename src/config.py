"""Configuration constants and paths for the player application."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "player.db"
SONGS_DIR = BASE_DIR / "songs"
THUMBS_DIR = BASE_DIR / "thumbnails"
PLAYLIST_JSON_PATH = BASE_DIR / "playlist.json"
