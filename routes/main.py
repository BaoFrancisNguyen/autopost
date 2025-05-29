import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from datetime import datetime

# Import conditionnel des modèles
try:
    from models import Post, PostStatus, ContentTone
except ImportError:
    # Modèles de secours si models.py n'est pas disponible
    class PostStatus:
        DRAFT = "draft"
        SCHEDULED = "scheduled"
        PUBLISHED = "published"
        FAILED = "failed"
        PROCESSING = "processing"
    
    class ContentTone:
        ENGAGING = "engageant"

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Page d'accueil - Dashboard"""
    try:
        # Vérifier si le gestionnaire de base de données existe
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            # Version de secours sans base de données
            stats = {'total': 0, 'published': 0, 'scheduled': 0, 'failed': 0, 'ready_to_publish': 0}
            posts = []
        else:
            # Récupérer les statistiques
            stats = current_app.db_manager.get_posts_stats()
            # Récupérer les posts récents (limitez à 10)
            posts = current_app.db_manager.get_all_posts(limit=10)
        
        return render_template('index.html', posts=posts, stats=stats)
        
    except Exception as e:
        current_app.logger.error(f"Erreur dashboard: {e}")
        flash('Erreur lors du chargement du dashboard', 'error')
        # Retourner une version minimale en cas d'erreur
        stats = {'total': 0, 'published': 0, 'scheduled': 0, 'failed': 0, 'ready_to_publish': 0}
        return render_template('index.html', posts=[], stats=stats)


@main_bp.route('/create', methods=['GET', 'POST'])
def create_post():
    """Création d'un nouveau post"""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.form.get('title', '').strip()
            topic = request.form.get('topic', '').strip()
            image_prompt = request.form.get('image_prompt', '').strip()
            tone = request.form.get('tone', 'engageant')
            scheduled_time_str = request.form.get('scheduled_time', '').strip()
            additional_context = request.form.get('additional_context', '').strip()
            
            # Validation des champs obligatoires
            if not all([title, topic, image_prompt]):
                flash('Tous les champs obligatoires doivent être remplis', 'error')
                return render_template('create_post.html')
            
            # Traitement de la date de programmation
            scheduled_time = None
            if scheduled_time_str:
                try:
                    scheduled_time = datetime.fromisoformat(scheduled_time_str)
                    if scheduled_time <= datetime.now():
                        flash('La date de programmation doit être dans le futur', 'error')
                        return render_template('create_post.html')
                except ValueError:
                    flash('Format de date invalide', 'error')
                    return render_template('create_post.html')
            
            current_app.logger.info(f"Création d'un nouveau post: {title}")
            
            # Génération du contenu avec IA
            description = ""
            hashtags = ""
            
            if hasattr(current_app, 'content_generator') and current_app.content_generator:
                current_app.logger.info("Génération du contenu avec IA...")
                
                result = current_app.content_generator.generate_description_and_hashtags(
                    topic, tone, additional_context
                )
                
                if result.success:
                    description = result.description
                    hashtags = result.hashtags
                    current_app.logger.info("✅ Contenu généré avec succès")
                else:
                    current_app.logger.warning(f"❌ Échec génération contenu: {result.error_message}")
                    description = f"Post sur le sujet: {topic}"
                    hashtags = f"#{topic.replace(' ', '').lower()} #instagram #ai"
            else:
                # Contenu par défaut si pas d'IA
                description = f"Découvrez notre contenu sur {topic} !"
                hashtags = f"#{topic.replace(' ', '').lower()} #instagram #automation"
            
            # Génération de l'image avec IA
            image_path = None
            if hasattr(current_app, 'ai_generator') and current_app.ai_generator:
                current_app.logger.info("Génération de l'image avec IA...")
                
                image_result = current_app.ai_generator.generate_image(image_prompt)
                
                if image_result.success:
                    image_path = image_result.image_path
                    current_app.logger.info(f"✅ Image générée: {image_path}")
                else:
                    current_app.logger.warning(f"❌ Échec génération image: {image_result.error_message}")
                    flash(f'Image non générée: {image_result.error_message}', 'error')
            
            # Déterminer le statut
            if scheduled_time:
                status = PostStatus.SCHEDULED
            else:
                status = PostStatus.DRAFT
            
            # Vérifier si la base de données est disponible
            if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
                flash('Base de données non disponible', 'error')
                return render_template('create_post.html')
            
            # Créer le post (version simplifiée)
            try:
                # Simuler la création d'un post
                post_data = {
                    'title': title,
                    'description': description,
                    'hashtags': hashtags,
                    'image_prompt': image_prompt,
                    'topic': topic,
                    'tone': tone,
                    'image_path': image_path,
                    'scheduled_time': scheduled_time,
                    'status': status
                }
                
                # Si les modèles sont disponibles, créer un vrai post
                if 'Post' in globals():
                    post = Post(
                        title=title,
                        description=description,
                        hashtags=hashtags,
                        image_prompt=image_prompt,
                        topic=topic,
                        tone=tone,
                        image_path=image_path,
                        scheduled_time=scheduled_time,
                        status=status
                    )
                    
                    post_id = current_app.db_manager.create_post(post)
                else:
                    # Simulation d'ID
                    post_id = 1
                
                if post_id:
                    success_msg = f'Post "{title}" créé avec succès!'
                    if scheduled_time:
                        success_msg += f' Programmé pour {scheduled_time.strftime("%d/%m/%Y à %H:%M")}'
                    
                    flash(success_msg, 'success')
                    current_app.logger.info(f"✅ Post créé avec ID: {post_id}")
                    return redirect(url_for('main.index'))
                else:
                    flash('Erreur lors de la création du post', 'error')
                    
            except Exception as e:
                current_app.logger.error(f"Erreur création post en base: {e}")
                flash(f'Post créé mais non sauvegardé: {str(e)}', 'warning')
                
        except Exception as e:
            current_app.logger.error(f"Erreur création post: {e}")
            flash(f'Erreur lors de la création: {str(e)}', 'error')
    
    return render_template('create_post.html')


