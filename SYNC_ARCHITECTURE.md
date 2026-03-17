# 🔄 Arquitetura de Sincronização - Music Player

## 📋 Visão Geral

Este documento descreve a arquitetura de sincronização multi-plataforma para o Music Player. O sistema foi projetado com **Offline-First**, onde o backend é **opcional** e serve apenas para sincronizar dados entre dispositivos.

## 🎯 Princípios Fundamentais

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

Já implementado no `app.py`:

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

Criar arquivo `sync_manager.py`:

```python
import requests
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

class SyncManager:
    def __init__(self, repo):
        self.repo = repo
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Carrega configuração de sync do banco."""
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
    
    def is_enabled(self) -> bool:
        """Verifica se sync está habilitado."""
        return self.config.get('enabled', False) and self.config.get('backend_url')
    
    def try_sync(self) -> None:
        """Tenta sincronizar. Falha silenciosa se offline."""
        if not self.is_enabled():
            return
        
        try:
            # Verifica conexão
            response = requests.get(
                f"{self.config['backend_url']}/api/health",
                timeout=3
            )
            if not response.ok:
                return
            
            # Push mudanças locais
            self.push_queue()
            
            # Pull mudanças remotas
            self.pull_changes()
            
            # Atualiza timestamp
            self.repo.conn.execute(
                "UPDATE sync_config SET last_sync = ? WHERE id = 1",
                (datetime.now().isoformat(),)
            )
            self.repo.conn.commit()
        except Exception as e:
            # Falha silenciosa
            import logging
            logging.debug(f"Sync failed: {e}")
    
    def push_queue(self) -> None:
        """Envia mudanças locais para o backend."""
        queue = self.repo.conn.execute(
            "SELECT id, entity_type, entity_id, action, payload FROM sync_queue WHERE synced = 0"
        ).fetchall()
        
        for item in queue:
            item_id, entity_type, entity_id, action, payload = item
            
            try:
                response = requests.post(
                    f"{self.config['backend_url']}/api/sync/push",
                    json={
                        'entity_type': entity_type,
                        'entity_id': entity_id,
                        'action': action,
                        'payload': json.loads(payload)
                    },
                    headers={'Authorization': f"Bearer {self.config['api_key']}"},
                    timeout=10
                )
                
                if response.ok:
                    self.repo.conn.execute(
                        "UPDATE sync_queue SET synced = 1 WHERE id = ?",
                        (item_id,)
                    )
                    self.repo.conn.commit()
            except:
                continue
    
    def pull_changes(self) -> None:
        """Puxa mudanças do backend."""
        try:
            response = requests.get(
                f"{self.config['backend_url']}/api/sync/pull",
                params={'since': self.config.get('last_sync', '1970-01-01')},
                headers={'Authorization': f"Bearer {self.config['api_key']}"},
                timeout=10
            )
            
            if response.ok:
                changes = response.json()
                self._merge_changes(changes)
        except:
            pass
    
    def _merge_changes(self, changes: dict) -> None:
        """Merge mudanças remotas com dados locais."""
        # Sync playlists
        for sp in changes.get('sync_playlists', []):
            self.repo.conn.execute(
                """INSERT OR REPLACE INTO sync_playlists (id, name, url, synced_at)
                   VALUES (?, ?, ?, ?)""",
                (sp['id'], sp['name'], sp['url'], datetime.now().isoformat())
            )
        
        # Tags
        for tag in changes.get('tags', []):
            self.repo.conn.execute(
                """INSERT OR IGNORE INTO tags (id, name)
                   VALUES (?, ?)""",
                (tag['id'], tag['name'])
            )
        
        self.repo.conn.commit()
    
    def queue_change(self, entity_type: str, entity_id: str, action: str, payload: dict) -> None:
        """Adiciona mudança à queue de sync."""
        if not self.is_enabled():
            return
        
        self.repo.conn.execute(
            """INSERT INTO sync_queue (entity_type, entity_id, action, payload)
               VALUES (?, ?, ?, ?)""",
            (entity_type, entity_id, action, json.dumps(payload))
        )
        self.repo.conn.commit()
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

```python
def handle_config_key(self, key: int) -> None:
    if key == ord("s"):
        enabled = self.prompt("Habilitar sync? (s/n): ").lower() == 's'
        
        if enabled:
            backend_url = self.prompt("URL do backend: ")
            api_key = self.prompt("API Key: ")
            
            self.repo.conn.execute(
                """INSERT OR REPLACE INTO sync_config (id, enabled, backend_url, api_key)
                   VALUES (1, 1, ?, ?)""",
                (backend_url, api_key)
            )
            self.repo.conn.commit()
            
            self.status = "Sync habilitado!"
            threading.Thread(target=self.sync_manager.try_sync, daemon=True).start()
        else:
            self.repo.conn.execute("UPDATE sync_config SET enabled = 0 WHERE id = 1")
            self.repo.conn.commit()
            self.status = "Sync desabilitado."
```

## 🎯 Checklist de Implementação

### **Fase 1: Backend**
- [ ] Criar projeto Node.js/FastAPI
- [ ] Configurar PostgreSQL
- [ ] Implementar autenticação (JWT)
- [ ] Criar endpoints de sync
- [ ] Deploy em Railway/Render

### **Fase 2: Python TUI**
- [x] Adicionar tabelas sync_config e sync_queue
- [ ] Criar sync_manager.py
- [ ] Integrar no App.__init__
- [ ] Adicionar seção Config no menu
- [ ] Testar sync

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
