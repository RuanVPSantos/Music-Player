#!/bin/bash
# Player TUI - Uninstallation Script
# Removes the player from the system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="$HOME/.local/share/player"
BIN_PATH="$HOME/.local/bin/player"

echo -e "${RED}╔════════════════════════════════════════╗${NC}"
echo -e "${RED}║      Player TUI - Desinstalação        ║${NC}"
echo -e "${RED}╚════════════════════════════════════════╝${NC}"
echo

# Check if installed
if [ ! -d "$INSTALL_DIR" ] && [ ! -f "$BIN_PATH" ]; then
    echo -e "${YELLOW}⚠${NC}  Player não está instalado"
    exit 0
fi

# Ask for confirmation
echo -e "${YELLOW}Esta ação irá remover:${NC}"
echo -e "  • Executável: $BIN_PATH"
echo -e "  • Instalação: $INSTALL_DIR"
echo
echo -e "${RED}ATENÇÃO:${NC} Suas músicas e banco de dados serão ${RED}REMOVIDOS${NC}!"
echo -e "${YELLOW}Deseja continuar? [s/N]${NC} "
read -r response

if [[ ! "$response" =~ ^[sS]$ ]]; then
    echo -e "${BLUE}ℹ${NC}  Desinstalação cancelada"
    exit 0
fi

# Optional: Backup user data
echo
echo -e "${YELLOW}Deseja fazer backup dos seus dados antes? [S/n]${NC} "
read -r backup_response

if [[ ! "$backup_response" =~ ^[nN]$ ]]; then
    BACKUP_DIR="$HOME/player-backup-$(date +%Y%m%d-%H%M%S)"
    echo -e "${YELLOW}→${NC} Criando backup em $BACKUP_DIR..."
    mkdir -p "$BACKUP_DIR"
    
    if [ -f "$INSTALL_DIR/player.db" ]; then
        cp "$INSTALL_DIR/player.db" "$BACKUP_DIR/"
        echo -e "${GREEN}✓${NC} Banco de dados copiado"
    fi
    
    if [ -d "$INSTALL_DIR/songs" ] && [ "$(ls -A $INSTALL_DIR/songs)" ]; then
        cp -r "$INSTALL_DIR/songs" "$BACKUP_DIR/"
        echo -e "${GREEN}✓${NC} Músicas copiadas"
    fi
    
    if [ -d "$INSTALL_DIR/thumbnails" ] && [ "$(ls -A $INSTALL_DIR/thumbnails)" ]; then
        cp -r "$INSTALL_DIR/thumbnails" "$BACKUP_DIR/"
        echo -e "${GREEN}✓${NC} Thumbnails copiadas"
    fi
    
    echo -e "${GREEN}✓${NC} Backup salvo em: $BACKUP_DIR"
fi

# Remove files
echo
echo -e "${YELLOW}→${NC} Removendo arquivos..."

if [ -f "$BIN_PATH" ]; then
    rm -f "$BIN_PATH"
    echo -e "${GREEN}✓${NC} Executável removido"
fi

if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo -e "${GREEN}✓${NC} Diretório de instalação removido"
fi

# Success message
echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Desinstalação Concluída!         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}✓${NC} Player TUI foi removido do sistema"

if [[ ! "$backup_response" =~ ^[nN]$ ]]; then
    echo -e "${BLUE}ℹ${NC}  Seus dados foram salvos em: $BACKUP_DIR"
fi

echo
echo -e "${BLUE}Obrigado por usar o Player TUI!${NC}"
echo

exit 0
