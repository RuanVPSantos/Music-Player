# 🔄 Arquitetura de Sincronização - Music Player

## 📋 Visão Geral

Este documento descreve a arquitetura de sincronização multi-plataforma para o Music Player. O sistema foi projetado com **Offline-First**, onde o backend é **opcional** e serve apenas para sincronizar dados entre dispositivos.

## 🏗️ Estrutura Modular do Projeto

O projeto Python TUI foi refatorado em módulos independentes seguindo princípios de POO:

```
player/
├── player.py              # Ponto de entrada da aplicação
├── src/                   # Código fonte modular
│   ├── __init__.py
│   ├── main.py           # PlayerApp - aplicação principal
│   ├── config.py         # Constantes e caminhos (DB_PATH, SONGS_DIR, etc.)
│   ├── models.py         # Dataclasses (Music, Playlist, Tag, SyncPlaylist)
│   ├── repository.py     # Repository - operações de banco de dados
│   ├── audio_player.py   # AudioPlayer - controle de reprodução (ffplay)
│   ├── download_manager.py  # DownloadManager - downloads via yt-dlp
│   ├── sync_manager.py   # SyncManager - sincronização de playlists
│   ├── ui_renderer.py    # UIRenderer - renderização curses
│   ├── handlers.py       # KeyHandlers - tratamento de teclas
│   └── utils.py          # FileUtils - funções utilitárias
├── docs/                  # Documentação
│   ├── README.md
│   ├── SYNC_ARCHITECTURE.md
│   └── MODULARIDADE_EXEMPLO.md
├── songs/                 # Arquivos de música (MP3)
├── thumbnails/            # Miniaturas
└── player.db             # Banco de dados SQLite
```

### Benefícios da Modularização
- ✅ **Baixo acoplamento**: Cada módulo pode ser substituído independentemente
- ✅ **Alta coesão**: Responsabilidades bem definidas
- ✅ **Testabilidade**: Classes podem ser testadas isoladamente
- ✅ **Manutenibilidade**: Fácil localizar e modificar funcionalidades

## � Princípios Fundamentais

### ✅ Offline-First
- **App funciona 100% sem internet**
- Backend é um recurso opcional
- Falhas de sincronização não afetam funcionalidade
- Dados locais sempre têm prioridade

### ✅ Multi-Plataforma
- Python TUI (desktop Linux)
- React Native (iOS/Android)
- Next.js (Web)
- Mesma lógica de sincronização em todos

## 🗄️ Estrutura de Dados

### **Banco Local (SQLite/IndexedDB)**

Já implementado no módulo `repository.py` (classe `Repository`):

```sql
-- Configuração de sincronização (opcional)
CREATE TABLE sync_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled BOOLEAN DEFAULT 0,
    backend_url TEXT,
    api_key TEXT,
    last_sync TIMESTAMP
);

-- Queue de mudanças locais para sincronizar
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,  -- 'tag', 'playlist', 'sync_playlist', 'music_tag'
    entity_id TEXT,
    action TEXT,       -- 'create', 'update', 'delete'
    payload TEXT,      -- JSON com dados
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    synced BOOLEAN DEFAULT 0
);

-- Playlists de sincronização (URLs do YouTube)
CREATE TABLE sync_playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    synced_at TIMESTAMP NULL  -- NULL = nunca sincronizado
);

-- Outras tabelas já existentes com suporte a sync
-- musics, tags, playlists, etc.
```

## 🏗️ Backend (A Implementar)

### **Stack Recomendada**
- **Runtime:** Node.js 20+ ou Python FastAPI
- **Database:** PostgreSQL 15+
- **Auth:** JWT + Refresh Tokens
- **Storage:** S3/MinIO (opcional, para streaming)
- **Deploy:** Docker + Railway/Render/Fly.io

### **Schema do Backend**

