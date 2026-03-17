#!/usr/bin/env python3
"""Player terminal com TUI, playlists, tags e sincronização com yt-dlp."""

from __future__ import annotations

import curses
import queue
import time
from typing import Optional

from src.audio_player import AudioPlayer
from src.config import DB_PATH, SONGS_DIR, THUMBS_DIR
from src.download_manager import DownloadManager
from src.handlers import KeyHandlers
from src.models import Music, Playlist, Tag, SyncPlaylist
from src.repository import Repository
from src.sync_manager import SyncManager
from src.ui_renderer import UIRenderer
from src.utils import FileUtils


class PlayerApp:
    """Main application class for the terminal music player."""
    
    MENU = ["Músicas", "Playlists", "Tags", "Busca", "Sync URLs", "Sincronizar", "Sair"]

    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.repo = Repository(DB_PATH)
        self.player = AudioPlayer()
        self.ui = UIRenderer(stdscr)
        self.handlers = KeyHandlers(self.repo, self.ui)
        
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
        self.sync_manager = SyncManager(self.status_queue, self.download_manager)
        
        self.musics: list[Music] = []
        self.playlists: list[Playlist] = []
        self.tags: list[Tag] = []
        self.sync_playlists: list[SyncPlaylist] = []
        
        self.running = True
        
        FileUtils.cleanup_temp_files()
        FileUtils.migrate_playlist_json(self.repo)
        self.refresh_lists()
        self._auto_sync()

    def _auto_sync(self) -> None:
        """Start automatic synchronization on startup."""
        if self.repo.list_sync_playlists():
            self.sync_manager.sync_playlists_async()

    def refresh_lists(self) -> None:
        """Refresh all data lists from repository."""
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

    def current_length(self) -> int:
        """Get the length of the current section's list."""
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
        """Filter musics using fuzzy search."""
        if not self.fuzzy_query:
            return self.musics
        
        query_lower = self.fuzzy_query.lower()
        return [m for m in self.musics if query_lower in m.title.lower()]

    def update_playlist_order(self) -> None:
        """Update the playback order of musics."""
        if self.shuffle:
            import random
            self.playlist_order = [m.id for m in self.musics]
            random.shuffle(self.playlist_order)
        else:
            self.playlist_order = [m.id for m in self.musics]
        self.current_playlist_index = 0

    def get_next_music(self) -> Optional[Music]:
        """Get the next music in the playlist."""
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
        """Get the previous music in the playlist."""
        if not self.playlist_order:
            return None
        
        self.current_playlist_index = max(0, self.current_playlist_index - 2)
        return self.get_next_music()

    def move_music_up(self) -> None:
        """Move selected music up in the list."""
        if self.section != 0 or self.selection <= 0:
            return
        
        idx = self.selection
        self.musics[idx], self.musics[idx - 1] = self.musics[idx - 1], self.musics[idx]
        self.selection -= 1
        self.update_playlist_order()

    def move_music_down(self) -> None:
        """Move selected music down in the list."""
        if self.section != 0 or self.selection >= len(self.musics) - 1:
            return
        
        idx = self.selection
        self.musics[idx], self.musics[idx + 1] = self.musics[idx + 1], self.musics[idx]
        self.selection += 1
        self.update_playlist_order()

    def selected_music(self) -> Optional[Music]:
        """Get the currently selected music."""
        if self.fuzzy_search_mode:
            filtered = self.get_fuzzy_filtered_musics()
            if 0 <= self.selection < len(filtered):
                return filtered[self.selection]
            return None
        if 0 <= self.selection < len(self.musics):
            return self.musics[self.selection]
        return None

    def selected_playlist(self) -> Optional[Playlist]:
        """Get the currently selected playlist."""
        if 0 <= self.selection < len(self.playlists):
            return self.playlists[self.selection]
        return None

    def selected_tag(self) -> Optional[Tag]:
        """Get the currently selected tag."""
        if 0 <= self.selection < len(self.tags):
            return self.tags[self.selection]
        return None

    def selected_sync_playlist(self) -> Optional[SyncPlaylist]:
        """Get the currently selected sync playlist."""
        if 0 <= self.selection < len(self.sync_playlists):
            return self.sync_playlists[self.selection]
        return None

    def process_status_queue(self) -> None:
        """Process download status messages from the queue."""
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

    def build_items_list(self) -> list[str]:
        """Build the list of items to display based on current section."""
        items: list[str] = []
        
        if self.fuzzy_search_mode:
            for music in self.get_fuzzy_filtered_musics():
                tags = ",".join(self.repo.tags_for_music(music.id))
                items.append(f"{music.title} • {self.ui.format_duration(music.duration)} • {tags or 'sem tags'}")
        elif self.section == 0:
            for music in self.musics:
                tags = ",".join(self.repo.tags_for_music(music.id))
                items.append(f"{music.title} • {self.ui.format_duration(music.duration)} • {tags or 'sem tags'}")
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
        
        return items

    def draw(self) -> None:
        """Draw the entire UI."""
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        self.ui.draw_header()
        self.ui.draw_menu(self.MENU, self.section)
        
        y = self.ui.draw_filter_info(5, self.fuzzy_search_mode, self.fuzzy_query, self.selected_tags)
        
        items = self.build_items_list()
        
        max_items = h - 14
        if self.selection < self.scroll_offset:
            self.scroll_offset = self.selection
        elif self.selection >= self.scroll_offset + max_items:
            self.scroll_offset = self.selection - max_items + 1
        
        self.ui.draw_items(y, items, self.selection, self.scroll_offset)
        
        progress_y = h - 7
        self.stdscr.addstr(progress_y, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)
        self.ui.draw_progress(progress_y + 1, self.player)
        
        help_y = h - 4
        self.stdscr.addstr(help_y, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)
        self.ui.draw_help(help_y + 1, self.section, self.fuzzy_search_mode, self.tag_multiselect_mode)
        
        self.ui.draw_status(h - 2, self.status, self.autoplay, self.shuffle)
        
        self.stdscr.refresh()

    def handle_fuzzy_search_key(self, key: int) -> None:
        """Handle keys in fuzzy search mode."""
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

    def handle_global_keys(self, key: int) -> bool:
        """Handle global keys that work in any section. Returns True if key was handled."""
        if key == ord("q"):
            self.running = False
            return True
        if key == ord("/"):
            self.fuzzy_search_mode = True
            self.fuzzy_query = ""
            self.selection = 0
            self.status = "Modo de busca ativado. Digite para filtrar..."
            return True
        if key in (ord("a"), ord("A")):
            self.autoplay = not self.autoplay
            self.status = f"Autoplay: {'ON' if self.autoplay else 'OFF'}"
            return True
        if key in (ord("r"), ord("R")):
            self.shuffle = not self.shuffle
            self.update_playlist_order()
            self.status = f"Shuffle: {'ON' if self.shuffle else 'OFF'}"
            return True
        if key in (ord("v"), ord("V")):
            if self.player.current_music:
                self.status = FileUtils.show_thumbnail(self.player.current_music.thumbnail)
            else:
                self.status = "Nenhuma música tocando."
            return True
        if key in (ord("f"), ord("F")) and self.selected_tags:
            self.selected_tags.clear()
            self.refresh_lists()
            self.status = "Filtros removidos."
            return True
        if key in (ord("S"), ord("s")):
            self.status = "Iniciando sincronização..."
            self.sync_manager.sync_playlists_async()
            return True
        if key == ord("["):
            self.move_music_up()
            self.status = "Música movida para cima."
            return True
        if key == ord("]"):
            self.move_music_down()
            self.status = "Música movida para baixo."
            return True
        
        return False

    def handle_player_keys(self, key: int) -> bool:
        """Handle player control keys. Returns True if key was handled."""
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
            return True
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
            return True
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
            return True
        if key in (ord("="), ord("+")):
            if self.player.current_music:
                self.player.volume_up()
                self.status = f"Volume: {self.player.volume}%"
            else:
                self.status = "Nenhuma música tocando."
            return True
        if key == ord("-"):
            if self.player.current_music:
                self.player.volume_down()
                self.status = f"Volume: {self.player.volume}%"
            else:
                self.status = "Nenhuma música tocando."
            return True
        if key in (ord("."), ord(">")):
            if self.player.current_music:
                self.player.seek_forward()
                self.status = f"+5s ({self.player.format_position()})"
            else:
                self.status = "Nenhuma música tocando."
            return True
        if key in (ord(","), ord("<")):
            if self.player.current_music:
                self.player.seek_backward()
                self.status = f"-5s ({self.player.format_position()})"
            else:
                self.status = "Nenhuma música tocando."
            return True
        
        return False

    def handle_navigation_keys(self, key: int) -> bool:
        """Handle navigation keys. Returns True if key was handled."""
        if key in (ord("j"), curses.KEY_DOWN):
            self.selection = min(self.selection + 1, max(0, self.current_length() - 1))
            return True
        if key in (ord("k"), curses.KEY_UP):
            self.selection = max(self.selection - 1, 0)
            return True
        if key in (ord("l"), curses.KEY_RIGHT):
            self.section = min(self.section + 1, len(self.MENU) - 1)
            self.selection = 0
            return True
        if key in (ord("h"), curses.KEY_LEFT):
            self.section = max(self.section - 1, 0)
            self.selection = 0
            return True
        
        return False

    def handle_section_keys(self, key: int) -> None:
        """Handle keys specific to the current section."""
        if self.section == 0:
            status, playlist_idx = self.handlers.handle_music_key(
                key, self.selected_music(), self.musics, self.player, self.tags
            )
            if status:
                self.status = status
            if playlist_idx is not None:
                self.current_playlist_index = playlist_idx
        elif self.section == 1:
            status = self.handlers.handle_playlist_key(
                key, self.selected_playlist(), self.musics, self.tags
            )
            if status:
                self.status = status
                self.refresh_lists()
        elif self.section == 2:
            status, multiselect, tags, should_refresh = self.handlers.handle_tag_key(
                key, self.selected_tag(), self.tag_multiselect_mode, self.selected_tags
            )
            if status:
                self.status = status
            self.tag_multiselect_mode = multiselect
            self.selected_tags = tags
            if should_refresh:
                self.refresh_lists()
                if self.selected_tags and not multiselect:
                    self.section = 0
        elif self.section == 4:
            status, should_refresh = self.handlers.handle_sync_playlist_key(
                key, self.selected_sync_playlist()
            )
            if status:
                self.status = status
            if should_refresh:
                self.refresh_lists()
        elif self.section == 5 and key in (10, 13):
            self.status = "Iniciando sincronização..."
            self.sync_manager.sync_playlists_async()
        elif self.section == 6 and key in (10, 13):
            self.running = False

    def run(self) -> None:
        """Main application loop."""
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
            
            try:
                key = self.stdscr.getch()
            except:
                key = -1
            
            if key == -1:
                time.sleep(0.05)
                continue

            if self.fuzzy_search_mode:
                self.handle_fuzzy_search_key(key)
                continue

            if self.handle_global_keys(key):
                continue
            
            if self.handle_player_keys(key):
                continue
            
            if self.handle_navigation_keys(key):
                continue
            
            self.handle_section_keys(key)

        self.player.stop()
        self.download_manager.shutdown()


def main() -> None:
    """Application entry point."""
    SONGS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    curses.wrapper(lambda stdscr: PlayerApp(stdscr).run())


if __name__ == "__main__":
    main()
