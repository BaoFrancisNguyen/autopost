#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction de la base de données
Corrige les problèmes de migration et recrée la structure
"""

import sqlite3
import os
import shutil
from datetime import datetime


def backup_database(db_path):
    """Crée une sauvegarde de la base de données"""
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_path)
        print(f"✅ Sauvegarde créée: {backup_path}")
        return backup_path
    return None


def recreate_database_schema(db_path):
    """Recrée la structure de base de données corrigée"""
    print(f"🔧 Recréation de la structure de base de données...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Supprimer les anciennes tables si elles existent
            cursor.execute('DROP TABLE IF EXISTS posts_new')
            cursor.execute('DROP TABLE IF EXISTS activity_logs_new')
            
            # Créer la nouvelle table posts avec la structure complète
            cursor.execute('''
                CREATE TABLE posts_new (
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
            
            # Créer la nouvelle table activity_logs
            cursor.execute('''
                CREATE TABLE activity_logs_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts_new (id)
                )
            ''')
            
            # Vérifier si l'ancienne table posts existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            old_table_exists = cursor.fetchone()
            
            if old_table_exists:
                print("📦 Migration des données existantes...")
                
                # Vérifier la structure de l'ancienne table
                cursor.execute("PRAGMA table_info(posts)")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"   Colonnes existantes: {columns}")
                
                # Construire la requête de migration en fonction des colonnes disponibles
                common_columns = []
                if 'id' in columns:
                    common_columns.append('id')
                if 'title' in columns:
                    common_columns.append('title')
                if 'description' in columns:
                    common_columns.append('description')
                if 'hashtags' in columns:
                    common_columns.append('hashtags')
                if 'image_prompt' in columns:
                    common_columns.append('image_prompt')
                elif 'media_prompt' in columns:
                    # Utiliser media_prompt comme image_prompt
                    common_columns.append('media_prompt as image_prompt')
                if 'topic' in columns:
                    common_columns.append('topic')
                if 'tone' in columns:
                    common_columns.append('tone')
                if 'image_path' in columns:
                    common_columns.append('image_path')
                if 'scheduled_time' in columns:
                    common_columns.append('scheduled_time')
                if 'status' in columns:
                    common_columns.append('status')
                if 'created_at' in columns:
                    common_columns.append('created_at')
                if 'updated_at' in columns:
                    common_columns.append('updated_at')
                if 'instagram_post_id' in columns:
                    common_columns.append('instagram_post_id')
                if 'error_message' in columns:
                    common_columns.append('error_message')
                
                # Ajouter des valeurs par défaut pour les colonnes manquantes
                values_mapping = []
                target_columns = []
                
                for col in ['id', 'title', 'description', 'hashtags', 'image_prompt', 'topic', 'tone', 
                           'image_path', 'scheduled_time', 'status', 'created_at', 'updated_at', 
                           'instagram_post_id', 'error_message']:
                    target_columns.append(col)
                    
                    if col in common_columns or any(col in c for c in common_columns):
                        # Trouver la colonne correspondante
                        matching_col = next((c for c in common_columns if col in c), col)
                        values_mapping.append(matching_col)
                    else:
                        # Valeur par défaut
                        if col == 'title':
                            values_mapping.append("'Post sans titre'")
                        elif col == 'description':
                            values_mapping.append("'Description générée automatiquement'")
                        elif col == 'hashtags':
                            values_mapping.append("'#instagram #ai'")
                        elif col == 'image_prompt':
                            values_mapping.append("'Image par défaut'")
                        elif col == 'topic':
                            values_mapping.append("'Général'")
                        elif col == 'tone':
                            values_mapping.append("'engageant'")
                        elif col == 'status':
                            values_mapping.append("'draft'")
                        elif col in ['created_at', 'updated_at']:
                            values_mapping.append("datetime('now')")
                        else:
                            values_mapping.append('NULL')
                
                # Migrer les données
                migration_query = f"""
                INSERT INTO posts_new ({', '.join(target_columns)})
                SELECT {', '.join(values_mapping)}
                FROM posts
                """
                
                print(f"   Requête de migration: {migration_query}")
                cursor.execute(migration_query)
                migrated_count = cursor.rowcount
                print(f"   ✅ {migrated_count} post(s) migré(s)")
                
                # Migrer les logs d'activité si ils existent
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_logs'")
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO activity_logs_new (id, post_id, action, details, timestamp)
                        SELECT id, post_id, action, details, timestamp
                        FROM activity_logs
                    """)
                    print(f"   ✅ Logs d'activité migrés")
                
                # Supprimer les anciennes tables
                cursor.execute('DROP TABLE posts')
                cursor.execute('DROP TABLE IF EXISTS activity_logs')
            else:
                print("📝 Création d'une nouvelle base de données...")
            
            # Renommer les nouvelles tables
            cursor.execute('ALTER TABLE posts_new RENAME TO posts')
            cursor.execute('ALTER TABLE activity_logs_new RENAME TO activity_logs')
            
            # Créer les index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_scheduled_time ON posts(scheduled_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
            
            conn.commit()
            print("✅ Structure de base de données recréée avec succès")
            
    except Exception as e:
        print(f"❌ Erreur lors de la recréation: {e}")
        raise


def verify_database(db_path):
    """Vérifie la structure de la base de données"""
    print("🔍 Vérification de la base de données...")
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Vérifier la table posts
            cursor.execute("PRAGMA table_info(posts)")
            columns = cursor.fetchall()
            print(f"   Table 'posts' - {len(columns)} colonnes:")
            for col in columns:
                print(f"     - {col[1]} ({col[2]})")
            
            # Vérifier le nombre de posts
            cursor.execute("SELECT COUNT(*) FROM posts")
            posts_count = cursor.fetchone()[0]
            print(f"   📊 {posts_count} post(s) dans la base")
            
            # Vérifier la table activity_logs
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='activity_logs'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM activity_logs")
                logs_count = cursor.fetchone()[0]
                print(f"   📊 {logs_count} log(s) d'activité")
            
            print("✅ Vérification terminée")
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False


def main():
    """Point d'entrée principal"""
    db_path = "posts.db"
    
    print("🔧 CORRECTION DE LA BASE DE DONNÉES")
    print("=" * 50)
    
    # 1. Créer une sauvegarde
    backup_path = backup_database(db_path)
    
    try:
        # 2. Recréer la structure
        recreate_database_schema(db_path)
        
        # 3. Vérifier la structure
        if verify_database(db_path):
            print("\n✅ Base de données corrigée avec succès !")
            print("🚀 Vous pouvez maintenant relancer l'application")
            
            if backup_path:
                print(f"💾 Sauvegarde disponible: {backup_path}")
        else:
            raise Exception("Vérification échouée")
            
    except Exception as e:
        print(f"\n❌ Erreur lors de la correction: {e}")
        
        # Restaurer la sauvegarde si possible
        if backup_path and os.path.exists(backup_path):
            print("🔄 Restauration de la sauvegarde...")
            shutil.copy2(backup_path, db_path)
            print("✅ Sauvegarde restaurée")
        
        print("💡 Vous pouvez essayer de supprimer posts.db pour repartir à zéro")
        return False
    
    return True


if __name__ == "__main__":
    main()
