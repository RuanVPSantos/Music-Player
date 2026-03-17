"""UI rendering module for the terminal interface."""

import curses
from typing import Optional

from src.audio_player import AudioPlayer
from src.models import Music, Playlist, Tag, SyncPlaylist


class UIRenderer:
    """Handles all UI rendering for the terminal interface."""
    
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self._init_colors()

    def _init_colors(self) -> None:
        """Initialize color pairs for the UI."""
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

    def format_duration(self, sec: int) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS."""
        m, s = divmod(max(0, sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def draw_header(self) -> None:
        """Draw the application header."""
        h, w = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(0, 2, "╭" + "─" * (w - 4) + "╮", curses.color_pair(2))
        self.stdscr.addstr(1, 2, "│", curses.color_pair(2))
        self.stdscr.addstr(1, 4, "♫ PLAYER TUI", curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(1, w - 3, "│", curses.color_pair(2))
        self.stdscr.addstr(2, 2, "╰" + "─" * (w - 4) + "╯", curses.color_pair(2))

    def draw_menu(self, menu_items: list[str], current_section: int) -> None:
        """Draw the menu bar."""
        h, w = self.stdscr.getmaxyx()
        menu_y = 3
        x_pos = 4
        
        for idx, name in enumerate(menu_items):
            if idx == current_section:
                self.stdscr.addstr(menu_y, x_pos, f" {name} ", curses.color_pair(8) | curses.A_BOLD)
            else:
                self.stdscr.addstr(menu_y, x_pos, f" {name} ", curses.color_pair(7) | curses.A_DIM)
            x_pos += len(name) + 4
        
        self.stdscr.addstr(4, 2, "─" * (w - 4), curses.color_pair(7) | curses.A_DIM)

    def draw_filter_info(self, y: int, fuzzy_mode: bool, fuzzy_query: str, selected_tags: set[str]) -> int:
        """Draw filter/search information."""
        h, w = self.stdscr.getmaxyx()
        
        if fuzzy_mode:
            search_line = f"🔍 Busca: {fuzzy_query}_ (Esc: sair)"
            self.stdscr.addstr(y, 4, search_line[:w - 8], curses.color_pair(1) | curses.A_BOLD)
            return y + 2
        elif selected_tags:
            filter_line = f"🏷  Filtros ativos: {', '.join(sorted(selected_tags))} (F: limpar)"
            self.stdscr.addstr(y, 4, filter_line[:w - 8], curses.color_pair(4) | curses.A_BOLD)
            return y + 2
        
        return y + 1

    def draw_items(self, y: int, items: list[str], selection: int, scroll_offset: int) -> None:
        """Draw the list of items."""
        h, w = self.stdscr.getmaxyx()
        max_items = h - 14
        
        visible_items = items[scroll_offset:scroll_offset + max_items]
        
        for idx, item in enumerate(visible_items):
            actual_idx = idx + scroll_offset
            if actual_idx == selection:
                self.stdscr.addstr(y + idx, 4, "▶", curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y + idx, 6, item[:w - 8], curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y + idx, 4, "•", curses.color_pair(7) | curses.A_DIM)
                self.stdscr.addstr(y + idx, 6, item[:w - 8], curses.color_pair(7))
        
        if len(items) > max_items:
            scroll_info = f" [{selection + 1}/{len(items)}] "
            self.stdscr.addstr(y + max_items - 1, w - len(scroll_info) - 4, scroll_info, curses.color_pair(7) | curses.A_DIM)

    def draw_progress(self, y: int, player: AudioPlayer) -> None:
        """Draw the playback progress bar."""
        h, w = self.stdscr.getmaxyx()
        
        if not player.current_music:
            self.stdscr.addstr(y, 2, "♪ ", curses.color_pair(7))
            self.stdscr.addstr("Nenhuma música tocando", curses.color_pair(7) | curses.A_DIM)
            return

        music = player.current_music
        elapsed = min(player.elapsed_seconds(), max(1, music.duration))
        total = max(1, music.duration)
        ratio = min(1.0, elapsed / total)
        bar_w = min(50, max(20, w - 40))
        done = int(bar_w * ratio)
        
        if player.paused:
            icon = "⏸ "
            state_color = curses.color_pair(4)
        elif player.is_playing():
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
        
        # Mostrar volume e player backend
        backend_indicator = "⚡" if player.player_backend == "mpv" else "🔊"
        self.stdscr.addstr(f" {backend_indicator} Vol: {player.volume}%", curses.color_pair(6) | curses.A_DIM)
        
        # Indicar se é tempo real ou não
        if player.player_backend == "mpv":
            self.stdscr.addstr(" [RT]", curses.color_pair(3) | curses.A_DIM)

    def draw_help(self, y: int, section: int, fuzzy_mode: bool, tag_multiselect: bool) -> None:
        """Draw the help text."""
        h, w = self.stdscr.getmaxyx()
        
        if fuzzy_mode:
            help_text = "Digite para buscar  Enter: tocar  Esc: sair da busca  Q: sair"
        elif section == 2:
            if tag_multiselect:
                help_text = "↑↓: navegar  Space: marcar/desmarcar  F: aplicar filtro  Esc: cancelar  Q: sair"
            else:
                help_text = "↑↓: navegar  M: multiselect  C: criar  D: deletar  Q: sair"
        elif section == 4:
            help_text = "↑↓: navegar  C: criar  E: editar  D: deletar  Q: sair"
        else:
            help_text = "↑↓: navegar  []: reordenar  /: busca  V: thumb  A: auto  R: shuffle  S: sync  P/N/B: player  +/-: vol  <>.: seek  Q: sair"
        
        self.stdscr.addstr(y, 4, help_text[:w - 8], curses.color_pair(6) | curses.A_DIM)

    def draw_status(self, y: int, status: str, autoplay: bool, shuffle: bool) -> None:
        """Draw the status line."""
        h, w = self.stdscr.getmaxyx()
        
        status_line = status[:w - 40]
        flags = []
        if autoplay:
            flags.append("AUTO")
        if shuffle:
            flags.append("SHUFFLE")
        if flags:
            status_line += f" [{' | '.join(flags)}]"
        
        self.stdscr.addstr(y, 4, "● ", curses.color_pair(3))
        self.stdscr.addstr(status_line[:w - 10], curses.color_pair(7))

    def prompt(self, text: str) -> str:
        """Show a prompt and get user input."""
        h, w = self.stdscr.getmaxyx()
        self.stdscr.move(h - 1, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(h - 1, 0, text[: max(1, w - 1)])
        self.stdscr.refresh()
        curses.echo()
        curses.curs_set(1)
        self.stdscr.timeout(-1)
        try:
            value = self.stdscr.getstr(h - 1, min(len(text), w - 2), max(1, w - len(text) - 1)).decode("utf-8").strip()
        finally:
            curses.noecho()
            curses.curs_set(0)
            self.stdscr.timeout(50)
        return value
