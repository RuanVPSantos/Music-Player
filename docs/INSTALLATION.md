# Guia de Instalação - Player TUI

## 📦 Instalação Automática

### Passo 1: Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd player
```

### Passo 2: Executar o Instalador

```bash
./install.sh
```

### O Que o Instalador Faz?

1. **Verifica Dependências**
   - Python 3.10+
   - mpv (recomendado) ou ffplay
   - yt-dlp (instala se necessário)

2. **Instala o Player**
   - Copia arquivos para `~/.local/share/player`
   - Cria executável em `~/.local/bin/player`
   - Configura ambiente virtual Python
   - Instala dependências Python (requests)

3. **Preserva Dados do Usuário**
   - Mantém banco de dados (`player.db`)
   - Preserva músicas (`songs/`)
   - Preserva thumbnails (`thumbnails/`)

### Passo 3: Executar

```bash
player
```

Se o comando não for encontrado, adicione ao PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## 🔄 Atualização

Para atualizar o player, execute novamente o instalador:

```bash
cd /caminho/para/player
git pull
./install.sh
```

O instalador detecta instalação existente e:
- ✅ Faz backup do banco de dados
- ✅ Atualiza apenas o código
- ✅ Preserva músicas e configurações
- ✅ Restaura banco de dados

## 🗑️ Desinstalação

### Passo 1: Executar Desinstalador

```bash
./uninstall.sh
```

### Opções de Desinstalação

O script pergunta se deseja:
1. **Fazer backup** antes de remover (recomendado)
2. **Confirmar remoção** de todos os dados

### O Que é Removido?

- Executável: `~/.local/bin/player`
- Instalação: `~/.local/share/player`
- Banco de dados, músicas e thumbnails

### Backup Automático

Se escolher fazer backup, os dados são salvos em:
```
~/player-backup-YYYYMMDD-HHMMSS/
├── player.db
├── songs/
└── thumbnails/
```

## 🛠️ Instalação Manual (Desenvolvimento)

Para desenvolvedores ou quem prefere controle manual:

### 1. Preparar Ambiente

```bash
cd player
python3 -m venv venv
source venv/bin/activate
pip install requests
```

### 2. Instalar Dependências do Sistema

**Ubuntu/Debian:**
```bash
sudo apt install mpv yt-dlp
```

**Fedora:**
```bash
sudo dnf install mpv yt-dlp
```

**Arch:**
```bash
sudo pacman -S mpv yt-dlp
```

**macOS:**
```bash
brew install mpv yt-dlp
```

### 3. Executar

```bash
python3 player.py
```

## 📋 Requisitos Detalhados

### Python

- **Versão:** 3.10 ou superior
- **Módulos:** requests (instalado automaticamente)

### Player de Áudio

**Opção 1: MPV (Recomendado)**
- Volume em tempo real ⚡
- Seek instantâneo
- Melhor performance

```bash
sudo apt install mpv
```

**Opção 2: FFplay (Fallback)**
- Volume reinicia música
- Seek reinicia música
- Funcional mas menos eficiente

```bash
sudo apt install ffmpeg
```

### Downloader

**yt-dlp**
- Necessário para baixar músicas do YouTube
- Instalado automaticamente pelo `install.sh`

```bash
pip install yt-dlp
```

## 🔍 Verificação da Instalação

### Verificar Comando

```bash
which player
# Deve mostrar: /home/usuario/.local/bin/player
```

### Verificar Instalação

```bash
ls -la ~/.local/share/player
# Deve mostrar: src/, docs/, player.py, etc.
```

### Verificar Dependências

```bash
player --version  # (se implementado)
mpv --version
yt-dlp --version
```

## 🐛 Solução de Problemas

### Comando `player` não encontrado

**Problema:** PATH não configurado

**Solução:**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Erro: "Nenhum player encontrado"

**Problema:** mpv e ffplay não instalados

**Solução:**
```bash
sudo apt install mpv
# ou
sudo apt install ffmpeg
```

### Erro ao baixar músicas

**Problema:** yt-dlp não instalado ou desatualizado

**Solução:**
```bash
pip install --upgrade yt-dlp
```

### Permissão negada ao executar scripts

**Problema:** Scripts sem permissão de execução

**Solução:**
```bash
chmod +x install.sh uninstall.sh
```

## 📁 Estrutura de Instalação

```
~/.local/
├── bin/
│   └── player              # Executável (wrapper script)
└── share/
    └── player/             # Instalação completa
        ├── src/            # Código fonte
        ├── docs/           # Documentação
        ├── songs/          # Suas músicas
        ├── thumbnails/     # Miniaturas
        ├── player.db       # Banco de dados
        ├── player.py       # Entry point
        └── venv/           # Ambiente virtual
```

## 🔐 Segurança

- Scripts verificam checksums (futuro)
- Backup automático antes de atualizar
- Dados do usuário nunca são sobrescritos
- Instalação em diretório do usuário (sem sudo)

## 📊 Comparação de Métodos

| Método | Vantagens | Desvantagens |
|--------|-----------|--------------|
| **install.sh** | Automático, comando global, atualizações fáceis | Requer bash |
| **Manual** | Controle total, bom para dev | Configuração manual |

## 🎯 Recomendação

Para **usuários finais**: Use `./install.sh`

Para **desenvolvedores**: Use instalação manual com venv
