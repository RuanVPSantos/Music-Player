# Lógica de Instalação e Atualização

## 🔄 Comportamento do install.sh

O script `install.sh` foi projetado para ser **inteligente** e **não destrutivo**, preservando sempre os dados do usuário.

## 📋 Fluxo de Decisão

### 1. Detecção de Instalação Existente

```bash
if [ -d "$INSTALL_DIR/src" ]; then
    # É uma atualização
    IS_UPDATE=true
else
    # É uma instalação nova
    IS_UPDATE=false
fi
```

### 2. Backup Temporário (Apenas em Atualizações)

Se for atualização e existir banco de dados:
```bash
if [ -f "$INSTALL_DIR/player.db" ]; then
    cp "$INSTALL_DIR/player.db" "$INSTALL_DIR/player.db.backup"
fi
```

### 3. Cópia de Arquivos do Programa

Copia **apenas** o código fonte, excluindo dados:
```bash
rsync -a --exclude='venv' \
         --exclude='__pycache__' \
         --exclude='songs' \
         --exclude='thumbnails' \
         --exclude='*.db' \
         "$SCRIPT_DIR/" "$INSTALL_DIR/"
```

### 4. Preservação Inteligente de Dados

#### 🗄️ Banco de Dados (player.db)

**Cenário 1: Nova Instalação**
```bash
if [ ! -f "$INSTALL_DIR/player.db" ]; then
    if [ -f "$SCRIPT_DIR/player.db" ]; then
        # Copia DB inicial se existir no source
        cp "$SCRIPT_DIR/player.db" "$INSTALL_DIR/player.db"
    fi
fi
```

**Cenário 2: Atualização**
```bash
elif [ "$IS_UPDATE" = true ] && [ -f "$INSTALL_DIR/player.db.backup" ]; then
    # Restaura backup feito no início
    mv "$INSTALL_DIR/player.db.backup" "$INSTALL_DIR/player.db"
fi
```

**Resultado:**
- ✅ Nova instalação: Copia DB se existir no source
- ✅ Atualização: **NUNCA** sobrescreve, restaura backup
- ✅ DB existente: **SEMPRE** preservado

#### 🎵 Músicas (songs/)

```bash
if [ ! "$(ls -A $INSTALL_DIR/songs 2>/dev/null)" ]; then
    # Diretório vazio ou não existe
    if [ -d "$SCRIPT_DIR/songs" ] && [ "$(ls -A $SCRIPT_DIR/songs 2>/dev/null)" ]; then
        # Copia músicas do source se existirem
        cp -r "$SCRIPT_DIR/songs/"* "$INSTALL_DIR/songs/"
    fi
else
    # Diretório tem conteúdo - PRESERVA
    echo "✓ Músicas existentes preservadas"
fi
```

**Resultado:**
- ✅ Pasta vazia: Copia do source se houver
- ✅ Pasta com músicas: **NUNCA** mexe
- ✅ Mostra quantos arquivos foram preservados

#### 🖼️ Thumbnails (thumbnails/)

```bash
if [ ! "$(ls -A $INSTALL_DIR/thumbnails 2>/dev/null)" ]; then
    # Diretório vazio ou não existe
    if [ -d "$SCRIPT_DIR/thumbnails" ] && [ "$(ls -A $SCRIPT_DIR/thumbnails 2>/dev/null)" ]; then
        # Copia thumbnails do source se existirem
        cp -r "$SCRIPT_DIR/thumbnails/"* "$INSTALL_DIR/thumbnails/"
    fi
else
    # Diretório tem conteúdo - PRESERVA
    echo "✓ Thumbnails existentes preservadas"
fi
```

**Resultado:**
- ✅ Pasta vazia: Copia do source se houver
- ✅ Pasta com thumbnails: **NUNCA** mexe
- ✅ Mostra quantos arquivos foram preservados

## 📊 Matriz de Decisão

| Situação | player.db | songs/ | thumbnails/ |
|----------|-----------|--------|-------------|
| **Nova instalação (destino vazio)** | Copia do source se existir | Copia do source se existir | Copia do source se existir |
| **Atualização (destino tem dados)** | Preserva (restaura backup) | Preserva (não mexe) | Preserva (não mexe) |
| **Atualização (destino vazio)** | Copia do source se existir | Copia do source se existir | Copia do source se existir |

