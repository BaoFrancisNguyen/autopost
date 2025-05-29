import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from models import Post, PostStatus


class DatabaseManager:
    """Gestionnaire de base de données pour l'application Instagram"""
    
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
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Table principale des posts
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        description TEXT NOT NULL,
                        hashtags TEXT NOT NULL DEFAULT '',
                        image_prompt TEXT NOT NULL,
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
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        post_id INTEGER,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (post_id) REFERENCES posts (id)
                    )
                ''')
                
                # Index pour optimiser les requêtes
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_status 
                    ON posts(status)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_scheduled_time 
                    ON posts(scheduled_time)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_created_at 
                    ON posts(created_at)
                ''')
                
                conn.commit()
    
    def create_post(self, post: Post) -> int:
        """Crée un nouveau post dans la base de données"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO posts (
                        title, description, hashtags, image_prompt, topic, tone,
                        image_path, scheduled_time, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.title, post.description, post.hashtags, post.image_prompt,
                    post.topic, post.tone, post.image_path, post.scheduled_time,
                    post.status, post.created_at, post.updated_at
                ))
                
                post_id = cursor.lastrowid
                conn.commit()
                
                # Logger l'activité
                self._log_activity(post_id, "CREATED", f"Post créé: {post.title}", conn)
                
                return post_id
    
    def get_post_by_id(self, post_id: int) -> Optional[Post]:
        """Récupère un post par son ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            row = cursor.fetchone()
            
            if row:
                return Post.from_db_row(tuple(row))
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
            
            return [Post.from_db_row(tuple(row)) for row in rows]
    
    def get_posts_by_status(self, status: PostStatus) -> List[Post]:
        """Récupère tous les posts avec un statut donné"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC', 
                (status.value,)
            )
            rows = cursor.fetchall()
            
            return [Post.from_db_row(tuple(row)) for row in rows]
    
    def get_scheduled_posts_ready(self) -> List[Post]:
        """Récupère les posts programmés prêts à être publiés"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM posts 
                WHERE status = 'scheduled' 
                AND scheduled_time <= ? 
                AND image_path IS NOT NULL
                ORDER BY scheduled_time ASC
            ''', (datetime.now(),))
            rows = cursor.fetchall()
            
            return [Post.from_db_row(tuple(row)) for row in rows]
    
    def update_post(self, post: Post) -> bool:
        """Met à jour un post existant"""
        if not post.id:
            return False
        
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                post.updated_at = datetime.now()
                
                cursor.execute('''
                    UPDATE posts SET
                        title = ?, description = ?, hashtags = ?, image_prompt = ?,
                        topic = ?, tone = ?, image_path = ?, scheduled_time = ?,
                        status = ?, updated_at = ?, instagram_post_id = ?, error_message = ?
                    WHERE id = ?
                ''', (
                    post.title, post.description, post.hashtags, post.image_prompt,
                    post.topic, post.tone, post.image_path, post.scheduled_time,
                    post.status, post.updated_at, post.instagram_post_id, 
                    post.error_message, post.id
                ))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self._log_activity(post.id, "UPDATED", f"Post mis à jour", conn)
                
                return affected_rows > 0
    
    def update_post_status(self, post_id: int, status: PostStatus, 
                          error_message: str = None, instagram_post_id: str = None) -> bool:
        """Met à jour le statut d'un post"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE posts SET 
                        status = ?, updated_at = ?, error_message = ?, instagram_post_id = ?
                    WHERE id = ?
                ''', (status.value, datetime.now(), error_message, instagram_post_id, post_id))
                
                affected_rows = cursor.rowcount
                conn.commit()
                
                if affected_rows > 0:
                    self._log_activity(post_id, "STATUS_CHANGED", 
                                     f"Statut changé vers: {status.value}", conn)
                
                return affected_rows > 0
    
    def delete_post(self, post_id: int) -> bool:
        """Supprime un post"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Supprimer d'abord les logs d'activité
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
                'ready_to_publish': 0
            }
            
            # Total des posts
            cursor.execute('SELECT COUNT(*) FROM posts')
            stats['total'] = cursor.fetchone()[0]
            
            # Posts par statut
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM posts 
                GROUP BY status
            ''')
            for status, count in cursor.fetchall():
                if status in stats:
                    stats[status] = count
            
            # Posts prêts à publier
            cursor.execute('''
                SELECT COUNT(*) FROM posts 
                WHERE status = 'scheduled' 
                AND scheduled_time <= ?
                AND image_path IS NOT NULL
            ''', (datetime.now(),))
            stats['ready_to_publish'] = cursor.fetchone()[0]
            
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
    
    def _log_activity(self, post_id: int, action: str, details: str, conn):
        """Log une activité (méthode privée)"""
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (post_id, action, details)
            VALUES (?, ?, ?)
        ''', (post_id, action, details))
    
    def search_posts(self, query: str, limit: int = 20) -> List[Post]:
        """Recherche des posts par titre, description ou hashtags"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_query = f"%{query}%"
            
            cursor.execute('''
                SELECT * FROM posts 
                WHERE title LIKE ? OR description LIKE ? OR hashtags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (search_query, search_query, search_query, limit))
            
            rows = cursor.fetchall()
            return [Post.from_db_row(tuple(row)) for row in rows]
    
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
            return [Post.from_db_row(tuple(row)) for row in rows]