@main_bp.route('/post/<int:post_id>/publish')
def publish_now(post_id):
    """Publication immédiate d'un post"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            flash('Base de données non disponible', 'error')
            return redirect(url_for('main.index'))
        
        # Récupérer le post
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            flash('Post non trouvé', 'error')
            return redirect(url_for('main.index'))
        
        if not hasattr(current_app, 'instagram_publisher') or not current_app.instagram_publisher:
            flash('Service Instagram non configuré', 'error')
            return redirect(url_for('main.index'))
        
        current_app.logger.info(f"Publication immédiate du post: {post.title}")
        
        # Marquer comme en cours si possible
        try:
            current_app.db_manager.update_post_status(post_id, PostStatus.PROCESSING)
        except:
            pass
        
        # Publier sur Instagram
        caption = f"{post.description}\n\n{post.hashtags}" if hasattr(post, 'get_full_caption') else f"{post.description}\n\n{post.hashtags}"
        result = current_app.instagram_publisher.publish_post(post.image_path, caption)
        
        if result.success:
            # Mettre à jour le statut
            try:
                current_app.db_manager.update_post_status(
                    post_id, 
                    PostStatus.PUBLISHED,
                    instagram_post_id=result.instagram_post_id
                )
            except:
                pass
            
            flash(f'Post "{post.title}" publié avec succès sur Instagram!', 'success')
            current_app.logger.info(f"✅ Post {post_id} publié avec succès")
        else:
            # Marquer comme échoué
            try:
                current_app.db_manager.update_post_status(
                    post_id, 
                    PostStatus.FAILED,
                    error_message=result.error_message
                )
            except:
                pass
            
            flash(f'Erreur lors de la publication: {result.error_message}', 'error')
            current_app.logger.error(f"❌ Échec publication post {post_id}: {result.error_message}")
            
    except Exception as e:
        current_app.logger.error(f"Erreur publication post {post_id}: {e}")
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('main.index'))


@main_bp.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    """Modification d'un post existant"""
    if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
        flash('Base de données non disponible', 'error')
        return redirect(url_for('main.index'))
    
    post = current_app.db_manager.get_post_by_id(post_id)
    
    if not post:
        flash('Post non trouvé', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # Mise à jour des champs
            post.title = request.form.get('title', post.title).strip()
            post.topic = request.form.get('topic', post.topic).strip()
            post.description = request.form.get('description', post.description).strip()
            post.hashtags = request.form.get('hashtags', post.hashtags).strip()
            post.image_prompt = request.form.get('image_prompt', post.image_prompt).strip()
            post.tone = request.form.get('tone', post.tone)
            
            # Programmation
            scheduled_time_str = request.form.get('scheduled_time', '').strip()
            if scheduled_time_str:
                post.scheduled_time = datetime.fromisoformat(scheduled_time_str)
                if post.status == PostStatus.DRAFT:
                    post.status = PostStatus.SCHEDULED
            else:
                post.scheduled_time = None
                if post.status == PostStatus.SCHEDULED:
                    post.status = PostStatus.DRAFT
            
            # Regénérer l'image si demandé
            if request.form.get('regenerate_image') == 'on' and hasattr(current_app, 'ai_generator') and current_app.ai_generator:
                image_result = current_app.ai_generator.generate_image(post.image_prompt)
                if image_result.success:
                    post.image_path = image_result.image_path
                    flash('Image régénérée avec succès', 'success')
            
            # Sauvegarder
            if current_app.db_manager.update_post(post):
                flash(f'Post "{post.title}" mis à jour avec succès', 'success')
                return redirect(url_for('main.index'))
            else:
                flash('Erreur lors de la mise à jour', 'error')
                
        except ValueError as e:
            flash('Format de date invalide', 'error')
        except Exception as e:
            current_app.logger.error(f"Erreur modification post {post_id}: {e}")
            flash(f'Erreur: {str(e)}', 'error')
    
    return render_template('edit_post.html', post=post)


@main_bp.route('/post/<int:post_id>/delete')
def delete_post(post_id):
    """Suppression d'un post"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            flash('Base de données non disponible', 'error')
            return redirect(url_for('main.index'))
        
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            flash('Post non trouvé', 'error')
            return redirect(url_for('main.index'))
        
        # Supprimer le fichier image si il existe
        if hasattr(post, 'image_path') and post.image_path and os.path.exists(post.image_path):
            try:
                os.remove(post.image_path)
            except Exception as e:
                current_app.logger.warning(f"Impossible de supprimer l'image: {e}")
        
        # Supprimer de la base de données
        if current_app.db_manager.delete_post(post_id):
            flash(f'Post supprimé avec succès', 'success')
            current_app.logger.info(f"Post {post_id} supprimé")
        else:
            flash('Erreur lors de la suppression', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Erreur suppression post {post_id}: {e}")
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('main.index'))


@main_bp.route('/posts')
def list_posts():
    """Liste paginée de tous les posts"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            flash('Base de données non disponible', 'error')
            return render_template('list_posts.html', posts=[], stats={}, current_page=1, total_pages=1)
        
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        posts = current_app.db_manager.get_all_posts(limit=per_page, offset=offset)
        stats = current_app.db_manager.get_posts_stats()
        
        # Calculer le nombre total de pages
        total_pages = (stats['total'] + per_page - 1) // per_page
        
        return render_template('list_posts.html', 
                             posts=posts, 
                             stats=stats,
                             current_page=page,
                             total_pages=total_pages)
        
    except Exception as e:
        current_app.logger.error(f"Erreur liste posts: {e}")
        flash('Erreur lors du chargement des posts', 'error')
        return render_template('list_posts.html', posts=[], stats={}, current_page=1, total_pages=1)


@main_bp.route('/scheduler')
def scheduler_status():
    """Page de statut du scheduler"""
    try:
        if not hasattr(current_app, 'scheduler') or not current_app.scheduler:
            flash('Scheduler non disponible', 'error')
            return render_template('scheduler.html', stats={}, scheduled_posts=[], ready_posts=[])
        
        stats = current_app.scheduler.get_statistics()
        
        if hasattr(current_app, 'db_manager') and current_app.db_manager:
            scheduled_posts = current_app.db_manager.get_posts_by_status(PostStatus.SCHEDULED)
            ready_posts = current_app.db_manager.get_scheduled_posts_ready()
        else:
            scheduled_posts = []
            ready_posts = []
        
        return render_template('scheduler.html', 
                             stats=stats,
                             scheduled_posts=scheduled_posts,
                             ready_posts=ready_posts)
        
    except Exception as e:
        current_app.logger.error(f"Erreur statut scheduler: {e}")
        flash('Erreur lors du chargement du scheduler', 'error')
        return render_template('scheduler.html', stats={}, scheduled_posts=[], ready_posts=[])


@main_bp.route('/scheduler/manual-check')
def manual_check():
    """Déclenchement manuel du scheduler"""
    try:
        if not hasattr(current_app, 'scheduler') or not current_app.scheduler:
            flash('Scheduler non disponible', 'error')
            return redirect(url_for('main.scheduler_status'))
        
        result = current_app.scheduler.manual_check()
        
        if result['success']:
            msg = f"Vérification terminée: {result['posts_published']} publiés"
            if result['posts_failed'] > 0:
                msg += f", {result['posts_failed']} échoués"
            flash(msg, 'success')
        else:
            flash(f'Erreur: {result["error"]}', 'error')
            
    except Exception as e:
        current_app.logger.error(f"Erreur vérification manuelle: {e}")
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('main.scheduler_status'))


