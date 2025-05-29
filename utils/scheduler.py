import time
import threading
from datetime import datetime, timedelta
from typing import List, Callable, Optional
import logging

from database import DatabaseManager
from services.instagram_api import InstagramPublisher
from models import Post, PostStatus, PublicationResult


class PostScheduler:
    """Gestionnaire de programmation et publication automatique des posts"""
    
    def __init__(self, db_manager: DatabaseManager, 
                 instagram_publisher: InstagramPublisher = None):
        """
        Initialise le scheduler
        
        Args:
            db_manager: Gestionnaire de base de données
            instagram_publisher: Publisher Instagram (optionnel)
        """
        self.db_manager = db_manager
        self.instagram_publisher = instagram_publisher
        self.is_running = False
        self.thread = None
        self.check_interval = 60  # Vérifier toutes les 60 secondes
        self.logger = logging.getLogger(__name__)
        
        # Callbacks pour les événements
        self.on_post_published = None
        self.on_post_failed = None
        self.on_scheduler_error = None
    
    def start(self):
        """Démarre le scheduler en arrière-plan"""
        if self.is_running:
            self.logger.warning("Le scheduler est déjà en cours d'exécution")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info("📅 Scheduler démarré")
    
    def stop(self):
        """Arrête le scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self.logger.info("📅 Scheduler arrêté")
    
    def _run_scheduler(self):
        """Boucle principale du scheduler"""
        self.logger.info("🔄 Boucle de scheduler démarrée")
        
        while self.is_running:
            try:
                self._check_and_publish_scheduled_posts()
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Erreur dans le scheduler: {e}")
                if self.on_scheduler_error:
                    self.on_scheduler_error(e)
                
                # Attendre un peu plus longtemps en cas d'erreur
                time.sleep(self.check_interval * 2)
    
    def _check_and_publish_scheduled_posts(self):
        """Vérifie et publie les posts programmés prêts"""
        try:
            # Récupérer les posts prêts à être publiés
            ready_posts = self.db_manager.get_scheduled_posts_ready()
            
            if not ready_posts:
                return
            
            self.logger.info(f"📋 {len(ready_posts)} post(s) prêt(s) pour publication")
            
            for post in ready_posts:
                self._publish_single_post(post)
                
                # Petite pause entre les publications pour éviter les limites de taux
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la vérification des posts: {e}")
    
    def _publish_single_post(self, post: Post):
        """Publie un seul post"""
        try:
            self.logger.info(f"📸 Publication du post: {post.title}")
            
            # Marquer comme en cours de traitement
            self.db_manager.update_post_status(
                post.id, PostStatus.PROCESSING
            )
            
            if not self.instagram_publisher:
                raise Exception("Publisher Instagram non configuré")
            
            if not post.image_path or not post.can_be_published():
                raise Exception("Post non prêt pour publication (image ou contenu manquant)")
            
            # Publier sur Instagram
            caption = post.get_full_caption()
            result = self.instagram_publisher.publish_post(post.image_path, caption)
            
            if result.success:
                # Mise à jour du statut en succès
                self.db_manager.update_post_status(
                    post.id, 
                    PostStatus.PUBLISHED,
                    instagram_post_id=result.instagram_post_id
                )
                
                self.logger.info(f"✅ Post publié avec succès: {post.title}")
                
                # Callback de succès
                if self.on_post_published:
                    self.on_post_published(post, result)
                    
            else:
                # Mise à jour du statut en échec
                self.db_manager.update_post_status(
                    post.id, 
                    PostStatus.FAILED,
                    error_message=result.error_message
                )
                
                self.logger.error(f"❌ Échec publication: {post.title} - {result.error_message}")
                
                # Callback d'échec
                if self.on_post_failed:
                    self.on_post_failed(post, result.error_message)
                
        except Exception as e:
            error_msg = f"Erreur publication post {post.id}: {str(e)}"
            self.logger.error(error_msg)
            
            # Marquer le post comme échoué
            self.db_manager.update_post_status(
                post.id, 
                PostStatus.FAILED,
                error_message=error_msg
            )
            
            if self.on_post_failed:
                self.on_post_failed(post, error_msg)
    
    def schedule_post(self, post: Post, publish_time: datetime) -> bool:
        """Programme un post pour publication"""
        try:
            post.scheduled_time = publish_time
            post.status = PostStatus.SCHEDULED.value
            
            success = self.db_manager.update_post(post)
            
            if success:
                self.logger.info(f"📅 Post programmé: {post.title} pour {publish_time}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur programmation post: {e}")
            return False
    
    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Annule la programmation d'un post"""
        try:
            success = self.db_manager.update_post_status(post_id, PostStatus.DRAFT)
            
            if success:
                self.logger.info(f"📅 Programmation annulée pour le post {post_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur annulation programmation: {e}")
            return False
    
    def reschedule_post(self, post_id: int, new_time: datetime) -> bool:
        """Reprogramme un post"""
        try:
            post = self.db_manager.get_post_by_id(post_id)
            if not post:
                return False
            
            post.scheduled_time = new_time
            post.status = PostStatus.SCHEDULED.value
            
            success = self.db_manager.update_post(post)
            
            if success:
                self.logger.info(f"📅 Post reprogrammé: {post_id} pour {new_time}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Erreur reprogrammation: {e}")
            return False
    
    def get_scheduled_posts_summary(self) -> dict:
        """Retourne un résumé des posts programmés"""
        try:
            scheduled_posts = self.db_manager.get_posts_by_status(PostStatus.SCHEDULED)
            ready_posts = self.db_manager.get_scheduled_posts_ready()
            
            # Grouper par période
            now = datetime.now()
            next_hour = now + timedelta(hours=1)
            next_day = now + timedelta(days=1)
            next_week = now + timedelta(weeks=1)
            
            summary = {
                'total_scheduled': len(scheduled_posts),
                'ready_now': len(ready_posts),
                'next_hour': 0,
                'next_day': 0,
                'next_week': 0,
                'later': 0,
                'overdue': 0
            }
            
            for post in scheduled_posts:
                if not post.scheduled_time:
                    continue
                
                if post.scheduled_time <= now:
                    if post in ready_posts:
                        continue  # Déjà compté dans ready_now
                    summary['overdue'] += 1
                elif post.scheduled_time <= next_hour:
                    summary['next_hour'] += 1
                elif post.scheduled_time <= next_day:
                    summary['next_day'] += 1
                elif post.scheduled_time <= next_week:
                    summary['next_week'] += 1
                else:
                    summary['later'] += 1
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Erreur résumé programmation: {e}")
            return {}
    
    def get_next_publication_time(self) -> Optional[datetime]:
        """Retourne l'heure de la prochaine publication programmée"""
        try:
            scheduled_posts = self.db_manager.get_posts_by_status(PostStatus.SCHEDULED)
            
            if not scheduled_posts:
                return None
            
            # Trouver le post avec la date la plus proche
            next_time = None
            for post in scheduled_posts:
                if post.scheduled_time and (not next_time or post.scheduled_time < next_time):
                    next_time = post.scheduled_time
            
            return next_time
            
        except Exception as e:
            self.logger.error(f"Erreur recherche prochaine publication: {e}")
            return None
    
    def retry_failed_posts(self, max_retries: int = 3) -> int:
        """Retente la publication des posts échoués"""
        try:
            failed_posts = self.db_manager.get_posts_by_status(PostStatus.FAILED)
            retried_count = 0
            
            for post in failed_posts:
                # Vérifier si le post peut être republié
                if post.can_be_published():
                    # Remettre en programmation immédiate
                    post.scheduled_time = datetime.now()
                    post.status = PostStatus.SCHEDULED.value
                    post.error_message = None
                    
                    if self.db_manager.update_post(post):
                        retried_count += 1
                        self.logger.info(f"🔄 Post {post.id} remis en file de publication")
                
                if retried_count >= max_retries:
                    break
            
            return retried_count
            
        except Exception as e:
            self.logger.error(f"Erreur retry posts échoués: {e}")
            return 0
    
    def cleanup_old_data(self, days: int = 30):
        """Nettoie les anciennes données de scheduling"""
        try:
            # Cette méthode pourrait nettoyer les logs de scheduling anciens
            cutoff_date = datetime.now() - timedelta(days=days)
            self.logger.info(f"🧹 Nettoyage des données antérieures à {cutoff_date}")
            
            # Appeler la méthode de nettoyage de la base de données
            self.db_manager.cleanup_old_data(days)
            
        except Exception as e:
            self.logger.error(f"Erreur nettoyage: {e}")
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques du scheduler"""
        try:
            stats = self.db_manager.get_posts_stats()
            
            scheduler_stats = {
                'is_running': self.is_running,
                'check_interval': self.check_interval,
                'next_check_in': self.check_interval if self.is_running else None,
                'posts_stats': stats,
                'next_publication': self.get_next_publication_time(),
                'scheduled_summary': self.get_scheduled_posts_summary()
            }
            
            return scheduler_stats
            
        except Exception as e:
            self.logger.error(f"Erreur statistiques scheduler: {e}")
            return {'error': str(e)}
    
    def set_callbacks(self, on_published: Callable = None, 
                     on_failed: Callable = None, on_error: Callable = None):
        """Configure les callbacks pour les événements du scheduler"""
        self.on_post_published = on_published
        self.on_post_failed = on_failed
        self.on_scheduler_error = on_error
    
    def manual_check(self) -> dict:
        """Effectue une vérification manuelle des posts à publier"""
        try:
            self.logger.info("🔍 Vérification manuelle des posts programmés")
            
            before_stats = self.db_manager.get_posts_stats()
            
            # Exécuter la vérification
            self._check_and_publish_scheduled_posts()
            
            after_stats = self.db_manager.get_posts_stats()
            
            result = {
                'success': True,
                'posts_published': after_stats['published'] - before_stats['published'],
                'posts_failed': after_stats['failed'] - before_stats['failed'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"✓ Vérification terminée: {result['posts_published']} publiés, {result['posts_failed']} échoués")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur vérification manuelle: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }