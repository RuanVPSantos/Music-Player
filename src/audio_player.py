"""Audio player module for managing music playback."""

import os
import shutil
import signal
import subprocess
import time
from typing import Optional

from src.config import SONGS_DIR
from src.models import Music


class AudioPlayer:
    """Manages audio playback using ffplay."""
    
    def __init__(self) -> None:
        self.current_music: Optional[Music] = None
        self.process: Optional[subprocess.Popen[str]] = None
        self.started_at: float = 0.0
        self.accumulated: float = 0.0
        self.paused = False
        self.volume: int = 100
        self.current_position: float = 0.0

    def is_playing(self) -> bool:
        """Check if music is currently playing."""
        return self.process is not None and self.process.poll() is None

    def play(self, music: Music, start_position: float = 0.0) -> None:
        """Play a music file."""
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
        """Pause the current playback."""
        if not self.is_playing() or not self.process or self.paused:
            return
        self.accumulated += time.time() - self.started_at
        self.current_position = self.accumulated
        os.kill(self.process.pid, signal.SIGSTOP)
        self.paused = True

    def resume(self) -> None:
        """Resume paused playback."""
        if not self.is_playing() or not self.process or not self.paused:
            return
        os.kill(self.process.pid, signal.SIGCONT)
        self.started_at = time.time()
        self.paused = False

    def set_volume(self, new_volume: int) -> None:
        """Set the playback volume."""
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
        """Increase volume by 10%."""
        self.set_volume(self.volume + 10)

    def volume_down(self) -> None:
        """Decrease volume by 10%."""
        self.set_volume(self.volume - 10)

    def _restart_at_position(self, new_pos: float) -> None:
        """Restart playback at a specific position."""
        if self.is_playing():
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        
        ffplay_path = shutil.which("ffplay")
        if ffplay_path and self.current_music:
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

    def seek_forward(self) -> None:
        """Seek forward 5 seconds."""
        if not self.current_music:
            return
        new_pos = min(self.current_position + 5, self.current_music.duration)
        self.current_position = new_pos
        self.accumulated = new_pos
        self._restart_at_position(new_pos)

    def seek_backward(self) -> None:
        """Seek backward 5 seconds."""
        if not self.current_music:
            return
        new_pos = max(self.current_position - 5, 0)
        self.current_position = new_pos
        self.accumulated = new_pos
        self._restart_at_position(new_pos)

    def pause_or_resume(self) -> None:
        """Toggle between pause and resume."""
        if self.paused:
            self.resume()
        else:
            self.pause()

    def stop(self) -> None:
        """Stop playback and reset state."""
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
        """Get elapsed playback time in seconds."""
        if not self.current_music:
            return 0
        if self.paused:
            return int(self.accumulated)
        if not self.is_playing():
            return int(self.current_music.duration)
        return int(self.accumulated + max(0.0, time.time() - self.started_at))

    def format_position(self) -> str:
        """Format current position as HH:MM:SS or MM:SS."""
        sec = int(self.current_position)
        m, s = divmod(max(0, sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
