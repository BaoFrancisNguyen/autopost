import sqlite3
import threading
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

# Import conditionnel des modèles
try:
    from models import Post, PostStatus
except ImportError:
    # Classes de secours si models.py a des problèmes
    class PostStatus:
        DRAFT = "draft"
        SCHEDULED = "scheduled"
        PUBLISHED = "published"
        FAILED = "failed"
        PROCESSING = "processing"
    
    class Post:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)


class DatabaseManager:
    """Gestionnaire de base de données pour l'application Instagram - VERSION CORRIGÉE"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager pour les connexions à la base de données"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            # Activer les contraintes de clés étrangères
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires - VERSION CORRIGÉE"""
        print(f"🗄️  Initialisation de la base de données: {self.db_path}")
        
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Vérifier la version actuelle du schéma
                schema_version = self._get_schema_version(cursor)
                print(f"   📊 Version du schéma: {schema_version}")
                
                if schema_version == 0:
                    # Première installation
                    self._create_initial_schema(cursor)
                    self._set_schema_version(cursor, 1)
                    print("   ✅ Schéma initial créé")
                elif schema_version < 2:
                    # Migration nécessaire
                    print("   🔄 Migration du schéma nécessaire...")
                    self._migrate_to_v2(cursor)
                    self._set_schema_version(cursor, 2)
                    print("   ✅ Migration terminée")
                else:
                    print("   ✅ Schéma à jour")
                
                conn.commit()
                print("✅ Base de données initialisée avec succès")
    
    def _get_schema_version(self, cursor) -> int:
        """Récupère la version du schéma de la base de données"""
        try:
            # Vérifier si la table de métadonnées existe
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_metadata'
            """)
            
            if not cursor.fetchone():
                # Vérifier si des tables existent déjà
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='posts'
                """)
                return 1 if cursor.fetchone() else 0
            
            # Récupérer la version
            cursor.execute("SELECT version FROM schema_metadata WHERE key='schema_version'")
            result = cursor.fetchone()
            return result[0] if result else 0
            
        except Exception:
            return 0
    
    def _set_schema_version(self, cursor, version: int):
        """Définit la version du schéma"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_metadata (
                key TEXT PRIMARY KEY,
                version INTEGER,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            INSERT OR REPLACE INTO schema_metadata (key, version, updated_at)
            VALUES ('schema_version', ?, datetime('now'))
        """, (version,))
    
    def _create_initial_schema(self, cursor):
        """Crée le schéma initial de la base de données"""
        
        # Table principale des posts
        cursor.execute('''
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                hashtags TEXT NOT NULL DEFAULT '',
                image_prompt TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL,
                tone TEXT DEFAULT 'engageant',
                image_path TEXT,
                scheduled_time DATETIME,
                status TEXT DEFAULT 'draft',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                instagram_post_id TEXT,
                error_message TEXT
            )
        ''')
        
        # Table des logs d'activité
        cursor.execute('''
            CREATE TABLE activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
            )
        ''')
        
        # Table des paramètres utilisateur
        cursor.execute('''
            CREATE TABLE user_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Créer les index pour optimiser les requêtes
        self._create_indexes(cursor)
    
    def _migrate_to_v2(self, cursor):
        """Migration vers la version 2 du schéma"""
        try:
            # Vérifier si la migration est nécessaire
            cursor.execute("PRAGMA table_info(posts)")
            columns = [row[1] for row in cursor.fetchall()]
            
            print(f"   📋 Colonnes actuelles: {columns}")
            
            # Gérer la migration de media_prompt vers image_prompt
            if 'media_prompt' in columns and 'image_prompt' not in columns:
                print("   🔄 Migration de media_prompt vers image_prompt...")
                cursor.execute("ALTER TABLE posts ADD COLUMN image_prompt TEXT DEFAULT ''")
                cursor.execute("UPDATE posts SET image_prompt = media_prompt WHERE media_prompt IS NOT NULL")
                # Note: On garde media_prompt pour compatibilité, on peut la supprimer plus tard
            elif 'image_prompt' not in columns:
                print("   ➕ Ajout de la colonne image_prompt...")
                cursor.execute("ALTER TABLE posts ADD COLUMN image_prompt TEXT DEFAULT ''")
            
            # Ajouter les colonnes manquantes si nécessaire
            missing_columns = [
                ('description', 'TEXT NOT NULL DEFAULT ""'),
                ('hashtags', 'TEXT NOT NULL DEFAULT ""'),
                ('topic', 'TEXT NOT NULL DEFAULT "général"'),
                ('tone', 'TEXT DEFAULT "engageant"'),
                ('image_path', 'TEXT'),
                ('scheduled_time', 'DATETIME'),
                ('status', 'TEXT DEFAULT "draft"'),
                ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
                ('instagram_post_id', 'TEXT'),
                ('error_message', 'TEXT')
            ]
            
            for col_name, col_def in missing_columns:
                if col_name not in columns:
                    print(f"   ➕ Ajout de la colonne {col_name}...")
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_def}")
            
            # Créer les tables manquantes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Recréer les index
            self._create_indexes(cursor)
            
            # Nettoyer les données si nécessaire
            cursor.execute("UPDATE posts SET status = 'draft' WHERE status IS NULL OR status = ''")
            cursor.execute("UPDATE posts SET tone = 'engageant' WHERE tone IS NULL OR tone = ''")
            cursor.execute("UPDATE posts SET created_at = datetime('now') WHERE created_at IS NULL")
            cursor.execute("UPDATE posts SET updated_at = datetime('now') WHERE updated_at IS NULL")
            
            print("   ✅ Migration terminée avec succès")
            
        except Exception as e:
            print(f"   ❌ Erreur lors de la migration: {e}")
            raise
    
    def _create_indexes(self, cursor):
        """Crée les index pour optimiser les performances"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)",
            "CREATE INDEX IF NOT EXISTS idx_posts_scheduled_time ON posts(scheduled_time)",
            "CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic)",
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_post_id ON activity_logs(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                print(f"   ⚠️  Erreur création index: {e}")
    
    def create_post(self, post: Post) -> int:
        """Crée un nouveau post dans la base de données"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # S'assurer que les champs obligatoires sont présents
                title = getattr(post, 'title', 'Post sans titre')
                description = getattr(post, 'description', '')
                hashtags = getattr(post, 'hashtags', '')
                image_prompt = getattr(post, 'image_prompt', '')
                topic = getattr(post, 'topic', 'général')
                tone = getattr(post, 'tone', 'engageant')
                image_path = getattr(post, 'image_path', None)
                scheduled_time = getattr(post, 'scheduled_time', None)
                status = getattr(post, 'status', 'draft')
                created_at = getattr(post, 'created_at', datetime.now())
                updated_at = getattr(post, 'updated_at', datetime.now())
                
                cursor.execute('''
                    INSERT INTO posts (
                        title, description, hashtags, image_prompt, topic, tone,
                        image_path, scheduled_time, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    title, description, hashtags, image_prompt, topic, tone,
                    image_path, scheduled_time, status, created_at, updated_at
                ))
                
                post_id = cursor.lastrowid
                conn.commit()
                
                # Logger l'activité
                self._log_activity(post_id, "CREATED", f"Post créé: {title}", conn)
                
                return post_id
    
    def get_post_by_id(self, post_id: int) -> Optional[Post]:
        """Récupère un post par son ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_post(row)
            return None
    
    def get_all_posts(self, limit: Optional[int] = None, offset: int = 0) -> List[Post]:
        """Récupère tous les posts avec pagination optionnelle"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM posts ORDER BY created_at DESC'
            params = []
            
            if limit:
                query += ' LIMIT ? OFFSET ?'
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_post(row) for row in rows]
    
    def get_posts_by_status(self, status) -> List[Post]:
        """Récupère tous les posts avec un statut donné"""
        # Gérer les différents types de statut
        if hasattr(status, 'value'):
            status_value = status.value
        else:
            status_value = str(status)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC', 
                (status_value,)
            )
            rows = cursor.fetchall()
            
            return [self._row_to_post(row) for row in rows]
    
    def get_scheduled_posts_ready(self) -> List[Post]:
        """Récupère les posts programmés prêts à être publiés"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE status = 'scheduled' 
                AND scheduled_time <= ? 
                AND (image_path IS NOT NULL OR image_path != '')
                ORDER BY scheduled_time ASC
            ''', (datetime.now(),))
            rows = cursor.fetchall()
            
            return [self._row_to_post(row) for row in rows]
    
    def update_post(self, post: Post) -> bool:
        """Met à jour un post existant"""
        if not hasattr(post, 'id') or not post.id:
            return False
        
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Mise à jour du timestamp
                post.updated_at = datetime.now()
                
                cursor.execute('''
                    UPDATE posts SET
                        title = ?, description = ?, hashtags = ?, image_prompt = ?,
                        topic = ?, tone = ?, image_path = ?, scheduled_time = ?,
                        status = ?, updated_at = ?, instagram_post_id = ?, error_message = ?
                    WHERE id = ?
                ''', (
                    getattr(post, 'title', ''),
                    getattr(post, 'description', ''),
                    getattr(post, 'hashtags', ''),
                    getattr(post, 'image_prompt', ''),
                    getattr(post, 'topic', ''),
                    getattr(post, 'tone', 'engageant'),
                    getattr(post, 'image_path', None),
                    getattr(post, 'scheduled_time', None),
                    getattr(post, 'status', 'draft'),
                    post.updated_at,
                    getattr(post, 'instagram_post_id', None),
                    getattr(post, 'error_message', None),
                    post.id
                ))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self._log_activity(post.id, "UPDATED", f"Post mis à jour", conn)
                
                return affected_rows > 0
    
    def update_post_status(self, post_id: int, status, 
                          error_message: str = None, instagram_post_id: str = None) -> bool:
        """Met à jour le statut d'un post"""
        # Gérer les différents types de statut
        if hasattr(status, 'value'):
            status_value = status.value
        else:
            status_value = str(status)
        
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE posts SET 
                        status = ?, updated_at = ?, error_message = ?, instagram_post_id = ?
                    WHERE id = ?
                ''', (status_value, datetime.now(), error_message, instagram_post_id, post_id))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self._log_activity(post_id, "STATUS_CHANGED", 
                                     f"Statut changé vers: {status_value}", conn)
                
                return affected_rows > 0
    
    def delete_post(self, post_id: int) -> bool:
        """Supprime un post"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Supprimer d'abord les logs d'activité (CASCADE devrait le faire automatiquement)
                cursor.execute('DELETE FROM activity_logs WHERE post_id = ?', (post_id,))
                
                # Ensuite supprimer le post
                cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                return affected_rows > 0
    
    def get_posts_stats(self) -> Dict[str, int]:
        """Récupère les statistiques des posts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {
                'total': 0,
                'draft': 0,
                'scheduled': 0,
                'published': 0,
                'failed': 0,
                'processing': 0,
                'ready_to_publish': 0
            }
            
            # Total des posts
            cursor.execute('SELECT COUNT(*) FROM posts')
            result = cursor.fetchone()
            stats['total'] = result[0] if result else 0
            
            # Posts par statut
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM posts 
                GROUP BY status
            ''')
            for row in cursor.fetchall():
                status = row[0] if row[0] else 'unknown'
                count = row[1] if row[1] else 0
                if status in stats:
                    stats[status] = count
            
            # Posts prêts à publier
            cursor.execute('''
                SELECT COUNT(*) FROM posts 
                WHERE status = 'scheduled' 
                AND scheduled_time <= ?
                AND (image_path IS NOT NULL AND image_path != '')
            ''', (datetime.now(),))
            result = cursor.fetchone()
            stats['ready_to_publish'] = result[0] if result else 0
            
            return stats
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Récupère l'activité récente"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT al.*, p.title as post_title
                FROM activity_logs al
                LEFT JOIN posts p ON al.post_id = p.id
                ORDER BY al.timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'id': row['id'],
                    'post_id': row['post_id'],
                    'post_title': row['post_title'],
                    'action': row['action'],
                    'details': row['details'],
                    'timestamp': row['timestamp']
                })
            
            return activities
    
    def cleanup_old_data(self, days: int = 90):
        """Nettoie les anciennes données"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Supprimer les anciens logs
                cursor.execute('''
                    DELETE FROM activity_logs 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                # Optionnel: supprimer les anciens posts publiés
                # cursor.execute('''
                #     DELETE FROM posts 
                #     WHERE status = 'published' AND created_at < ?
                # ''', (cutoff_date,))
                
                conn.commit()
    
    def search_posts(self, query: str, limit: int = 20) -> List[Post]:
        """Recherche des posts par titre, description ou hashtags"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            
            cursor.execute('''
                SELECT * FROM posts 
                WHERE title LIKE ? OR description LIKE ? OR hashtags LIKE ? OR topic LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (search_query, search_query, search_query, search_query, limit))
            
            rows = cursor.fetchall()
            return [self._row_to_post(row) for row in rows]
    
    def get_posts_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Post]:
        """Récupère les posts dans une plage de dates"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
            ''', (start_date, end_date))
            
            rows = cursor.fetchall()
            return [self._row_to_post(row) for row in rows]
    
    def get_user_setting(self, key: str, default_value: str = None) -> Optional[str]:
        """Récupère un paramètre utilisateur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM user_settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result[0] if result else default_value
    
    def set_user_setting(self, key: str, value: str) -> bool:
        """Définit un paramètre utilisateur"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (key, value, updated_at)
                    VALUES (?, ?, datetime('now'))
                ''', (key, value))
                conn.commit()
                return True
    
    def _row_to_post(self, row) -> Post:
        """Convertit une ligne de base de données en objet Post"""
        try:
            # Import dynamique pour éviter les erreurs circulaires
            from models import Post
            
            return Post(
                id=row['id'],
                title=row['title'] or 'Post sans titre',
                description=row['description'] or '',
                hashtags=row['hashtags'] or '',
                image_prompt=row['image_prompt'] or '',
                topic=row['topic'] or 'général',
                tone=row['tone'] or 'engageant',
                image_path=row['image_path'],
                scheduled_time=datetime.fromisoformat(row['scheduled_time']) if row['scheduled_time'] else None,
                status=row['status'] or 'draft',
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
                instagram_post_id=row['instagram_post_id'],
                error_message=row['error_message']
            )
        except ImportError:
            # Fallback si Post n'est pas disponible
            post = Post()
            for key in row.keys():
                value = row[key]
                if key in ['scheduled_time', 'created_at', 'updated_at'] and value:
                    try:
                        value = datetime.fromisoformat(value)
                    except:
                        value = None
                setattr(post, key, value)
            return post
    
    def _log_activity(self, post_id: int, action: str, details: str, conn):
        """Log une activité (méthode privée)"""
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_logs (post_id, action, details)
                VALUES (?, ?, ?)
            ''', (post_id, action, details))
        except Exception as e:
            print(f"⚠️  Erreur log activité: {e}")
    
    def vacuum_database(self):
        """Optimise la base de données (réorganise et compacte)"""
        with self._lock:
            with self.get_connection() as conn:
                conn.execute('VACUUM')
                print("✅ Base de données optimisée")
    
    def backup_database(self, backup_path: str = None) -> str:
        """Crée une sauvegarde de la base de données"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            print(f"✅ Sauvegarde créée: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Retourne des informations sur la base de données"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Taille du fichier
            file_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            # Version du schéma
            schema_version = self._get_schema_version(cursor)
            
            # Nombre d'enregistrements par table
            cursor.execute("SELECT COUNT(*) FROM posts")
            posts_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            logs_count = cursor.fetchone()[0]
            
            return {
                'file_path': self.db_path,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'schema_version': schema_version,
                'posts_count': posts_count,
                'activity_logs_count': logs_count,
                'created_at': datetime.fromtimestamp(os.path.getctime(self.db_path)) if os.path.exists(self.db_path) else None
            }