# Player TUI - Terminal Music Player

Player de música para terminal com interface TUI (Text User Interface) usando curses, com suporte a playlists, tags e sincronização automática via yt-dlp.

## 📁 Estrutura do Projeto

```
player/
├── player.py              # Ponto de entrada da aplicação
├── src/                   # Código fonte modular
│   ├── __init__.py
│   ├── main.py           # Aplicação principal (PlayerApp)
│   ├── config.py         # Constantes e caminhos
│   ├── models.py         # Dataclasses (Music, Playlist, Tag, SyncPlaylist)
│   ├── repository.py     # Repository - operações de banco de dados
│   ├── audio_player.py   # AudioPlayer - controle de reprodução
│   ├── download_manager.py  # DownloadManager - downloads via yt-dlp
│   ├── sync_manager.py   # SyncManager - sincronização de playlists
│   ├── ui_renderer.py    # UIRenderer - renderização curses
│   ├── handlers.py       # KeyHandlers - tratamento de teclas
│   └── utils.py          # FileUtils - funções utilitárias
├── docs/                  # Documentação
│   ├── README.md         # Este arquivo
│   ├── SYNC_ARCHITECTURE.md  # Arquitetura de sincronização
│   └── MODULARIDADE_EXEMPLO.md  # Exemplos de modularidade
├── songs/                 # Arquivos de música (MP3)
├── thumbnails/            # Miniaturas das músicas
├── player.db             # Banco de dados SQLite
└── venv/                 # Ambiente virtual Python
```

## Estrutura Modular

O projeto foi refatorado seguindo princípios de POO e separação de responsabilidades:

### Módulos em `src/`

- **`main.py`**: Classe PlayerApp - aplicação principal que integra todos os módulos
- **`config.py`**: Constantes e caminhos do projeto (DB_PATH, SONGS_DIR, etc.)
- **`models.py`**: Modelos de dados (Music, Playlist, Tag, SyncPlaylist)
- **`repository.py`**: Classe Repository para todas as operações de banco de dados
- **`audio_player.py`**: Classe AudioPlayer para controle de reprodução com ffplay
- **`download_manager.py`**: Classe DownloadManager para downloads e conversões via yt-dlp
- **`sync_manager.py`**: Classe SyncManager para sincronização de playlists
- **`ui_renderer.py`**: Classe UIRenderer para renderização da interface curses
- **`handlers.py`**: Classe KeyHandlers para tratamento de teclas por seção
- **`utils.py`**: Classe FileUtils com funções utilitárias

## Requiplsyer.iy
# ou
./tlayeros

- Python 3.10+
- ffmpeg/ffplay (para reprodução de áudio)
- yt-dlp (para download de músicas)
- requests (para download de thumbnails)

## Instalação

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install requests yt-dlp
```

## Uso

```bash
python3 app.py
```

## Controles

### Navegação
- `↑/↓` ou `j/k`: Navegar na lista
- `←/→` ou `h/l`: Mudar de seção
- `/`: Ativar busca fuzzy
- `[` / `]`: Reordenar músicas

### Player
- `Enter`: Tocar música selecionada
- `P`: Pausar/Retomar
- `N`: Próxima música
- `B`: Música anterior
- `+/-`: Aumentar/Diminuir volume
- `</>` ou `,/.`: Retroceder/Avançar 5 segundos

### Funcionalidades
- `A`: Toggle autoplay
- `R`: Toggle shuffle
- `V`: Mostrar thumbnail
- `S`: Sincronizar playlists
- `F`: Limpar filtros de tags
- `Q`: Sair

### Por Seção

**Músicas:**
- `T`: Adicionar tag
- `R`: Remover tag

**Playlists:**
- `C`: Criar playlist
- `D`: Deletar playlist
- `A`: Adicionar música
- `X`: Remover música
- `T`: Adicionar tag
- `R`: Remover tag

**Tags:**
- `C`: Criar tag
- `D`: Deletar tag
- `M`: Modo multiselect (para filtrar)
- `Space`: Marcar/desmarcar (no multiselect)
- `F`: Aplicar filtro (no multiselect)

**Sync URLs:**
- `C`: Criar playlist de sync
- `E`: Editar playlist de sync
- `D`: Deletar playlist de sync

## Arquitetura

### Princípios Aplicados

1. **Separação de Responsabilidades**: Cada módulo tem uma responsabilidade clara
2. **Programação Orientada a Objetos**: Uso de classes com métodos e atributos bem definidos
3. **Baixo Acoplamento**: Módulos independentes que se comunicam via interfaces claras
4. **Alta Coesão**: Funcionalidades relacionadas agrupadas no mesmo módulo
5. **Simplicidade**: Código limpo e fácil de manter

### Fluxo de Dados

```
PlayerApp (app.py)
    ├── Repository (repository.py) ──> SQLite Database
    ├── AudioPlayer (audio_player.py) ──> ffplay
    ├── DownloadManager (download_manager.py) ──> yt-dlp
    ├── SyncManager (sync_manager.py) ──> DownloadManager
    ├── UIRenderer (ui_renderer.py) ──> curses
    ├── KeyHandlers (handlers.py) ──> Repository
    └── FileUtils (utils.py) ──> File System
```

## Banco de Dados

SQLite com as seguintes tabelas:
- `musics`: Músicas baixadas
- `playlists`: Playlists criadas pelo usuário
- `tags`: Tags para organização
- `playlist_music`: Relação N:N entre playlists e músicas
- `music_tags`: Tags associadas a músicas
- `playlist_tags`: Tags associadas a playlists
- `sync_playlists`: URLs de playlists para sincronização
- `sync_config`: Configurações de sincronização
- `sync_queue`: Fila de sincronização

## Diretórios

- `src/`: Código fonte modular da aplicação
- `docs/`: Documentação do projeto
- `songs/`: Arquivos de música em MP3
- `thumbnails/`: Miniaturas das músicas
- `__pycache__/`: Cache do Python (ignorado)
- `venv/`: Ambiente virtual (ignorado)

## Licença

Projeto pessoal - Uso livre
