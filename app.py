#!/usr/bin/env python3
"""Player terminal com TUI, playlists, tags e sincronização com yt-dlp."""

from __future__ import annotations

import curses
import glob
import json
import os
import queue
import shutil
import signal
import sqlite3
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "player.db"
SONGS_DIR = BASE_DIR / "songs"
THUMBS_DIR = BASE_DIR / "thumbnails"
PLAYLIST_JSON_PATH = BASE_DIR / "playlist.json"


@dataclass
class Music:
    id: str
    title: str
    url: str
    duration: int
    thumbnail: str
    file_path: str


@dataclass
class Playlist:
    id: str
    name: str


@dataclass
class Tag:
    id: str
    name: str


@dataclass
class SyncPlaylist:
    id: str
    name: str
    url: str


class Repo:
    def __init__(self, db_path: Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
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
        rows = self.conn.execute(
            "SELECT id, title, url, duration, thumbnail, file_path FROM musics ORDER BY title COLLATE NOCASE"
        ).fetchall()
        return [Music(**dict(r)) for r in rows]

    def list_playlists(self) -> list[Playlist]:
        rows = self.conn.execute("SELECT id, name FROM playlists ORDER BY name COLLATE NOCASE").fetchall()
        return [Playlist(**dict(r)) for r in rows]

    def list_tags(self) -> list[Tag]:
        rows = self.conn.execute("SELECT id, name FROM tags ORDER BY name COLLATE NOCASE").fetchall()
        return [Tag(**dict(r)) for r in rows]

    def list_sync_playlists(self) -> list[SyncPlaylist]:
        rows = self.conn.execute("SELECT id, name, url FROM sync_playlists ORDER BY name COLLATE NOCASE").fetchall()
        return [SyncPlaylist(**dict(r)) for r in rows]

    def create_sync_playlist(self, name: str, url: str) -> str:
        sync_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO sync_playlists (id, name, url) VALUES (?, ?, ?)",
            (sync_id, name, url)
        )
        self.conn.commit()
        return sync_id

    def delete_sync_playlist(self, sync_id: str) -> None:
        self.conn.execute("DELETE FROM sync_playlists WHERE id = ?", (sync_id,))
        self.conn.commit()

    def update_sync_playlist(self, sync_id: str, name: str, url: str) -> None:
        self.conn.execute(
            "UPDATE sync_playlists SET name = ?, url = ? WHERE id = ?",
            (name, url, sync_id)
        )
        self.conn.commit()

    def create_playlist(self, name: str) -> None:
        self.conn.execute("INSERT INTO playlists (id, name) VALUES (?, ?)", (str(uuid.uuid4()), name.strip()))
        self.conn.commit()

    def delete_playlist(self, playlist_id: str) -> None:
        self.conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.conn.commit()

    def create_tag(self, name: str) -> None:
        self.conn.execute("INSERT INTO tags (id, name) VALUES (?, ?)", (str(uuid.uuid4()), name.strip()))
        self.conn.commit()

    def delete_tag(self, tag_id: str) -> None:
        self.conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self.conn.commit()

    def add_music_to_playlist(self, playlist_id: str, music_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO playlist_music (playlist_id, music_id) VALUES (?, ?)",
            (playlist_id, music_id),
        )
        self.conn.commit()

    def remove_music_from_playlist(self, playlist_id: str, music_id: str) -> None:
        self.conn.execute("DELETE FROM playlist_music WHERE playlist_id = ? AND music_id = ?", (playlist_id, music_id))
        self.conn.commit()

    def add_tag_to_music(self, music_id: str, tag_id: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO music_tags (music_id, tag_id) VALUES (?, ?)", (music_id, tag_id))
        self.conn.commit()

    def remove_tag_from_music(self, music_id: str, tag_id: str) -> None:
        self.conn.execute("DELETE FROM music_tags WHERE music_id = ? AND tag_id = ?", (music_id, tag_id))
        self.conn.commit()

    def add_tag_to_playlist(self, playlist_id: str, tag_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO playlist_tags (playlist_id, tag_id) VALUES (?, ?)",
            (playlist_id, tag_id),
        )
        self.conn.commit()

    def remove_tag_from_playlist(self, playlist_id: str, tag_id: str) -> None:
        self.conn.execute("DELETE FROM playlist_tags WHERE playlist_id = ? AND tag_id = ?", (playlist_id, tag_id))
        self.conn.commit()

    def tags_for_music(self, music_id: str) -> list[str]:
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
        rows = self.conn.execute("SELECT music_id FROM playlist_music WHERE playlist_id = ?", (playlist_id,)).fetchall()
        return {r["music_id"] for r in rows}

    def find_musics_by_tag(self, tag_name: str) -> list[Music]:
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
        rows = self.conn.execute(
            "SELECT id, name FROM tags WHERE LOWER(name) LIKE LOWER(?) ORDER BY name COLLATE NOCASE",
            (f"%{query.strip()}%",),
        ).fetchall()
        return [Tag(**dict(r)) for r in rows]

    def upsert_music(self, music: Music) -> None:
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


class AudioPlayer:
    def __init__(self) -> None:
        self.current_music: Optional[Music] = None
        self.process: Optional[subprocess.Popen[str]] = None
        self.started_at: float = 0.0
        self.accumulated: float = 0.0
        self.paused = False
        self.volume: int = 100
        self.current_position: float = 0.0

    def is_playing(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def play(self, music: Music, start_position: float = 0.0) -> None:
        self.stop()
        ffplay_path = shutil.which("ffplay")
        if not ffplay_path:
            raise RuntimeError("ffplay não encontrado. Instale ffmpeg para reproduzir músicas.")
        
        full_path = SONGS_DIR / music.file_path
        if not full_path.exists():
            raise RuntimeError(f"Arquivo não encontrado: {full_path}")

        cmd = [ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(self.volume)]
        if start_position > 0:
            cmd.extend(["-ss", str(start_position)])
        cmd.append(str(full_path))
        
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.current_music = music
        self.started_at = time.time()
        self.accumulated = start_position
        self.current_position = start_position
        self.paused = False

    def pause(self) -> None:
        if not self.is_playing() or not self.process or self.paused:
            return
        self.accumulated += time.time() - self.started_at
        self.current_position = self.accumulated
        os.kill(self.process.pid, signal.SIGSTOP)
        self.paused = True

    def resume(self) -> None:
        if not self.is_playing() or not self.process or not self.paused:
            return
        os.kill(self.process.pid, signal.SIGCONT)
        self.started_at = time.time()
        self.paused = False

    def set_volume(self, new_volume: int) -> None:
        self.volume = max(0, min(200, new_volume))
        if not self.current_music:
            return
        if self.is_playing() and self.process:
            self.accumulated += time.time() - self.started_at
            self.current_position = self.accumulated
            try:
                self.process.terminate()
                self.process.wait(timeout=1.0)
            except:
                pass
            ffplay_path = shutil.which("ffplay")
            if ffplay_path:
                full_path = SONGS_DIR / self.current_music.file_path
                cmd = [ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(self.volume)]
                if self.current_position > 0:
                    cmd.extend(["-ss", str(self.current_position)])
                cmd.append(str(full_path))
                self.process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                )
                self.started_at = time.time()

    def volume_up(self) -> None:
        self.set_volume(self.volume + 10)

    def volume_down(self) -> None:
        self.set_volume(self.volume - 10)

    def seek_forward(self) -> None:
        if not self.current_music:
            return
        new_pos = min(self.current_position + 5, self.current_music.duration)
        self.current_position = new_pos
        self.accumulated = new_pos
        if self.is_playing():
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        ffplay_path = shutil.which("ffplay")
        if ffplay_path:
            full_path = SONGS_DIR / self.current_music.file_path
            cmd = [ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(self.volume), "-ss", str(new_pos)]
            cmd.append(str(full_path))
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self.started_at = time.time()

    def seek_backward(self) -> None:
        if not self.current_music:
            return
        new_pos = max(self.current_position - 5, 0)
        self.current_position = new_pos
        self.accumulated = new_pos
        if self.is_playing():
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        ffplay_path = shutil.which("ffplay")
        if ffplay_path:
            full_path = SONGS_DIR / self.current_music.file_path
            cmd = [ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(self.volume), "-ss", str(new_pos)]
            cmd.append(str(full_path))
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self.started_at = time.time()

    def pause_or_resume(self) -> None:
        if self.paused:
            self.resume()
        else:
            self.pause()

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.current_music = None
        self.started_at = 0.0
        self.accumulated = 0.0
        self.paused = False

    def elapsed_seconds(self) -> int:
        if not self.current_music:
            return 0
        if self.paused:
            return int(self.accumulated)
        if not self.is_playing():
            return int(self.current_music.duration)
        return int(self.accumulated + max(0.0, time.time() - self.started_at))

    def format_position(self) -> str:
        sec = int(self.current_position)
        m, s = divmod(max(0, sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


class DownloadManager:
    def __init__(self, status_queue: queue.Queue) -> None:
        self.status_queue = status_queue
        self.download_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="download")
        self.convert_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="convert")
        self.active = False

    def download_and_convert(self, video_id: str, video_url: str, video_title: str, detail: dict, total: int, current: int) -> None:
        """Download em uma thread, conversão em outra."""
        try:
            repo = Repo(DB_PATH)
            
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
        self.download_executor.shutdown(wait=False)
        self.convert_executor.shutdown(wait=False)


class App:
    MENU = ["Músicas", "Playlists", "Tags", "Busca", "Sync URLs", "Sincronizar", "Sair"]

    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.repo = Repo(DB_PATH)
        self.player = AudioPlayer()
        self.section = 0
        self.selection = 0
        self.scroll_offset = 0
        self.status = "Pronto."
        self.search_cache: list[str] = []
        self.selected_tags: set[str] = set()
        self.tag_multiselect_mode = False
        self.fuzzy_search_mode = False
        self.fuzzy_query = ""
        self.autoplay = True
        self.shuffle = False
        self.playlist_order: list[str] = []
        self.current_playlist_index = 0
        self.status_queue: queue.Queue = queue.Queue()
        self.download_manager = DownloadManager(self.status_queue)
        self.sync_playlists: list[SyncPlaylist] = []
        self.thumbnail_mode = False
        self.refresh_lists()
        self.running = True
        self._init_colors()
        self.cleanup_temp_files()
        self.migrate_playlist_json()
        self.auto_sync()

    def _init_colors(self) -> None:
        curses.start_color()
        curses.use_default_colors()
        
        curses.init_color(curses.COLOR_BLACK, 26, 27, 38)
        curses.init_color(curses.COLOR_RED, 973, 549, 655)
        curses.init_color(curses.COLOR_GREEN, 611, 866, 741)
        curses.init_color(curses.COLOR_YELLOW, 901, 796, 549)
        curses.init_color(curses.COLOR_BLUE, 486, 655, 973)
        curses.init_color(curses.COLOR_MAGENTA, 733, 549, 973)
        curses.init_color(curses.COLOR_CYAN, 486, 866, 937)
        curses.init_color(curses.COLOR_WHITE, 787, 819, 902)
        
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_MAGENTA, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_RED, -1)
        curses.init_pair(6, curses.COLOR_BLUE, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_MAGENTA)

    def refresh_lists(self) -> None:
        if self.selected_tags:
            all_musics = set()
            for tag_name in self.selected_tags:
                all_musics.update(m.id for m in self.repo.find_musics_by_tag(tag_name))
            self.musics = [m for m in self.repo.list_musics() if m.id in all_musics]
        else:
            self.musics = self.repo.list_musics()
        self.playlists = self.repo.list_playlists()
        self.tags = self.repo.list_tags()
        self.sync_playlists = self.repo.list_sync_playlists()
        self.selection = min(self.selection, max(0, self.current_length() - 1))
        self.scroll_offset = 0
        self.update_playlist_order()

    def cleanup_temp_files(self) -> None:
        """Remove arquivos temporários no startup."""
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

    def migrate_playlist_json(self) -> None:
        """Migra playlist.json para o banco de dados se existir."""
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
                        self.repo.create_sync_playlist(name, url)
                    except sqlite3.IntegrityError:
                        pass
            
            PLAYLIST_JSON_PATH.rename(PLAYLIST_JSON_PATH.with_suffix(".json.bak"))
        except:
            pass

    def auto_sync(self) -> None:
        """Inicia sincronização automática no startup."""
        if self.repo.list_sync_playlists():
            self.sync_musics_async()

    def current_length(self) -> int:
        if self.fuzzy_search_mode:
            return len(self.get_fuzzy_filtered_musics())
        if self.section == 0:
            return len(self.musics)
        if self.section == 1:
            return len(self.playlists)
        if self.section == 2:
            return len(self.tags)
        if self.section == 3:
            return len(self.search_cache)
        if self.section == 4:
            return len(self.sync_playlists)
        return 0

    def get_fuzzy_filtered_musics(self) -> list[Music]:
        """Filtra músicas usando busca fuzzy."""
        if not self.fuzzy_query:
            return self.musics
        
        query_lower = self.fuzzy_query.lower()
        filtered = []
        for music in self.musics:
            if query_lower in music.title.lower():
                filtered.append(music)
        return filtered

    def update_playlist_order(self) -> None:
        """Atualiza a ordem de reprodução das músicas."""
        if self.shuffle:
            import random
            self.playlist_order = [m.id for m in self.musics]
            random.shuffle(self.playlist_order)
        else:
            self.playlist_order = [m.id for m in self.musics]
        self.current_playlist_index = 0

    def get_next_music(self) -> Optional[Music]:
        """Retorna a próxima música da playlist."""
        if not self.playlist_order:
            return None
        
        if self.current_playlist_index >= len(self.playlist_order):
            if self.shuffle:
                import random
                random.shuffle(self.playlist_order)
            self.current_playlist_index = 0
        
        if self.current_playlist_index < len(self.playlist_order):
            music_id = self.playlist_order[self.current_playlist_index]
            self.current_playlist_index += 1
            for music in self.musics:
                if music.id == music_id:
                    return music
        return None

    def get_prev_music(self) -> Optional[Music]:
        """Retorna a música anterior da playlist."""
        if not self.playlist_order:
            return None
        
        self.current_playlist_index = max(0, self.current_playlist_index - 2)
        return self.get_next_music()

    def move_music_up(self) -> None:
        """Move a música selecionada para cima na lista."""
        if self.section != 0 or self.selection <= 0:
            return
        
        idx = self.selection
        self.musics[idx], self.musics[idx - 1] = self.musics[idx - 1], self.musics[idx]
        self.selection -= 1
        self.update_playlist_order()

    def move_music_down(self) -> None:
        """Move a música selecionada para baixo na lista."""
        if self.section != 0 or self.selection >= len(self.musics) - 1:
            return
        
        idx = self.selection
        self.musics[idx], self.musics[idx + 1] = self.musics[idx + 1], self.musics[idx]
        self.selection += 1
        self.update_playlist_order()

    def show_thumbnail(self) -> None:
        """Exibe a thumbnail da música atual em janela externa."""
        if not self.player.current_music:
            self.status = "Nenhuma música tocando."
            return
        
        thumb_filename = self.player.current_music.thumbnail
        if not thumb_filename or thumb_filename.startswith("http"):
            self.status = "Thumbnail não disponível localmente."
            return
        
        thumb_path = THUMBS_DIR / thumb_filename
        if not thumb_path.exists():
            self.status = "Thumbnail não encontrada."
            return
        
        # Tenta visualizadores gráficos
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
                    self.status = f"Thumbnail aberta com {viewer}"
                    return
                except:
                    continue
        
        self.status = "Nenhum visualizador encontrado (feh, eog, gwenview, etc.)"

    def prompt(self, text: str) -> str:
        h, w = self.stdscr.getmaxyx()
        self.stdscr.move(h - 1, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(h - 1, 0, text[: max(1, w - 1)])
        self.stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        self.stdscr.timeout(-1)  # Bloqueia até receber input
        try:
            value = self.stdscr.getstr(h - 1, min(len(text), w - 2), max(1, w - len(text) - 1)).decode("utf-8").strip()
        finally:
            curses.noecho()
            curses.curs_set(0)
            self.stdscr.timeout(50)  # Restaura timeout
        return value

    def format_duration(self, sec: int) -> str:
        m, s = divmod(max(0, sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def draw_progress(self, y: int) -> None:
        h, w = self.stdscr.getmaxyx()
        if not self.player.current_music:
            self.stdscr.addstr(y, 2, "♪ ", curses.color_pair(7))
            self.stdscr.addstr("Nenhuma música tocando", curses.color_pair(7) | curses.A_DIM)
            return

        music = self.player.current_music
        elapsed = min(self.player.elapsed_seconds(), max(1, music.duration))
        total = max(1, music.duration)
        ratio = min(1.0, elapsed / total)
        bar_w = min(50, max(20, w - 40))
        done = int(bar_w * ratio)
        
        if self.player.paused:
            icon = "⏸ "
            state_color = curses.color_pair(4)
        elif self.player.is_playing():
            icon = "▶ "
            state_color = curses.color_pair(3)
        else:
            icon = "⏹ "
            state_color = curses.color_pair(7)
        
        self.stdscr.addstr(y, 2, icon, state_color | curses.A_BOLD)
        
        title = music.title[:min(30, w - bar_w - 25)] if len(music.title) > 30 else music.title
        self.stdscr.addstr(title, curses.color_pair(1) | curses.A_BOLD)
        
        self.stdscr.addstr(y + 1, 2, "  ")
        bar = f"{'━' * done}{'─' * (bar_w - done)}"
        self.stdscr.addstr(bar, curses.color_pair(2))
        self.stdscr.addstr(f" {self.format_duration(elapsed)}", curses.color_pair(4))
        self.stdscr.addstr("/", curses.color_pair(7) | curses.A_DIM)
        self.stdscr.addstr(f"{self.format_duration(total)}", curses.color_pair(7))
        self.stdscr.addstr(f" Vol: {self.player.volume}%", curses.color_pair(6) | curses.A_DIM)

    def draw(self) -> None:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(0, 2, "╭" + "─" * (w - 4) + "╮", curses.color_pair(2))
        self.stdscr.addstr(1, 2, "│", curses.color_pair(2))
        self.stdscr.addstr(1, 4, "♫ PLAYER TUI", curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(1, w - 3, "│", curses.color_pair(2))
        self.stdscr.addstr(2, 2, "╰" + "─" * (w - 4) + "╯", curses.color_pair(2))
        
        menu_y = 3
        x_pos = 4
        for idx, name in enumerate(self.MENU):
            if idx == self.section:
                self.stdscr.addstr(menu_y, x_pos, f" {name} ", curses.color_pair(8) | curses.A_BOLD)
            else:
                self.stdscr.addstr(menu_y, x_pos, f" {name} ", curses.color_pair(7) | curses.A_DIM)
            x_pos += len(name) + 4
        
        self.stdscr.addstr(4, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)
        
        y = 6
        
        if self.fuzzy_search_mode:
            search_line = f"🔍 Busca: {self.fuzzy_query}_ (Esc: sair)"
            self.stdscr.addstr(5, 4, search_line[:w - 8], curses.color_pair(1) | curses.A_BOLD)
            y = 7
        elif self.selected_tags:
            filter_line = f"🏷  Filtros ativos: {', '.join(sorted(self.selected_tags))} (F: limpar)"
            self.stdscr.addstr(5, 4, filter_line[:w - 8], curses.color_pair(4) | curses.A_BOLD)
            y = 7
        
        items: list[str] = []
        if self.fuzzy_search_mode:
            for music in self.get_fuzzy_filtered_musics():
                tags = ",".join(self.repo.tags_for_music(music.id))
                items.append(f"{music.title} • {self.format_duration(music.duration)} • {tags or 'sem tags'}")
        elif self.section == 0:
            for music in self.musics:
                tags = ",".join(self.repo.tags_for_music(music.id))
                items.append(f"{music.title} • {self.format_duration(music.duration)} • {tags or 'sem tags'}")
        elif self.section == 1:
            for playlist in self.playlists:
                tags = ",".join(self.repo.tags_for_playlist(playlist.id))
                count = len(self.repo.get_playlist_music_ids(playlist.id))
                items.append(f"{playlist.name} • {count} músicas • {tags or 'sem tags'}")
        elif self.section == 2:
            if self.tag_multiselect_mode:
                for tag in self.tags:
                    marker = "[✓]" if tag.name in self.selected_tags else "[ ]"
                    items.append(f"{marker} {tag.name}")
            else:
                items = [t.name for t in self.tags]
        elif self.section == 3:
            items = self.search_cache or ["Nenhum resultado encontrado"]
        elif self.section == 4:
            for sync_pl in self.sync_playlists:
                items.append(f"{sync_pl.name} • {sync_pl.url[:50]}...")
            if not items:
                items = ["Nenhuma playlist de sync. Pressione C para criar."]
        elif self.section == 5:
            items = ["Pressione Enter ou S para sincronizar músicas"]
        elif self.section == 6:
            items = ["Pressione Enter para sair da aplicação"]
        
        max_items = h - 14
        
        if self.selection < self.scroll_offset:
            self.scroll_offset = self.selection
        elif self.selection >= self.scroll_offset + max_items:
            self.scroll_offset = self.selection - max_items + 1
        
        visible_items = items[self.scroll_offset:self.scroll_offset + max_items]
        
        for idx, item in enumerate(visible_items):
            actual_idx = idx + self.scroll_offset
            if actual_idx == self.selection:
                self.stdscr.addstr(y + idx, 4, "▶", curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y + idx, 6, item[:w - 8], curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y + idx, 4, "•", curses.color_pair(7) | curses.A_DIM)
                self.stdscr.addstr(y + idx, 6, item[:w - 8], curses.color_pair(7))
        
        if len(items) > max_items:
            scroll_info = f" [{self.selection + 1}/{len(items)}] "
            self.stdscr.addstr(y + max_items - 1, w - len(scroll_info) - 4, scroll_info, curses.color_pair(7) | curses.A_DIM)
        
        progress_y = h - 7
        self.stdscr.addstr(progress_y, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)
        self.draw_progress(progress_y + 1)
        
        help_y = h - 4
        self.stdscr.addstr(help_y, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)
        
        if self.fuzzy_search_mode:
            help_text = "Digite para buscar  Enter: tocar  Esc: sair da busca  Q: sair"
        elif self.section == 2:
            if self.tag_multiselect_mode:
                help_text = "↑↓: navegar  Space: marcar/desmarcar  F: aplicar filtro  Esc: cancelar  Q: sair"
            else:
                help_text = "↑↓: navegar  M: multiselect  C: criar  D: deletar  Q: sair"
        elif self.section == 4:
            help_text = "↑↓: navegar  C: criar  E: editar  D: deletar  Q: sair"
        else:
            help_text = "↑↓: navegar  []: reordenar  /: busca  V: thumb  A: auto  R: shuffle  S: sync  P/N/B: player  +/-: vol  <>.: seek  Q: sair"
        self.stdscr.addstr(help_y + 1, 4, help_text[:w - 8], curses.color_pair(6) | curses.A_DIM)
        
        status_line = self.status[:w - 40]
        flags = []
        if self.autoplay:
            flags.append("AUTO")
        if self.shuffle:
            flags.append("SHUFFLE")
        if flags:
            status_line += f" [{' | '.join(flags)}]"
        
        self.stdscr.addstr(h - 2, 4, "● ", curses.color_pair(3))
        self.stdscr.addstr(status_line[:w - 10], curses.color_pair(7))
        
        self.stdscr.refresh()

    def selected_music(self) -> Optional[Music]:
        if self.fuzzy_search_mode:
            filtered = self.get_fuzzy_filtered_musics()
            if 0 <= self.selection < len(filtered):
                return filtered[self.selection]
            return None
        if 0 <= self.selection < len(self.musics):
            return self.musics[self.selection]
        return None

    def selected_playlist(self) -> Optional[Playlist]:
        if 0 <= self.selection < len(self.playlists):
            return self.playlists[self.selection]
        return None

    def selected_tag(self) -> Optional[Tag]:
        if 0 <= self.selection < len(self.tags):
            return self.tags[self.selection]
        return None

    def selected_sync_playlist(self) -> Optional[SyncPlaylist]:
        if 0 <= self.selection < len(self.sync_playlists):
            return self.sync_playlists[self.selection]
        return None

    def sync_musics_async(self) -> None:
        """Inicia sincronização em background thread."""
        def sync_worker():
            repo = Repo(DB_PATH)
            
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
                        # Executor já foi encerrado
                        break
            
            self.status_queue.put(("sync_complete", "Sincronização iniciada! Downloads em andamento..."))
        
        threading.Thread(target=sync_worker, daemon=True).start()

    def process_status_queue(self) -> None:
        """Processa mensagens da fila de status de download."""
        try:
            while True:
                msg = self.status_queue.get_nowait()
                msg_type = msg[0]
                
                if msg_type == "progress":
                    _, current, total, title, percent = msg
                    self.status = f"[{current}/{total}] Baixando: {title}... {percent}%"
                elif msg_type == "converting":
                    _, current, total, title = msg
                    self.status = f"[{current}/{total}] Convertendo: {title}..."
                elif msg_type == "complete":
                    _, current, total, title = msg
                    self.status = f"[{current}/{total}] Concluído: {title}"
                    old_count = len(self.musics)
                    self.refresh_lists()
                    if len(self.musics) > old_count and self.fuzzy_search_mode:
                        pass
                elif msg_type == "error":
                    _, current, total, title = msg[:4]
                    self.status = f"[{current}/{total}] Erro: {title}"
                elif msg_type == "skip":
                    _, current, total, title = msg
                    self.status = f"[{current}/{total}] Já existe: {title}"
                elif msg_type == "loading":
                    self.status = msg[1]
                elif msg_type == "error_general":
                    self.status = msg[1]
                elif msg_type == "sync_complete":
                    self.status = msg[1]
        except queue.Empty:
            pass

    def handle_music_key(self, key: int) -> None:
        music = self.selected_music()
        if key in (10, 13):
            if not music:
                self.status = "Nenhuma música selecionada."
                return
            try:
                self.player.play(music)
                self.status = f"Tocando: {music.title}"
                for i, m in enumerate(self.musics):
                    if m.id == music.id:
                        self.current_playlist_index = i
                        break
            except RuntimeError as err:
                self.status = str(err)
        elif key == ord("t"):
            if not music:
                self.status = "Selecione uma música."
                return
            tag_name = self.prompt("Tag para adicionar à música: ")
            if not tag_name:
                return
            tags_map = {t.name.lower(): t for t in self.tags}
            if tag_name.lower() not in tags_map:
                self.repo.create_tag(tag_name)
                self.refresh_lists()
                tags_map = {t.name.lower(): t for t in self.tags}
            self.repo.add_tag_to_music(music.id, tags_map[tag_name.lower()].id)
            self.status = f"Tag '{tag_name}' adicionada."
        elif key == ord("r"):
            if not music:
                self.status = "Selecione uma música."
                return
            tag_name = self.prompt("Tag para remover da música: ")
            tags_map = {t.name.lower(): t for t in self.tags}
            tag = tags_map.get(tag_name.lower())
            if not tag:
                self.status = "Tag não encontrada."
                return
            self.repo.remove_tag_from_music(music.id, tag.id)
            self.status = f"Tag '{tag_name}' removida."

    def handle_playlist_key(self, key: int) -> None:
        playlist = self.selected_playlist()
        if key in (10, 13):  # Enter
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            music_ids = self.repo.get_playlist_music_ids(playlist.id)
            self.status = f"Playlist '{playlist.name}' tem {len(music_ids)} músicas."
        elif key == ord("c"):
            name = self.prompt("Nome da playlist: ")
            if not name:
                return
            try:
                self.repo.create_playlist(name)
                self.refresh_lists()
                self.status = f"Playlist '{name}' criada."
            except sqlite3.IntegrityError:
                self.status = "Já existe playlist com esse nome."
        elif key == ord("d"):
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            self.repo.delete_playlist(playlist.id)
            self.refresh_lists()
            self.status = "Playlist removida."
        elif key == ord("a"):
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            title = self.prompt("Parte do nome da música: ")
            candidates = [m for m in self.musics if title.lower() in m.title.lower()]
            if not candidates:
                self.status = "Nenhuma música encontrada."
                return
            music = candidates[0]
            self.repo.add_music_to_playlist(playlist.id, music.id)
            self.status = f"Música '{music.title}' adicionada."
        elif key == ord("x"):
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            title = self.prompt("Parte do nome da música para remover: ")
            playlist_music_ids = self.repo.get_playlist_music_ids(playlist.id)
            candidates = [m for m in self.musics if m.id in playlist_music_ids and title.lower() in m.title.lower()]
            if not candidates:
                self.status = "Música não encontrada na playlist."
                return
            music = candidates[0]
            self.repo.remove_music_from_playlist(playlist.id, music.id)
            self.status = f"Música '{music.title}' removida."
        elif key == ord("t"):
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            tag_name = self.prompt("Tag para adicionar à playlist: ")
            if not tag_name:
                return
            tags_map = {t.name.lower(): t for t in self.tags}
            if tag_name.lower() not in tags_map:
                self.repo.create_tag(tag_name)
                self.refresh_lists()
                tags_map = {t.name.lower(): t for t in self.tags}
            self.repo.add_tag_to_playlist(playlist.id, tags_map[tag_name.lower()].id)
            self.status = f"Tag '{tag_name}' adicionada à playlist."
        elif key == ord("r"):
            if not playlist:
                self.status = "Selecione uma playlist."
                return
            tag_name = self.prompt("Tag para remover da playlist: ")
            tags_map = {t.name.lower(): t for t in self.tags}
            tag = tags_map.get(tag_name.lower())
            if not tag:
                self.status = "Tag não encontrada."
                return
            self.repo.remove_tag_from_playlist(playlist.id, tag.id)
            self.status = f"Tag '{tag_name}' removida da playlist."

    def handle_tag_key(self, key: int) -> None:
        tag = self.selected_tag()
        
        if self.tag_multiselect_mode:
            if key == ord(" "):
                if tag:
                    if tag.name in self.selected_tags:
                        self.selected_tags.remove(tag.name)
                    else:
                        self.selected_tags.add(tag.name)
                    self.status = f"Tags selecionadas: {len(self.selected_tags)}"
            elif key in (ord("f"), ord("F")):
                self.tag_multiselect_mode = False
                self.refresh_lists()
                if self.selected_tags:
                    self.status = f"Filtro aplicado: {', '.join(sorted(self.selected_tags))}"
                    self.section = 0
                else:
                    self.status = "Nenhuma tag selecionada."
            elif key == 27:
                self.tag_multiselect_mode = False
                self.selected_tags.clear()
                self.refresh_lists()
                self.status = "Multiselect cancelado."
            return
        
        if key == ord("c"):
            name = self.prompt("Nome da tag: ")
            if not name:
                return
            try:
                self.repo.create_tag(name)
                self.refresh_lists()
                self.status = f"Tag '{name}' criada."
            except sqlite3.IntegrityError:
                self.status = "Tag já existe."
        elif key == ord("d"):
            if not tag:
                self.status = "Selecione uma tag."
                return
            self.repo.delete_tag(tag.id)
            self.refresh_lists()
            self.status = "Tag removida."
        elif key in (ord("m"), ord("M")):
            self.tag_multiselect_mode = True
            self.status = "Modo multiselect ativado. Space: marcar/desmarcar, F: aplicar, Esc: cancelar"

    def handle_search_key(self, key: int) -> None:
        if key == ord("m"):
            query = self.prompt("Buscar músicas por título: ")
            musics = self.repo.find_musics_by_title(query)
            self.search_cache = [f"{m.title} ({self.format_duration(m.duration)})" for m in musics] or ["Nenhuma música encontrada."]
            self.selection = 0
            self.status = f"Busca por '{query}' concluída."
        elif key == ord("p"):
            name = self.prompt("Buscar playlists com tag: ")
            playlists = self.repo.find_playlists_by_tag(name)
            self.search_cache = [f"Playlist: {p.name}" for p in playlists] or ["Nenhuma playlist encontrada."]
            self.selection = 0
            self.status = f"Busca por playlists com tag '{name}' concluída."
        elif key == ord("t"):
            query = self.prompt("Buscar tags por nome: ")
            tags = self.repo.find_tags_by_name(query)
            self.search_cache = [f"Tag: {t.name}" for t in tags] or ["Nenhuma tag encontrada."]
            self.selection = 0
            self.status = f"Busca por tags '{query}' concluída."

    def handle_sync_playlist_key(self, key: int) -> None:
        sync_pl = self.selected_sync_playlist()
        
        if key in (10, 13):  # Enter
            if not sync_pl:
                self.status = "Selecione uma playlist de sync."
                return
            self.status = f"Playlist: {sync_pl.name} | URL: {sync_pl.url}"
        elif key == ord("c"):
            name = self.prompt("Nome da playlist de sync: ")
            if not name:
                return
            url = self.prompt("URL da playlist: ")
            if not url:
                return
            try:
                self.repo.create_sync_playlist(name, url)
                self.refresh_lists()
                self.status = f"Playlist de sync '{name}' criada."
            except sqlite3.IntegrityError:
                self.status = "URL já existe."
        elif key == ord("e"):
            if not sync_pl:
                self.status = "Selecione uma playlist."
                return
            name = self.prompt(f"Novo nome [{sync_pl.name}]: ") or sync_pl.name
            url = self.prompt(f"Nova URL [{sync_pl.url}]: ") or sync_pl.url
            try:
                self.repo.update_sync_playlist(sync_pl.id, name, url)
                self.refresh_lists()
                self.status = f"Playlist '{name}' atualizada."
            except sqlite3.IntegrityError:
                self.status = "URL já existe."
        elif key == ord("d"):
            if not sync_pl:
                self.status = "Selecione uma playlist."
                return
            self.repo.delete_sync_playlist(sync_pl.id)
            self.refresh_lists()
            self.status = "Playlist de sync removida."

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)
        self.stdscr.timeout(50)

        while self.running:
            self.process_status_queue()
            
            if self.player.current_music and not self.player.is_playing() and not self.player.paused:
                self.status = f"Finalizado: {self.player.current_music.title}"
                if self.autoplay:
                    next_music = self.get_next_music()
                    if next_music:
                        try:
                            self.player.play(next_music)
                            self.status = f"Tocando: {next_music.title}"
                        except RuntimeError:
                            pass
            
            self.draw()
            self.stdscr.refresh()
            
            try:
                key = self.stdscr.getch()
            except:
                key = -1
            
            if key == -1:
                time.sleep(0.05)
                continue

            if self.fuzzy_search_mode:
                if key == 27:
                    self.fuzzy_search_mode = False
                    self.fuzzy_query = ""
                    self.selection = 0
                    self.status = "Busca cancelada."
                elif key in (10, 13):
                    music = self.selected_music()
                    if music:
                        try:
                            self.player.play(music)
                            self.status = f"Tocando: {music.title}"
                            self.fuzzy_search_mode = False
                            self.fuzzy_query = ""
                        except RuntimeError as err:
                            self.status = str(err)
                elif key == curses.KEY_BACKSPACE or key == 127:
                    if self.fuzzy_query:
                        self.fuzzy_query = self.fuzzy_query[:-1]
                        self.selection = 0
                elif key in (ord("j"), curses.KEY_DOWN):
                    self.selection = min(self.selection + 1, max(0, self.current_length() - 1))
                elif key in (ord("k"), curses.KEY_UP):
                    self.selection = max(self.selection - 1, 0)
                elif 32 <= key <= 126:
                    self.fuzzy_query += chr(key)
                    self.selection = 0
                continue

            if key == ord("q"):
                self.running = False
                break
            if key == ord("/"):
                self.fuzzy_search_mode = True
                self.fuzzy_query = ""
                self.selection = 0
                self.status = "Modo de busca ativado. Digite para filtrar..."
                continue
            if key in (ord("a"), ord("A")):
                self.autoplay = not self.autoplay
                self.status = f"Autoplay: {'ON' if self.autoplay else 'OFF'}"
                continue
            if key in (ord("r"), ord("R")):
                self.shuffle = not self.shuffle
                self.update_playlist_order()
                self.status = f"Shuffle: {'ON' if self.shuffle else 'OFF'}"
                continue
            if key in (ord("v"), ord("V")):
                self.thumbnail_mode = not self.thumbnail_mode
                if self.thumbnail_mode:
                    self.show_thumbnail()
                self.status = f"Modo thumbnail: {'ON' if self.thumbnail_mode else 'OFF'}"
                continue
            if key in (ord("f"), ord("F")) and self.selected_tags:
                self.selected_tags.clear()
                self.refresh_lists()
                self.status = "Filtros removidos."
                continue
            if key in (ord("S"), ord("s")):
                self.status = "Iniciando sincronização..."
                self.sync_musics_async()
                continue
            if key == ord("["):
                self.move_music_up()
                self.status = "Música movida para cima."
                continue
            if key == ord("]"):
                self.move_music_down()
                self.status = "Música movida para baixo."
                continue
            if key in (ord("p"), ord("P")):
                if self.player.current_music:
                    if self.player.paused:
                        self.player.resume()
                        self.status = "Retomado."
                    else:
                        self.player.pause()
                        self.status = "Pausado."
                else:
                    self.status = "Nenhuma música tocando."
                continue
            if key in (ord("n"), ord("N")):
                next_music = self.get_next_music()
                if next_music:
                    try:
                        self.player.play(next_music)
                        self.status = f"Tocando: {next_music.title}"
                    except RuntimeError as err:
                        self.status = str(err)
                else:
                    self.status = "Nenhuma próxima música."
                continue
            if key in (ord("b"), ord("B")):
                prev_music = self.get_prev_music()
                if prev_music:
                    try:
                        self.player.play(prev_music)
                        self.status = f"Tocando: {prev_music.title}"
                    except RuntimeError as err:
                        self.status = str(err)
                else:
                    self.status = "Nenhuma música anterior."
                continue
            if key in (ord("="), ord("+")):
                if self.player.current_music:
                    self.player.volume_up()
                    self.status = f"Volume: {self.player.volume}%"
                else:
                    self.status = "Nenhuma música tocando."
                continue
            if key == ord("-"):
                if self.player.current_music:
                    self.player.volume_down()
                    self.status = f"Volume: {self.player.volume}%"
                else:
                    self.status = "Nenhuma música tocando."
                continue
            if key in (ord("."), ord(">")):
                if self.player.current_music:
                    self.player.seek_forward()
                    self.status = f"+5s ({self.player.format_position()})"
                else:
                    self.status = "Nenhuma música tocando."
                continue
            if key in (ord(","), ord("<")):
                if self.player.current_music:
                    self.player.seek_backward()
                    self.status = f"-5s ({self.player.format_position()})"
                else:
                    self.status = "Nenhuma música tocando."
                continue
            if key in (ord("j"), curses.KEY_DOWN):
                self.selection = min(self.selection + 1, max(0, self.current_length() - 1))
                continue
            if key in (ord("k"), curses.KEY_UP):
                self.selection = max(self.selection - 1, 0)
                continue
            if key in (ord("l"), curses.KEY_RIGHT):
                self.section = min(self.section + 1, len(self.MENU) - 1)
                self.selection = 0
                continue
            if key in (ord("h"), curses.KEY_LEFT):
                self.section = max(self.section - 1, 0)
                self.selection = 0
                continue

            if self.section == 0:
                self.handle_music_key(key)
            elif self.section == 1:
                self.handle_playlist_key(key)
            elif self.section == 2:
                self.handle_tag_key(key)
            elif self.section == 3:
                self.handle_search_key(key)
            elif self.section == 4:
                self.handle_sync_playlist_key(key)
            elif self.section == 5 and key in (10, 13):
                self.status = "Iniciando sincronização..."
                self.sync_musics_async()
            elif self.section == 6 and key in (10, 13):
                self.running = False
                break

        self.player.stop()
        self.download_manager.shutdown()


def main() -> None:
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    curses.wrapper(lambda stdscr: App(stdscr).run())


if __name__ == "__main__":
    main()