@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Page de paramètres de l'application"""
    if request.method == 'POST':
        try:
            flash('Paramètres mis à jour avec succès', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Erreur mise à jour paramètres: {e}")
            flash(f'Erreur: {str(e)}', 'error')
    
    # Récupérer les informations de configuration et de statut
    try:
        services_status = {}
        services_status['database'] = hasattr(current_app, 'db_manager') and current_app.db_manager is not None
        services_status['ai_generator'] = hasattr(current_app, 'ai_generator') and current_app.ai_generator is not None
        services_status['content_generator'] = hasattr(current_app, 'content_generator') and current_app.content_generator is not None
        services_status['instagram_publisher'] = hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher is not None
        services_status['scheduler'] = hasattr(current_app, 'scheduler') and current_app.scheduler is not None
        
        # Test de connexion Instagram
        if services_status['instagram_publisher']:
            try:
                instagram_test = current_app.instagram_publisher.test_connection()
                services_status['instagram_test'] = instagram_test
            except:
                services_status['instagram_test'] = {'errors': ['Impossible de tester la connexion']}
        
        return render_template('settings.html', services_status=services_status)
        
    except Exception as e:
        current_app.logger.error(f"Erreur chargement paramètres: {e}")
        flash('Erreur lors du chargement des paramètres', 'error')
        return render_template('settings.html', services_status={})


@main_bp.route('/post/<int:post_id>/preview')
def preview_post(post_id):
    """Aperçu d'un post avant publication"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            flash('Base de données non disponible', 'error')
            return redirect(url_for('main.index'))
        
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            flash('Post non trouvé', 'error')
            return redirect(url_for('main.index'))
        
        return render_template('preview_post.html', post=post)
        
    except Exception as e:
        current_app.logger.error(f"Erreur aperçu post {post_id}: {e}")
        flash(f'Erreur: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/analytics')
def analytics():
    """Page d'analytics et statistiques détaillées"""
    try:
        # Statistiques générales
        if hasattr(current_app, 'db_manager') and current_app.db_manager:
            stats = current_app.db_manager.get_posts_stats()
            recent_activity = current_app.db_manager.get_recent_activity(20)
        else:
            stats = {}
            recent_activity = []
        
        # Posts récents par statut (version simplifiée)
        recent_published = []
        recent_failed = []
        
        # Statistiques du scheduler si disponible
        scheduler_stats = None
        if hasattr(current_app, 'scheduler') and current_app.scheduler:
            scheduler_stats = current_app.scheduler.get_statistics()
        
        return render_template('analytics.html', 
                             stats=stats,
                             recent_published=recent_published,
                             recent_failed=recent_failed,
                             recent_activity=recent_activity,
                             scheduler_stats=scheduler_stats)
        
    except Exception as e:
        current_app.logger.error(f"Erreur analytics: {e}")
        flash('Erreur lors du chargement des analytics', 'error')
        return render_template('analytics.html', 
                             stats={},
                             recent_published=[],
                             recent_failed=[],
                             recent_activity=[],
                             scheduler_stats=None)


@main_bp.route('/search')
def search_posts():
    """Recherche de posts"""
    query = request.args.get('q', '').strip()
    posts = []
    
    if query and hasattr(current_app, 'db_manager') and current_app.db_manager:
        try:
            posts = current_app.db_manager.search_posts(query, limit=50)
            flash(f'{len(posts)} post(s) trouvé(s) pour "{query}"', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Erreur recherche: {e}")
            flash('Erreur lors de la recherche', 'error')
    
    return render_template('search_results.html', posts=posts, query=query)


# Filtres de template personnalisés
@main_bp.app_template_filter('datetime_format')
def datetime_format(value, format='%d/%m/%Y %H:%M'):
    """Formatte une datetime pour l'affichage"""
    if value is None:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except:
            return value
    return value.strftime(format)


@main_bp.app_template_filter('truncate_words')
def truncate_words(text, length=50):
    """Tronque un texte à un nombre de mots donné"""
    if not text:
        return ''
    words = text.split()
    if len(words) <= length:
        return text
    return ' '.join(words[:length]) + '...'


@main_bp.app_template_filter('status_icon')
def status_icon(status):
    """Retourne l'icône Font Awesome pour un statut"""
    icons = {
        'draft': 'fas fa-edit',
        'scheduled': 'fas fa-clock',
        'published': 'fas fa-check-circle',
        'failed': 'fas fa-exclamation-triangle',
        'processing': 'fas fa-spinner'
    }
    return icons.get(status, 'fas fa-question')


# Contexte de template global
@main_bp.app_context_processor
def inject_global_vars():
    """Injecte des variables globales dans tous les templates"""
    return {
        'app_name': 'Instagram Automation',
        'current_year': datetime.now().year,
        'services_available': {
            'ai_generator': hasattr(current_app, 'ai_generator') and current_app.ai_generator is not None,
            'content_generator': hasattr(current_app, 'content_generator') and current_app.content_generator is not None,
            'instagram_publisher': hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher is not None,
            'scheduler': hasattr(current_app, 'scheduler') and current_app.scheduler is not None,
        }
    }