```sql
-- Usuários
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Playlists de sincronização (compartilhadas)
CREATE TABLE sync_playlists (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, url)
);

-- Cache de metadados (compartilhado entre usuários)
CREATE TABLE music_metadata_cache (
    youtube_id VARCHAR(50) PRIMARY KEY,
    title TEXT,
    url TEXT,
    duration INTEGER,
    thumbnail_url TEXT,
    cached_at TIMESTAMP DEFAULT NOW()
);

-- Tags do usuário
CREATE TABLE user_tags (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Relação música-tag do usuário
CREATE TABLE user_music_tags (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    music_youtube_id VARCHAR(50),
    tag_id UUID REFERENCES user_tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, music_youtube_id, tag_id)
);

-- Playlists personalizadas do usuário
CREATE TABLE user_playlists (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE user_playlist_items (
    playlist_id UUID REFERENCES user_playlists(id) ON DELETE CASCADE,
    music_youtube_id VARCHAR(50),
    position INTEGER,
    added_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (playlist_id, music_youtube_id)
);
```

### **API Endpoints**

```typescript
// Autenticação
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
POST   /api/auth/logout

// Sync Playlists (URLs do YouTube)
GET    /api/sync-playlists
POST   /api/sync-playlists
PUT    /api/sync-playlists/:id
DELETE /api/sync-playlists/:id

// Metadados (cache compartilhado)
GET    /api/music/metadata/:youtubeId
POST   /api/music/metadata/batch  // Busca múltiplos

// Tags
GET    /api/tags
POST   /api/tags
PUT    /api/tags/:id
DELETE /api/tags/:id

// Relação música-tag
POST   /api/music/:youtubeId/tags/:tagId
DELETE /api/music/:youtubeId/tags/:tagId

// Playlists personalizadas
GET    /api/playlists
POST   /api/playlists
PUT    /api/playlists/:id
DELETE /api/playlists/:id
POST   /api/playlists/:id/items
DELETE /api/playlists/:id/items/:youtubeId

// Sincronização (push/pull)
POST   /api/sync/push    // Cliente envia mudanças
GET    /api/sync/pull    // Cliente puxa mudanças desde timestamp
```

## 🔄 Fluxo de Sincronização

### **1. Cliente Python (TUI)**

**Status:** ✅ Parcialmente implementado

O módulo `sync_manager.py` já existe e implementa a sincronização de playlists do YouTube via yt-dlp.

**Estrutura atual:**
```python
# sync_manager.py
class SyncManager:
    """Manages synchronization of playlists from external sources."""
    
    def __init__(self, status_queue: queue.Queue, download_manager: DownloadManager):
        self.status_queue = status_queue
        self.download_manager = download_manager

    def sync_playlists_async(self) -> None:
        """Start playlist synchronization in background thread."""
        # Implementa sincronização de URLs do YouTube
        # Baixa metadados e delega downloads para DownloadManager
```

**Integração no app:**
```python
# src/main.py - classe PlayerApp
def __init__(self, stdscr: curses.window):
    # ...
    self.download_manager = DownloadManager(self.status_queue)
    self.sync_manager = SyncManager(self.status_queue, self.download_manager)
    # ...
    self._auto_sync()  # Sincroniza automaticamente no startup
```

**Para adicionar sync com backend (futuro):**

Expandir `sync_manager.py` com métodos adicionais:

```python
# Adicionar ao sync_manager.py
class SyncManager:
    # ... métodos existentes ...
    
    def _load_backend_config(self) -> dict:
        """Carrega configuração de sync com backend."""
        row = self.repo.conn.execute(
            "SELECT enabled, backend_url, api_key, last_sync FROM sync_config WHERE id = 1"
        ).fetchone()
        
        if row:
            return {
                'enabled': bool(row[0]),
                'backend_url': row[1],
                'api_key': row[2],
                'last_sync': row[3]
            }
        return {'enabled': False}
    
    def sync_with_backend(self) -> None:
        """Sincroniza tags e playlists personalizadas com backend."""
        config = self._load_backend_config()
        if not config.get('enabled'):
            return
        
        try:
            import requests
            
            # Push mudanças locais
            self._push_queue(config)
            
            # Pull mudanças remotas
            self._pull_changes(config)
            
        except Exception as e:
            import logging
            logging.debug(f"Backend sync failed: {e}")
    
    # ... implementar _push_queue e _pull_changes ...
```

