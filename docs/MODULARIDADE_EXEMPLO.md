# Exemplos de Modularidade

Este documento demonstra como a refatoração permite mudanças isoladas em cada componente.

## Exemplo 1: Trocar ffplay por mpv

**Arquivo a modificar:** `audio_player.py`

### Antes (ffplay):
```python
def play(self, music: Music, start_position: float = 0.0) -> None:
    ffplay_path = shutil.which("ffplay")
    if not ffplay_path:
        raise RuntimeError("ffplay não encontrado.")
    
    cmd = [ffplay_path, "-nodisp", "-autoexit", "-loglevel", "quiet", 
           "-volume", str(self.volume)]
    if start_position > 0:
        cmd.extend(["-ss", str(start_position)])
    cmd.append(str(full_path))
```

### Depois (mpv):
```python
def play(self, music: Music, start_position: float = 0.0) -> None:
    mpv_path = shutil.which("mpv")
    if not mpv_path:
        raise RuntimeError("mpv não encontrado.")
    
    cmd = [mpv_path, "--no-video", "--volume", str(self.volume)]
    if start_position > 0:
        cmd.extend([f"--start={start_position}"])
    cmd.append(str(full_path))
```

**Impacto:** ZERO mudanças em outros arquivos! ✅

---

## Exemplo 2: Trocar SQLite por PostgreSQL

**Arquivo a modificar:** `src/repository.py`

### Antes (SQLite):
```python
def __init__(self, db_path: Path) -> None:
    self.conn = sqlite3.connect(db_path)
    self.conn.row_factory = sqlite3.Row
```

### Depois (PostgreSQL):
```python
import psycopg2
from psycopg2.extras import RealDictCursor

def __init__(self, db_url: str) -> None:
    self.conn = psycopg2.connect(db_url)
    self.conn.cursor_factory = RealDictCursor
```

**Impacto:** Apenas `config.py` precisa mudar DB_PATH para DB_URL ✅

---

## Exemplo 3: Trocar curses por rich

**Arquivo a modificar:** `ui_renderer.py`

### Antes (curses):
```python
import curses

class UIRenderer:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self._init_colors()
    
    def draw_header(self) -> None:
        self.stdscr.addstr(0, 2, "╭" + "─" * (w - 4) + "╮")
```

### Depois (rich):
```python
from rich.console import Console
from rich.panel import Panel

class UIRenderer:
    def __init__(self) -> None:
        self.console = Console()
    
    def draw_header(self) -> None:
        self.console.print(Panel("♫ PLAYER TUI", style="cyan bold"))
```

**Impacto:** Apenas `app.py` precisa ajustar a inicialização ✅

---

## Exemplo 4: Trocar yt-dlp por spotdl

**Arquivo a modificar:** `download_manager.py`

### Antes (yt-dlp):
```python
ytdlp = shutil.which("yt-dlp")
dl_cmd = [
    ytdlp, "-x", "--audio-format", "mp3",
    "--newline",
    "-o", out_template,
    video_url
]
```

### Depois (spotdl):
```python
spotdl = shutil.which("spotdl")
dl_cmd = [
    spotdl, "download",
    "--output", str(SONGS_DIR),
    "--format", "mp3",
    video_url
]
```

**Impacto:** ZERO mudanças em outros arquivos! ✅

---

## Exemplo 5: Trocar requests por httpx (thumbnails)

**Arquivo a modificar:** `download_manager.py` (linhas ~512-520)

### Antes (requests):
```python
import requests

response = requests.get(thumbnail_url, timeout=10)
if response.ok:
    thumb_path.write_bytes(response.content)
```

### Depois (httpx):
```python
import httpx

with httpx.Client() as client:
    response = client.get(thumbnail_url, timeout=10)
    if response.status_code == 200:
        thumb_path.write_bytes(response.content)
```

**Impacto:** ZERO mudanças em outros arquivos! ✅

---

## Conclusão

A refatoração atingiu o objetivo de **modularidade total**:

✅ Cada componente pode ser substituído independentemente  
✅ Mudanças ficam isoladas em um único arquivo  
✅ Não há dependências circulares  
✅ Interfaces claras entre módulos  
✅ Fácil testar cada componente isoladamente  

**Isso é o que chamamos de arquitetura bem projetada!** 🎯
