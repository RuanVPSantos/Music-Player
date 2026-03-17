# Changelog - Suporte ao MPV com Volume em Tempo Real

## 🎵 Mudanças Implementadas

### ✅ Suporte Dual: MPV + FFplay

O `AudioPlayer` agora suporta **dois backends de reprodução**:

1. **MPV** (preferencial) - Com controle em tempo real via IPC
2. **FFplay** (fallback) - Mantido para compatibilidade

### 🎚️ Volume em Tempo Real

**Com MPV:**
- ✅ Volume muda **instantaneamente** sem reiniciar a música
- ✅ Usa socket IPC (Inter-Process Communication)
- ✅ Seek também é instantâneo
- ✅ Pause/Resume via comandos IPC

**Com FFplay:**
- ⚠️ Volume requer reiniciar a música (comportamento antigo)
- ⚠️ Seek reinicia a música
- ⚠️ Pause/Resume via sinais SIGSTOP/SIGCONT

## 🔧 Implementação Técnica

### Detecção Automática de Player

```python
def _detect_player(self) -> str:
    """Detect which player is available (prefer mpv)."""
    if shutil.which("mpv"):
        return "mpv"
    elif shutil.which("ffplay"):
        return "ffplay"
    else:
        return "none"
```

### Comunicação IPC com MPV

```python
def _send_mpv_command(self, command: dict) -> None:
    """Send command to mpv via IPC socket."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(str(self.ipc_socket_path))
    sock.sendall((json.dumps(command) + "\n").encode())
    sock.close()
```

### Volume em Tempo Real

```python
def set_volume(self, new_volume: int) -> None:
    if self.player_backend == "mpv":
        # Volume em tempo real!
        self._send_mpv_command({"command": ["set_property", "volume", self.volume]})
    else:
        # ffplay precisa reiniciar
        # ... código de restart ...
```

## 🎨 Mudanças na UI

A interface agora mostra:

- **⚡ [RT]** - Quando usando MPV (Real-Time)
- **🔊** - Quando usando FFplay

Exemplo:
```
▶ Nome da Música
  ━━━━━━━━━━━━━━━─────────── 02:30/05:00 ⚡ Vol: 80% [RT]
```

## 📦 Arquivos Modificados

### `src/audio_player.py`
- ✅ Adicionado suporte ao MPV com IPC
- ✅ Mantido FFplay como fallback
- ✅ Volume em tempo real com MPV
- ✅ Seek instantâneo com MPV
- ✅ Pause/Resume via IPC com MPV

### `src/ui_renderer.py`
- ✅ Indicador visual do player backend
- ✅ Badge [RT] para indicar controle em tempo real

## 🚀 Como Usar

### Instalar MPV (Recomendado)

```bash
# Ubuntu/Debian
sudo apt install mpv

# Fedora
sudo dnf install mpv

# Arch
sudo pacman -S mpv

# macOS
brew install mpv
```

### Executar o Player

```bash
python3 player.py
```

O player detectará automaticamente qual backend usar:
1. Se `mpv` estiver instalado → usa MPV (com volume em tempo real)
2. Se apenas `ffplay` estiver instalado → usa FFplay (modo legado)
3. Se nenhum estiver instalado → mostra erro

## 🎯 Benefícios

### Com MPV
- ✅ **Volume instantâneo** - Sem interrupção na música
- ✅ **Seek mais rápido** - Não precisa reiniciar
- ✅ **Melhor controle** - Comandos via IPC
- ✅ **Menos CPU** - Não reinicia processo

### Mantendo FFplay
- ✅ **Compatibilidade** - Funciona em sistemas antigos
- ✅ **Fallback automático** - Sem configuração manual
- ✅ **Zero breaking changes** - Código antigo funciona

## 🔍 Detalhes Técnicos

### Socket IPC
- Criado em `/tmp/mpv-socket-{PID}`
- Removido automaticamente ao parar música
- Comunicação via JSON sobre Unix socket

### Comandos MPV Usados
- `set_property volume {valor}` - Ajustar volume
- `set_property pause {true/false}` - Pausar/Retomar
- `seek {posição} absolute` - Pular para posição

## 📊 Comparação

| Recurso | MPV | FFplay |
|---------|-----|--------|
| Volume em tempo real | ✅ Sim | ❌ Não (reinicia) |
| Seek instantâneo | ✅ Sim | ❌ Não (reinicia) |
| Pause/Resume | ✅ IPC | ⚠️ Sinais OS |
| Uso de CPU | 🟢 Baixo | 🟡 Médio |
| Instalação | `apt install mpv` | `apt install ffmpeg` |

## 🎉 Resultado

Agora você tem:
- 🎵 Controle de volume **suave e instantâneo** com MPV
- 🔄 Fallback automático para FFplay se MPV não estiver instalado
- 🎨 Interface mostrando qual player está ativo
- 📦 Código modular e fácil de manter

**Experimente ajustar o volume enquanto a música toca - é instantâneo!** ⚡
