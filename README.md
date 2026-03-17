# Player TUI - Terminal Music Player

Player de música para terminal com interface TUI usando curses, playlists, tags e sincronização automática via yt-dlp.

## 🚀 Início Rápido

```bash
# Executar o player
python3 player.py
# ou
./player.py
```

## 📁 Estrutura do Projeto

```
player/
├── player.py              # Ponto de entrada
├── src/                   # Código fonte modular
│   ├── main.py           # Aplicação principal
│   ├── config.py         # Configurações
│   ├── models.py         # Modelos de dados
│   ├── repository.py     # Banco de dados
│   ├── audio_player.py   # Reprodução de áudio
│   ├── download_manager.py  # Downloads
│   ├── sync_manager.py   # Sincronização
│   ├── ui_renderer.py    # Interface
│   ├── handlers.py       # Controle de teclas
│   └── utils.py          # Utilitários
├── docs/                  # Documentação completa
│   ├── README.md         # Documentação detalhada
│   ├── SYNC_ARCHITECTURE.md
│   └── MODULARIDADE_EXEMPLO.md
├── songs/                 # Músicas (MP3)
├── thumbnails/            # Miniaturas
└── player.db             # Banco SQLite
```

## 📚 Documentação

- **[Documentação Completa](docs/README.md)** - Guia completo de uso e arquitetura
- **[Arquitetura de Sincronização](docs/SYNC_ARCHITECTURE.md)** - Sistema de sync multi-plataforma
- **[Exemplos de Modularidade](docs/MODULARIDADE_EXEMPLO.md)** - Como modificar componentes

## ⚙️ Instalação

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install requests yt-dlp
```

**Requisitos do sistema:**
- Python 3.10+
- ffmpeg/ffplay (reprodução)
- yt-dlp (downloads)

## 🎮 Controles Principais

- `↑↓` ou `j/k` - Navegar
- `←→` ou `h/l` - Mudar seção
- `Enter` - Tocar música
- `P` - Pausar/Retomar
- `N/B` - Próxima/Anterior
- `+/-` - Volume
- `/` - Busca fuzzy
- `S` - Sincronizar
- `Q` - Sair

## 🏗️ Arquitetura

Projeto modular com separação clara de responsabilidades:

- ✅ **Baixo acoplamento** - Componentes independentes
- ✅ **Alta coesão** - Responsabilidades bem definidas
- ✅ **Testável** - Classes isoladas
- ✅ **Manutenível** - Fácil localizar e modificar

Veja [docs/README.md](docs/README.md) para detalhes completos.

## 📄 Licença

Projeto pessoal - Uso livre