### **2. Cliente React Native**

Criar `src/services/sync.service.ts`:

```typescript
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { db } from '../db/sqlite';

interface SyncConfig {
  enabled: boolean;
  backendUrl?: string;
  apiKey?: string;
  lastSync?: string;
}

export class SyncService {
  private config: SyncConfig | null = null;

  async init() {
    const configStr = await AsyncStorage.getItem('sync_config');
    this.config = configStr ? JSON.parse(configStr) : { enabled: false };
  }

  isEnabled(): boolean {
    return this.config?.enabled && !!this.config?.backendUrl;
  }

  async trySync(): Promise<void> {
    if (!this.isEnabled()) return;

    try {
      // Verifica conexão
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) return;

      // Push & Pull
      await this.pushQueue();
      await this.pullChanges();

      // Atualiza timestamp
      this.config!.lastSync = new Date().toISOString();
      await AsyncStorage.setItem('sync_config', JSON.stringify(this.config));
    } catch (error) {
      console.debug('Sync failed:', error);
    }
  }

  async pushQueue(): Promise<void> {
    const queue = await db.getAllFrom('sync_queue', { synced: 0 });

    for (const item of queue) {
      try {
        const response = await fetch(`${this.config!.backendUrl}/api/sync/push`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config!.apiKey}`,
          },
          body: JSON.stringify({
            entity_type: item.entity_type,
            entity_id: item.entity_id,
            action: item.action,
            payload: JSON.parse(item.payload),
          }),
        });

        if (response.ok) {
          await db.update('sync_queue', item.id, { synced: 1 });
        }
      } catch {
        continue;
      }
    }
  }

  async pullChanges(): Promise<void> {
    try {
      const response = await fetch(
        `${this.config!.backendUrl}/api/sync/pull?since=${this.config!.lastSync || '1970-01-01'}`,
        {
          headers: {
            'Authorization': `Bearer ${this.config!.apiKey}`,
          },
        }
      );

      if (response.ok) {
        const changes = await response.json();
        await this.mergeChanges(changes);
      }
    } catch {
      // Falha silenciosa
    }
  }

  async mergeChanges(changes: any): Promise<void> {
    // Merge sync_playlists
    for (const sp of changes.sync_playlists || []) {
      await db.insertOrReplace('sync_playlists', sp);
    }

    // Merge tags
    for (const tag of changes.tags || []) {
      await db.insertOrIgnore('tags', tag);
    }
  }

  async queueChange(entityType: string, entityId: string, action: string, payload: any): Promise<void> {
    if (!this.isEnabled()) return;

    await db.insert('sync_queue', {
      entity_type: entityType,
      entity_id: entityId,
      action,
      payload: JSON.stringify(payload),
      synced: 0,
    });
  }
}
```

### **3. Cliente Next.js (Web)**

Criar `src/lib/sync.ts`:

```typescript
import { openDB, DBSchema, IDBPDatabase } from 'idb';

interface SyncConfig {
  enabled: boolean;
  backendUrl?: string;
  apiKey?: string;
  lastSync?: string;
}

interface MusicPlayerDB extends DBSchema {
  sync_config: { key: number; value: SyncConfig };
  sync_queue: { key: number; value: any; indexes: { 'synced': number } };
  sync_playlists: { key: string; value: any };
  tags: { key: string; value: any };
}

export class SyncManager {
  private db!: IDBPDatabase<MusicPlayerDB>;
  private config: SyncConfig | null = null;

