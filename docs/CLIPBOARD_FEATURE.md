# Funcionalidade de Clipboard - Copiar URL

## 📋 Visão Geral

O Player TUI agora permite copiar a URL da música selecionada diretamente para o clipboard do sistema com um simples atalho de teclado.

## ⌨️ Atalho

**Tecla:** `Y` (maiúscula ou minúscula)

**Ação:** Copia a URL da música selecionada para o clipboard

## 🎯 Como Usar

### Passo 1: Selecionar Música

Navegue até a música desejada usando `↑↓` ou `j/k`

### Passo 2: Pressionar Y

Aperte a tecla `Y` para copiar a URL

### Passo 3: Colar

Use `Ctrl+V` (ou `Cmd+V` no macOS) para colar a URL em qualquer aplicativo

## 💡 Casos de Uso

### 1. Compartilhar Música
```
1. Selecione a música
2. Aperte Y
3. Cole no WhatsApp/Telegram/Discord
4. Compartilhe com amigos!
```

### 2. Backup de URLs
```
1. Selecione a música
2. Aperte Y
3. Cole em arquivo de texto
4. Salve lista de URLs
```

### 3. Download Manual
```
1. Selecione a música
2. Aperte Y
3. Cole no navegador
4. Baixe manualmente se necessário
```

## 🔧 Compatibilidade de Clipboard

O player detecta automaticamente qual ferramenta de clipboard usar:

### Linux (X11)
- **xclip** (preferencial)
- **xsel** (alternativa)

### Linux (Wayland)
- **wl-copy**

### macOS
- **pbcopy** (nativo)

## 📦 Instalação de Ferramentas

### Ubuntu/Debian
```bash
# Opção 1: xclip (recomendado)
sudo apt install xclip

# Opção 2: xsel
sudo apt install xsel
```

### Fedora
```bash
sudo dnf install xclip
```

### Arch
```bash
sudo pacman -S xclip
```

### Wayland
```bash
sudo apt install wl-clipboard
```

### macOS
```bash
# pbcopy já vem instalado
# Nada a fazer!
```

## 🎨 Feedback Visual

Quando você aperta `Y`, o player mostra:

### Sucesso
```
URL copiada: https://www.youtube.com/watch?v=dQw4w9WgXcQ...
```

### Sem Clipboard
```
Clipboard não disponível. URL: https://www.youtube.com/watch?v=...
```
(Mostra a URL completa na tela)

### Música Sem URL
```
Esta música não tem URL.
```

### Nenhuma Música Selecionada
```
Selecione uma música.
```

## 🔍 Implementação Técnica

### Detecção de Ferramenta

```python
# Ordem de preferência
if subprocess.run(["which", "xclip"], capture_output=True).returncode == 0:
    clipboard_cmd = ["xclip", "-selection", "clipboard"]
elif subprocess.run(["which", "xsel"], capture_output=True).returncode == 0:
    clipboard_cmd = ["xsel", "--clipboard", "--input"]
elif subprocess.run(["which", "wl-copy"], capture_output=True).returncode == 0:
    clipboard_cmd = ["wl-copy"]
elif subprocess.run(["which", "pbcopy"], capture_output=True).returncode == 0:
    clipboard_cmd = ["pbcopy"]
```

### Cópia para Clipboard

```python
subprocess.run(clipboard_cmd, input=music.url.encode(), check=True)
```

## 🐛 Solução de Problemas

### Problema: "Clipboard não disponível"

**Causa:** Nenhuma ferramenta de clipboard instalada

**Solução:**
```bash
sudo apt install xclip
```

### Problema: Não funciona no Wayland

**Causa:** Usando xclip/xsel no Wayland

**Solução:**
```bash
sudo apt install wl-clipboard
```

### Problema: "Esta música não tem URL"

**Causa:** Música foi adicionada manualmente sem URL

**Solução:** Músicas baixadas via sync têm URL automaticamente. Músicas adicionadas manualmente não têm.

## 📊 Comparação de Ferramentas

| Ferramenta | Ambiente | Velocidade | Compatibilidade |
|------------|----------|------------|-----------------|
| **xclip** | X11 | Rápida | ✅ Excelente |
| **xsel** | X11 | Rápida | ✅ Boa |
| **wl-copy** | Wayland | Rápida | ✅ Excelente |
| **pbcopy** | macOS | Rápida | ✅ Nativa |

## 🎓 Dicas

### Dica 1: Verificar Clipboard
```bash
# Linux (X11)
xclip -selection clipboard -o

# Linux (Wayland)
wl-paste

# macOS
pbpaste
```

### Dica 2: Copiar Múltiplas URLs
```
1. Abra editor de texto
2. Para cada música:
   - Selecione música
   - Aperte Y
   - Cole no editor (Ctrl+V)
   - Nova linha
3. Salve arquivo
```

### Dica 3: Criar Playlist Externa
```bash
# Copie URLs e salve em arquivo
cat > minhas-musicas.txt << EOF
https://youtube.com/watch?v=...
https://youtube.com/watch?v=...
https://youtube.com/watch?v=...
EOF
```

## 🔐 Segurança

- ✅ Não envia dados para internet
- ✅ Copia apenas para clipboard local
- ✅ Não armazena histórico de clipboard
- ✅ Processo isolado e seguro

## 📝 Changelog

### v1.0 - Implementação Inicial
- ✅ Atalho `Y` para copiar URL
- ✅ Suporte multi-plataforma (Linux/macOS)
- ✅ Detecção automática de ferramenta
- ✅ Feedback visual de sucesso/erro
- ✅ Tratamento de erros robusto

## 🎉 Resumo

**Atalho:** `Y`  
**Ação:** Copia URL da música para clipboard  
**Requisito:** xclip, xsel, wl-copy ou pbcopy  
**Plataformas:** Linux (X11/Wayland), macOS  

**Experimente agora!** Selecione uma música e aperte `Y`! 📋
