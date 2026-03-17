"""Database repository for managing musics, playlists, tags, and sync configurations."""

import sqlite3
import uuid
from pathlib import Path
from typing import Optional

from src.models import Music, Playlist, Tag, SyncPlaylist


class Repository:
    """Handles all database operations for the player application."""
    
    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS musics (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                duration INTEGER NOT NULL DEFAULT 0,
                thumbnail TEXT NOT NULL DEFAULT '',
                file_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS playlist_music (
                playlist_id TEXT NOT NULL,
                music_id TEXT NOT NULL,
                PRIMARY KEY (playlist_id, music_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (music_id) REFERENCES musics(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS music_tags (
                music_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (music_id, tag_id),
                FOREIGN KEY (music_id) REFERENCES musics(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playlist_tags (
                playlist_id TEXT NOT NULL,
                tag_id TEXT NOT NULL,
                PRIMARY KEY (playlist_id, tag_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sync_playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                synced_at TIMESTAMP NULL
            );

            CREATE TABLE IF NOT EXISTS sync_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled BOOLEAN DEFAULT 0,
                backend_url TEXT,
                api_key TEXT,
                last_sync TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sync_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                entity_id TEXT,
                action TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced BOOLEAN DEFAULT 0
            );
            """
        )
        self.conn.commit()

    def list_musics(self) -> list[Music]:
        """List all musics ordered by title."""
        rows = self.conn.execute(
            "SELECT id, title, url, duration, thumbnail, file_path FROM musics ORDER BY title COLLATE NOCASE"
        ).fetchall()
        return [Music(**dict(r)) for r in rows]

    def list_playlists(self) -> list[Playlist]:
        """List all playlists ordered by name."""
        rows = self.conn.execute("SELECT id, name FROM playlists ORDER BY name COLLATE NOCASE").fetchall()
        return [Playlist(**dict(r)) for r in rows]

    def list_tags(self) -> list[Tag]:
        """List all tags ordered by name."""
        rows = self.conn.execute("SELECT id, name FROM tags ORDER BY name COLLATE NOCASE").fetchall()
        return [Tag(**dict(r)) for r in rows]

    def list_sync_playlists(self) -> list[SyncPlaylist]:
        """List all sync playlists ordered by name."""
        rows = self.conn.execute("SELECT id, name, url FROM sync_playlists ORDER BY name COLLATE NOCASE").fetchall()
        return [SyncPlaylist(**dict(r)) for r in rows]

    def create_sync_playlist(self, name: str, url: str) -> str:
        """Create a new sync playlist."""
        sync_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO sync_playlists (id, name, url) VALUES (?, ?, ?)",
            (sync_id, name, url)
        )
        self.conn.commit()
        return sync_id

    def delete_sync_playlist(self, sync_id: str) -> None:
        """Delete a sync playlist."""
        self.conn.execute("DELETE FROM sync_playlists WHERE id = ?", (sync_id,))
        self.conn.commit()

    def update_sync_playlist(self, sync_id: str, name: str, url: str) -> None:
        """Update a sync playlist."""
        self.conn.execute(
            "UPDATE sync_playlists SET name = ?, url = ? WHERE id = ?",
            (name, url, sync_id)
        )
        self.conn.commit()

    def create_playlist(self, name: str) -> None:
        """Create a new playlist."""
        self.conn.execute("INSERT INTO playlists (id, name) VALUES (?, ?)", (str(uuid.uuid4()), name.strip()))
        self.conn.commit()

    def delete_playlist(self, playlist_id: str) -> None:
        """Delete a playlist."""
        self.conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.conn.commit()

    def create_tag(self, name: str) -> None:
        """Create a new tag."""
        self.conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (str(uuid.uuid4()), name.strip()))
        self.conn.commit()

    def delete_tag(self, tag_id: str) -> None:
        """Delete a tag."""
        self.conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self.conn.commit()

    def add_music_to_playlist(self, playlist_id: str, music_id: str) -> None:
        """Add a music to a playlist."""
        self.conn.execute(
            "INSERT OR IGNORE INTO playlist_music (playlist_id, music_id) VALUES (?, ?)",
            (playlist_id, music_id),
        )
        self.conn.commit()

    def remove_music_from_playlist(self, playlist_id: str, music_id: str) -> None:
        """Remove a music from a playlist."""
        self.conn.execute("DELETE FROM playlist_music WHERE playlist_id = ? AND music_id = ?", (playlist_id, music_id))
        self.conn.commit()

    def add_tag_to_music(self, music_id: str, tag_id: str) -> None:
        """Add a tag to a music."""
        self.conn.execute("INSERT OR IGNORE INTO music_tags (music_id, tag_id) VALUES (?, ?)", (music_id, tag_id))
        self.conn.commit()

    def remove_tag_from_music(self, music_id: str, tag_id: str) -> None:
        """Remove a tag from a music."""
        self.conn.execute("DELETE FROM music_tags WHERE music_id = ? AND tag_id = ?", (music_id, tag_id))
        self.conn.commit()

    def add_tag_to_playlist(self, playlist_id: str, tag_id: str) -> None:
        """Add a tag to a playlist."""
        self.conn.execute(
            "INSERT OR IGNORE INTO playlist_tags (playlist_id, tag_id) VALUES (?, ?)",
            (playlist_id, tag_id),
        )
        self.conn.commit()

    def remove_tag_from_playlist(self, playlist_id: str, tag_id: str) -> None:
        """Remove a tag from a playlist."""
        self.conn.execute("DELETE FROM playlist_tags WHERE playlist_id = ? AND tag_id = ?", (playlist_id, tag_id))
        self.conn.commit()

    def tags_for_music(self, music_id: str) -> list[str]:
        """Get all tag names for a music."""
        rows = self.conn.execute(
            """
            SELECT t.name
            FROM tags t
            INNER JOIN music_tags mt ON t.id = mt.tag_id
            WHERE mt.music_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (music_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    def tags_for_playlist(self, playlist_id: str) -> list[str]:
        """Get all tag names for a playlist."""
        rows = self.conn.execute(
            """
            SELECT t.name
            FROM tags t
            INNER JOIN playlist_tags pt ON t.id = pt.tag_id
            WHERE pt.playlist_id = ?
            ORDER BY t.name COLLATE NOCASE
            """,
            (playlist_id,),
        ).fetchall()
        return [r["name"] for r in rows]

    def get_playlist_music_ids(self, playlist_id: str) -> set[str]:
        """Get all music IDs in a playlist."""
        rows = self.conn.execute("SELECT music_id FROM playlist_music WHERE playlist_id = ?", (playlist_id,)).fetchall()
        return {r["music_id"] for r in rows}

    def find_musics_by_tag(self, tag_name: str) -> list[Music]:
        """Find all musics with a specific tag."""
        rows = self.conn.execute(
            """
            SELECT m.id, m.title, m.url, m.duration, m.thumbnail, m.file_path
            FROM musics m
            INNER JOIN music_tags mt ON m.id = mt.music_id
            INNER JOIN tags t ON t.id = mt.tag_id
            WHERE LOWER(t.name) = LOWER(?)
            ORDER BY m.title COLLATE NOCASE
            """,
            (tag_name.strip(),),
        ).fetchall()
        return [Music(**dict(r)) for r in rows]

    def find_playlists_by_tag(self, tag_name: str) -> list[Playlist]:
        """Find all playlists with a specific tag."""
        rows = self.conn.execute(
            """
            SELECT p.id, p.name
            FROM playlists p
            INNER JOIN playlist_tags pt ON p.id = pt.playlist_id
            INNER JOIN tags t ON t.id = pt.tag_id
            WHERE LOWER(t.name) = LOWER(?)
            ORDER BY p.name COLLATE NOCASE
            """,
            (tag_name.strip(),),
        ).fetchall()
        return [Playlist(**dict(r)) for r in rows]

    def find_tags_by_name(self, query: str) -> list[Tag]:
        """Find tags by name pattern."""
        rows = self.conn.execute(
            "SELECT id, name FROM tags WHERE LOWER(name) LIKE LOWER(?) ORDER BY name COLLATE NOCASE",
            (f"%{query.strip()}%",),
        ).fetchall()
        return [Tag(**dict(r)) for r in rows]

    def upsert_music(self, music: Music) -> None:
        """Insert or update a music."""
        self.conn.execute(
            """
            INSERT INTO musics (id, title, url, duration, thumbnail, file_path)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                duration = excluded.duration,
                thumbnail = excluded.thumbnail,
                file_path = excluded.file_path
            """,
            (music.id, music.title, music.url, music.duration, music.thumbnail, music.file_path),
        )
        self.conn.commit()