  async init() {
    this.db = await openDB<MusicPlayerDB>('music-player', 1, {
      upgrade(db) {
        db.createObjectStore('sync_config', { keyPath: 'id' });
        const queueStore = db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
        queueStore.createIndex('synced', 'synced');
        db.createObjectStore('sync_playlists', { keyPath: 'id' });
        db.createObjectStore('tags', { keyPath: 'id' });
      },
    });

    this.config = await this.db.get('sync_config', 1) || { enabled: false };
  }

  isEnabled(): boolean {
    return this.config?.enabled && !!this.config?.backendUrl;
  }

  async trySync(): Promise<void> {
    if (!this.isEnabled() || !navigator.onLine) return;

    try {
      await this.pushQueue();
      await this.pullChanges();

      this.config!.lastSync = new Date().toISOString();
      await this.db.put('sync_config', { id: 1, ...this.config! });
    } catch (error) {
      console.debug('Sync failed:', error);
    }
  }

  async pushQueue(): Promise<void> {
    const queue = await this.db.getAllFromIndex('sync_queue', 'synced', 0);

    for (const item of queue) {
      try {
        const response = await fetch(`${this.config!.backendUrl}/api/sync/push`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config!.apiKey}`,
          },
          body: JSON.stringify(item),
        });

        if (response.ok) {
          await this.db.delete('sync_queue', item.id);
        }
      } catch {
        continue;
      }
    }
  }

  async pullChanges(): Promise<void> {
    try {
      const response = await fetch(
        `${this.config!.backendUrl}/api/sync/pull?since=${this.config!.lastSync || '1970-01-01'}`,
        {
          headers: {
            'Authorization': `Bearer ${this.config!.apiKey}`,
          },
        }
      );

      if (response.ok) {
        const changes = await response.json();
        await this.mergeChanges(changes);
      }
    } catch {
      // Falha silenciosa
    }
  }

  async mergeChanges(changes: any): Promise<void> {
    for (const sp of changes.sync_playlists || []) {
      await this.db.put('sync_playlists', sp);
    }

    for (const tag of changes.tags || []) {
      await this.db.put('tags', tag);
    }
  }
}
```

## 🚀 Implementação do Backend

### **Exemplo com Node.js + Express**

```typescript
// src/routes/sync.ts
import { Router } from 'express';
import { authenticate } from '../middleware/auth';
import { db } from '../db';

const router = Router();

router.post('/push', authenticate, async (req, res) => {
  const { entity_type, entity_id, action, payload } = req.body;
  const userId = req.user.id;

  try {
    switch (entity_type) {
      case 'sync_playlist':
        if (action === 'create' || action === 'update') {
          await db.query(
            `INSERT INTO sync_playlists (id, user_id, name, url, updated_at)
             VALUES ($1, $2, $3, $4, NOW())
             ON CONFLICT (id) DO UPDATE SET name = $3, url = $4, updated_at = NOW()`,
            [entity_id, userId, payload.name, payload.url]
          );
        } else if (action === 'delete') {
          await db.query('DELETE FROM sync_playlists WHERE id = $1 AND user_id = $2', [entity_id, userId]);
        }
        break;

      case 'tag':
        if (action === 'create') {
          await db.query(
            `INSERT INTO user_tags (id, user_id, name) VALUES ($1, $2, $3)
             ON CONFLICT DO NOTHING`,
            [entity_id, userId, payload.name]
          );
        } else if (action === 'delete') {
          await db.query('DELETE FROM user_tags WHERE id = $1 AND user_id = $2', [entity_id, userId]);
        }
        break;

      // Outros tipos...
    }

    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ error: 'Sync failed' });
  }
});

router.get('/pull', authenticate, async (req, res) => {
  const { since } = req.query;
  const userId = req.user.id;

  try {
    const [syncPlaylists, tags] = await Promise.all([
      db.query(
        'SELECT * FROM sync_playlists WHERE user_id = $1 AND updated_at > $2',
        [userId, since || '1970-01-01']
      ),
      db.query(
        'SELECT * FROM user_tags WHERE user_id = $1 AND created_at > $2',
        [userId, since || '1970-01-01']
      ),
    ]);

    res.json({
      sync_playlists: syncPlaylists.rows,
      tags: tags.rows,
    });
  } catch (error) {
    res.status(500).json({ error: 'Pull failed' });
  }
});

export default router;
```

## 📱 Configuração pelo Usuário

### **Python TUI - Adicionar seção "Config"**

Para adicionar configuração de backend, criar método em `handlers.py`:

```python
# handlers.py - classe KeyHandlers
def handle_config_key(self, key: int) -> str:
    """Handle keys in config section."""
    if key == ord("s"):
        enabled = self.ui.prompt("Habilitar sync com backend? (s/n): ").lower() == 's'
        
        if enabled:
            backend_url = self.ui.prompt("URL do backend: ")
            api_key = self.ui.prompt("API Key: ")
            
            self.repo.conn.execute(
                """INSERT OR REPLACE INTO sync_config (id, enabled, backend_url, api_key)
                   VALUES (1, 1, ?, ?)""",
                (backend_url, api_key)
            )
            self.repo.conn.commit()
            
            return "Sync com backend habilitado!"
        else:
            self.repo.conn.execute("UPDATE sync_config SET enabled = 0 WHERE id = 1")
            self.repo.conn.commit()
            return "Sync com backend desabilitado."
    
    return ""
```

E adicionar no `src/main.py`:

```python
# src/main.py - classe PlayerApp
MENU = ["Músicas", "Playlists", "Tags", "Busca", "Sync URLs", "Sincronizar", "Config", "Sair"]

# No método handle_section_keys:
elif self.section == 6:  # Config
    status = self.handlers.handle_config_key(key)
    if status:
        self.status = status
```

## 🎯 Checklist de Implementação

### **Fase 1: Backend**
- [ ] Criar projeto Node.js/FastAPI
- [ ] Configurar PostgreSQL
- [ ] Implementar autenticação (JWT)
- [ ] Criar endpoints de sync
- [ ] Deploy em Railway/Render

### **Fase 2: Python TUI**
- [x] Adicionar tabelas sync_config e sync_queue (em `src/repository.py`)
- [x] Criar sync_manager.py (sincronização de playlists YouTube)
- [x] Integrar no PlayerApp.__init__ (em `src/main.py`)
- [x] Refatorar código em módulos independentes
  - [x] `src/config.py` - Constantes e caminhos
  - [x] `src/models.py` - Dataclasses
  - [x] `src/repository.py` - Acesso a dados
  - [x] `src/audio_player.py` - Reprodução de áudio
  - [x] `src/download_manager.py` - Downloads
  - [x] `src/sync_manager.py` - Sincronização
  - [x] `src/ui_renderer.py` - Interface
  - [x] `src/handlers.py` - Tratamento de teclas
  - [x] `src/utils.py` - Utilitários
  - [x] `src/main.py` - Aplicação principal
- [x] Organizar em estrutura de diretórios (src/, docs/)
- [ ] Adicionar seção Config no menu (para sync com backend)
- [ ] Expandir sync_manager.py com sync de backend
- [ ] Testar sync com backend

### **Fase 3: React Native**
- [ ] Configurar SQLite
- [ ] Implementar SyncService
- [ ] Integrar com UI
- [ ] Testar offline-first

### **Fase 4: Next.js**
- [ ] Configurar IndexedDB
- [ ] Implementar SyncManager
- [ ] Integrar com UI
- [ ] Testar streaming

## 🔐 Segurança

- **JWT com refresh tokens**
- **HTTPS obrigatório**
- **Rate limiting**
- **Validação de entrada**
- **API Keys por usuário**

## 📊 Monitoramento

- **Logs de sync (sucesso/falha)**
- **Métricas de latência**
- **Alertas de falhas**
- **Dashboard de uso**

---

**Pronto para implementar quando você quiser! 🚀**