## 🎯 Exemplos Práticos

### Exemplo 1: Primeira Instalação

**Estado inicial:**
```
~/.local/share/player/  (não existe)
```

**Após install.sh:**
```
~/.local/share/player/
├── src/              (copiado)
├── docs/             (copiado)
├── player.py         (copiado)
├── player.db         (copiado do source, se existir)
├── songs/            (copiado do source, se existir)
└── thumbnails/       (copiado do source, se existir)
```

### Exemplo 2: Atualização com Dados

**Estado inicial:**
```
~/.local/share/player/
├── src/              (versão antiga)
├── player.db         (100 músicas cadastradas)
├── songs/            (100 arquivos MP3)
└── thumbnails/       (100 imagens)
```

**Após install.sh:**
```
~/.local/share/player/
├── src/              (ATUALIZADO)
├── docs/             (ATUALIZADO)
├── player.py         (ATUALIZADO)
├── player.db         (PRESERVADO - 100 músicas)
├── songs/            (PRESERVADO - 100 MP3s)
└── thumbnails/       (PRESERVADO - 100 imagens)
```

**Output do script:**
```
✓ Músicas existentes preservadas (100 arquivos)
✓ Thumbnails existentes preservadas (100 arquivos)
```

### Exemplo 3: Atualização Parcial

**Estado inicial:**
```
~/.local/share/player/
├── src/              (versão antiga)
├── player.db         (50 músicas)
├── songs/            (50 MP3s)
└── thumbnails/       (vazio)
```

**Após install.sh:**
```
~/.local/share/player/
├── src/              (ATUALIZADO)
├── player.db         (PRESERVADO - 50 músicas)
├── songs/            (PRESERVADO - 50 MP3s)
└── thumbnails/       (copiado do source, se houver)
```

## 🔒 Garantias de Segurança

### ✅ O Que NUNCA Acontece

1. ❌ Sobrescrever banco de dados existente
2. ❌ Deletar músicas do usuário
3. ❌ Deletar thumbnails do usuário
4. ❌ Perder dados em atualizações

### ✅ O Que SEMPRE Acontece

1. ✅ Código fonte é atualizado
2. ✅ Dados do usuário são preservados
3. ✅ Backup temporário do DB em atualizações
4. ✅ Feedback visual do que foi preservado

## 🧪 Testes de Verificação

### Teste 1: Nova Instalação
```bash
# Limpar instalação anterior
rm -rf ~/.local/share/player ~/.local/bin/player

# Instalar
./install.sh

# Verificar
ls -la ~/.local/share/player/
```

### Teste 2: Atualização Preservando Dados
```bash
# Criar dados fictícios
mkdir -p ~/.local/share/player/songs
touch ~/.local/share/player/songs/test.mp3
touch ~/.local/share/player/player.db

# Atualizar
./install.sh

# Verificar preservação
ls -la ~/.local/share/player/songs/test.mp3  # Deve existir
```

### Teste 3: Atualização com Pasta Vazia
```bash
# Criar instalação com pasta vazia
mkdir -p ~/.local/share/player/{src,songs,thumbnails}

# Atualizar
./install.sh

# Verificar se copiou do source (se houver)
ls -la ~/.local/share/player/songs/
```

## 📝 Logs e Feedback

O script fornece feedback claro:

```bash
→ Configurando diretórios de dados...
→ Copiando banco de dados inicial...           # Se for nova instalação
✓ Músicas existentes preservadas (100 arquivos) # Se já existirem
✓ Thumbnails existentes preservadas (50 arquivos)
```

## 🎓 Resumo

**Regra de Ouro:**
> "Se existir, preserve. Se não existir, copie do source (se houver)."

**Prioridades:**
1. **Segurança dos dados** - Nunca perder informação do usuário
2. **Atualização do código** - Sempre pegar versão mais recente
3. **Experiência suave** - Feedback claro do que aconteceu
