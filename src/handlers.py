"""Key handlers for different sections of the application."""

import sqlite3
from typing import Optional

from src.models import Music, Playlist, Tag, SyncPlaylist
from src.repository import Repository


class KeyHandlers:
    """Handles keyboard input for different sections."""
    
    def __init__(self, repo: Repository, ui_renderer) -> None:
        self.repo = repo
        self.ui = ui_renderer

    def handle_music_key(self, key: int, music: Optional[Music], musics: list[Music], 
                         player, tags: list[Tag]) -> tuple[str, Optional[int]]:
        """Handle keys in music section."""
        if key in (10, 13):
            if not music:
                return "Nenhuma música selecionada.", None
            try:
                player.play(music)
                current_index = None
                for i, m in enumerate(musics):
                    if m.id == music.id:
                        current_index = i
                        break
                return f"Tocando: {music.title}", current_index
            except RuntimeError as err:
                return str(err), None
        elif key == ord("t"):
            if not music:
                return "Selecione uma música.", None
            tag_name = self.ui.prompt("Tag para adicionar à música: ")
            if not tag_name:
                return "", None
            tags_map = {t.name.lower(): t for t in tags}
            if tag_name.lower() not in tags_map:
                self.repo.create_tag(tag_name)
                tags = self.repo.list_tags()
                tags_map = {t.name.lower(): t for t in tags}
            self.repo.add_tag_to_music(music.id, tags_map[tag_name.lower()].id)
            return f"Tag '{tag_name}' adicionada.", None
        elif key == ord("r"):
            if not music:
                return "Selecione uma música.", None
            tag_name = self.ui.prompt("Tag para remover da música: ")
            tags_map = {t.name.lower(): t for t in tags}
            tag = tags_map.get(tag_name.lower())
            if not tag:
                return "Tag não encontrada.", None
            self.repo.remove_tag_from_music(music.id, tag.id)
            return f"Tag '{tag_name}' removida.", None
        
        return "", None

    def handle_playlist_key(self, key: int, playlist: Optional[Playlist], 
                           musics: list[Music], tags: list[Tag]) -> str:
        """Handle keys in playlist section."""
        if key in (10, 13):
            if not playlist:
                return "Selecione uma playlist."
            music_ids = self.repo.get_playlist_music_ids(playlist.id)
            return f"Playlist '{playlist.name}' tem {len(music_ids)} músicas."
        elif key == ord("c"):
            name = self.ui.prompt("Nome da playlist: ")
            if not name:
                return ""
            try:
                self.repo.create_playlist(name)
                return f"Playlist '{name}' criada."
            except sqlite3.IntegrityError:
                return "Já existe playlist com esse nome."
        elif key == ord("d"):
            if not playlist:
                return "Selecione uma playlist."
            self.repo.delete_playlist(playlist.id)
            return "Playlist removida."
        elif key == ord("a"):
            if not playlist:
                return "Selecione uma playlist."
            title = self.ui.prompt("Parte do nome da música: ")
            candidates = [m for m in musics if title.lower() in m.title.lower()]
            if not candidates:
                return "Nenhuma música encontrada."
            music = candidates[0]
            self.repo.add_music_to_playlist(playlist.id, music.id)
            return f"Música '{music.title}' adicionada."
        elif key == ord("x"):
            if not playlist:
                return "Selecione uma playlist."
            title = self.ui.prompt("Parte do nome da música para remover: ")
            playlist_music_ids = self.repo.get_playlist_music_ids(playlist.id)
            candidates = [m for m in musics if m.id in playlist_music_ids and title.lower() in m.title.lower()]
            if not candidates:
                return "Música não encontrada na playlist."
            music = candidates[0]
            self.repo.remove_music_from_playlist(playlist.id, music.id)
            return f"Música '{music.title}' removida."
        elif key == ord("t"):
            if not playlist:
                return "Selecione uma playlist."
            tag_name = self.ui.prompt("Tag para adicionar à playlist: ")
            if not tag_name:
                return ""
            tags_map = {t.name.lower(): t for t in tags}
            if tag_name.lower() not in tags_map:
                self.repo.create_tag(tag_name)
                tags = self.repo.list_tags()
                tags_map = {t.name.lower(): t for t in tags}
            self.repo.add_tag_to_playlist(playlist.id, tags_map[tag_name.lower()].id)
            return f"Tag '{tag_name}' adicionada à playlist."
        elif key == ord("r"):
            if not playlist:
                return "Selecione uma playlist."
            tag_name = self.ui.prompt("Tag para remover da playlist: ")
            tags_map = {t.name.lower(): t for t in tags}
            tag = tags_map.get(tag_name.lower())
            if not tag:
                return "Tag não encontrada."
            self.repo.remove_tag_from_playlist(playlist.id, tag.id)
            return f"Tag '{tag_name}' removida da playlist."
        
        return ""

    def handle_tag_key(self, key: int, tag: Optional[Tag], tag_multiselect_mode: bool,
                      selected_tags: set[str]) -> tuple[str, bool, set[str], bool]:
        """Handle keys in tag section. Returns (status, multiselect_mode, selected_tags, should_refresh)."""
        if tag_multiselect_mode:
            if key == ord(" "):
                if tag:
                    if tag.name in selected_tags:
                        selected_tags.remove(tag.name)
                    else:
                        selected_tags.add(tag.name)
                    return f"Tags selecionadas: {len(selected_tags)}", True, selected_tags, False
            elif key in (ord("f"), ord("F")):
                if selected_tags:
                    return f"Filtro aplicado: {', '.join(sorted(selected_tags))}", False, selected_tags, True
                else:
                    return "Nenhuma tag selecionada.", False, selected_tags, True
            elif key == 27:
                selected_tags.clear()
                return "Multiselect cancelado.", False, selected_tags, True
            return "", True, selected_tags, False
        
        if key == ord("c"):
            name = self.ui.prompt("Nome da tag: ")
            if not name:
                return "", False, selected_tags, False
            try:
                self.repo.create_tag(name)
                return f"Tag '{name}' criada.", False, selected_tags, True
            except sqlite3.IntegrityError:
                return "Tag já existe.", False, selected_tags, False
        elif key == ord("d"):
            if not tag:
                return "Selecione uma tag.", False, selected_tags, False
            self.repo.delete_tag(tag.id)
            return "Tag removida.", False, selected_tags, True
        elif key in (ord("m"), ord("M")):
            return "Modo multiselect ativado. Space: marcar/desmarcar, F: aplicar, Esc: cancelar", True, selected_tags, False
        
        return "", False, selected_tags, False

    def handle_sync_playlist_key(self, key: int, sync_pl: Optional[SyncPlaylist]) -> tuple[str, bool]:
        """Handle keys in sync playlist section. Returns (status, should_refresh)."""
        if key in (10, 13):
            if not sync_pl:
                return "Selecione uma playlist de sync.", False
            return f"Playlist: {sync_pl.name} | URL: {sync_pl.url}", False
        elif key == ord("c"):
            name = self.ui.prompt("Nome da playlist de sync: ")
            if not name:
                return "", False
            url = self.ui.prompt("URL da playlist: ")
            if not url:
                return "", False
            try:
                self.repo.create_sync_playlist(name, url)
                return f"Playlist de sync '{name}' criada.", True
            except sqlite3.IntegrityError:
                return "URL já existe.", False
        elif key == ord("e"):
            if not sync_pl:
                return "Selecione uma playlist.", False
            name = self.ui.prompt(f"Novo nome [{sync_pl.name}]: ") or sync_pl.name
            url = self.ui.prompt(f"Nova URL [{sync_pl.url}]: ") or sync_pl.url
            try:
                self.repo.update_sync_playlist(sync_pl.id, name, url)
                return f"Playlist '{name}' atualizada.", True
            except sqlite3.IntegrityError:
                return "URL já existe.", False
        elif key == ord("d"):
            if not sync_pl:
                return "Selecione uma playlist.", False
            self.repo.delete_sync_playlist(sync_pl.id)
            return "Playlist de sync removida.", True
        
        return "", False
