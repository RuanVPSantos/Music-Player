#!/bin/bash
# Player TUI - Installation Script
# Installs or updates the player to ~/.local/bin/player

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="$HOME/.local/share/player"
BIN_DIR="$HOME/.local/bin"
BIN_PATH="$BIN_DIR/player"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Player TUI - Instalação/Update     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo

# Check Python version
echo -e "${YELLOW}→${NC} Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 não encontrado. Instale Python 3.10+ primeiro."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION encontrado"

# Check for audio player
echo -e "${YELLOW}→${NC} Verificando player de áudio..."
if command -v mpv &> /dev/null; then
    echo -e "${GREEN}✓${NC} mpv encontrado (recomendado - volume em tempo real)"
elif command -v ffplay &> /dev/null; then
    echo -e "${YELLOW}✓${NC} ffplay encontrado (funcional, mas sem volume em tempo real)"
    echo -e "${YELLOW}  Dica: Instale mpv para melhor experiência: sudo apt install mpv${NC}"
else
    echo -e "${RED}✗${NC} Nenhum player encontrado!"
    echo -e "${YELLOW}  Instale mpv (recomendado): sudo apt install mpv${NC}"
    echo -e "${YELLOW}  Ou ffmpeg: sudo apt install ffmpeg${NC}"
    exit 1
fi

# Check for yt-dlp
echo -e "${YELLOW}→${NC} Verificando yt-dlp..."
if ! command -v yt-dlp &> /dev/null; then
    echo -e "${YELLOW}!${NC} yt-dlp não encontrado (necessário para downloads)"
    echo -e "${YELLOW}  Instalando via pip...${NC}"
    pip3 install --user yt-dlp
    echo -e "${GREEN}✓${NC} yt-dlp instalado"
else
    echo -e "${GREEN}✓${NC} yt-dlp encontrado"
fi

# Create directories
echo
echo -e "${YELLOW}→${NC} Criando diretórios..."
mkdir -p "$BIN_DIR"
mkdir -p "$INSTALL_DIR"

# Check if it's an update
if [ -d "$INSTALL_DIR/src" ]; then
    echo -e "${BLUE}ℹ${NC} Instalação existente detectada - atualizando..."
    IS_UPDATE=true
    
    # Backup user data
    if [ -f "$INSTALL_DIR/player.db" ]; then
        echo -e "${YELLOW}→${NC} Fazendo backup do banco de dados..."
        cp "$INSTALL_DIR/player.db" "$INSTALL_DIR/player.db.backup"
    fi
else
    echo -e "${BLUE}ℹ${NC} Nova instalação"
    IS_UPDATE=false
fi

# Copy source files
echo -e "${YELLOW}→${NC} Copiando arquivos do programa..."
rsync -a --exclude='venv' \
         --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='.git' \
         --exclude='songs' \
         --exclude='thumbnails' \
         --exclude='*.db' \
         --exclude='*.db.backup' \
         --exclude='*.bak' \
         "$SCRIPT_DIR/" "$INSTALL_DIR/"

# Preserve or create data directories
echo -e "${YELLOW}→${NC} Configurando diretórios de dados..."
mkdir -p "$INSTALL_DIR/songs"
mkdir -p "$INSTALL_DIR/thumbnails"

# Copy database only if it doesn't exist in installation
if [ ! -f "$INSTALL_DIR/player.db" ]; then
    if [ -f "$SCRIPT_DIR/player.db" ]; then
        echo -e "${YELLOW}→${NC} Copiando banco de dados inicial..."
        cp "$SCRIPT_DIR/player.db" "$INSTALL_DIR/player.db"
    fi
elif [ "$IS_UPDATE" = true ] && [ -f "$INSTALL_DIR/player.db.backup" ]; then
    # Restore database if it was backed up during update
    echo -e "${YELLOW}→${NC} Restaurando banco de dados..."
    mv "$INSTALL_DIR/player.db.backup" "$INSTALL_DIR/player.db"
fi

# Copy songs only if directory is empty
if [ ! "$(ls -A $INSTALL_DIR/songs 2>/dev/null)" ]; then
    if [ -d "$SCRIPT_DIR/songs" ] && [ "$(ls -A $SCRIPT_DIR/songs 2>/dev/null)" ]; then
        echo -e "${YELLOW}→${NC} Copiando músicas iniciais..."
        cp -r "$SCRIPT_DIR/songs/"* "$INSTALL_DIR/songs/" 2>/dev/null || true
    fi
else
    echo -e "${GREEN}✓${NC} Músicas existentes preservadas ($(ls -1 $INSTALL_DIR/songs 2>/dev/null | wc -l) arquivos)"
fi

# Copy thumbnails only if directory is empty
if [ ! "$(ls -A $INSTALL_DIR/thumbnails 2>/dev/null)" ]; then
    if [ -d "$SCRIPT_DIR/thumbnails" ] && [ "$(ls -A $SCRIPT_DIR/thumbnails 2>/dev/null)" ]; then
        echo -e "${YELLOW}→${NC} Copiando thumbnails iniciais..."
        cp -r "$SCRIPT_DIR/thumbnails/"* "$INSTALL_DIR/thumbnails/" 2>/dev/null || true
    fi
else
    echo -e "${GREEN}✓${NC} Thumbnails existentes preservadas ($(ls -1 $INSTALL_DIR/thumbnails 2>/dev/null | wc -l) arquivos)"
fi

# Create executable wrapper in bin
echo -e "${YELLOW}→${NC} Criando executável em $BIN_PATH..."
cat > "$BIN_PATH" << 'EOF'
#!/bin/bash
# Player TUI - Wrapper Script

INSTALL_DIR="$HOME/.local/share/player"
cd "$INSTALL_DIR" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    pip install requests > /dev/null 2>&1
else
    source venv/bin/activate
fi

# Run the player
exec python3 player.py "$@"
EOF

chmod +x "$BIN_PATH"

# Setup virtual environment
echo -e "${YELLOW}→${NC} Configurando ambiente virtual..."
cd "$INSTALL_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    echo -e "${YELLOW}→${NC} Instalando dependências Python..."
    pip install requests > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} Dependências instaladas"
else
    echo -e "${GREEN}✓${NC} Ambiente virtual já existe"
fi

# Check if bin directory is in PATH
echo
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}⚠${NC}  O diretório $BIN_DIR não está no PATH"
    echo -e "${YELLOW}  Adicione esta linha ao seu ~/.bashrc ou ~/.zshrc:${NC}"
    echo -e "${BLUE}  export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo
    echo -e "${YELLOW}  Depois execute: source ~/.bashrc${NC}"
else
    echo -e "${GREEN}✓${NC} $BIN_DIR está no PATH"
fi

# Success message
echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Instalação Concluída!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "${BLUE}Instalado em:${NC} $INSTALL_DIR"
echo -e "${BLUE}Executável:${NC} $BIN_PATH"
echo
echo -e "${GREEN}Para executar, digite:${NC} ${BLUE}player${NC}"
echo
if [ "$IS_UPDATE" = true ]; then
    echo -e "${GREEN}✓${NC} Atualização concluída com sucesso!"
    echo -e "${BLUE}ℹ${NC}  Seus dados (músicas, playlists, tags) foram preservados"
else
    echo -e "${GREEN}✓${NC} Instalação concluída com sucesso!"
fi
echo

exit 0
