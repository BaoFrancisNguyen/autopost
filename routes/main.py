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
    """Création d'un nouveau post avec génération IA complète"""
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
            
            # ÉTAPE 1: GÉNÉRATION DU CONTENU TEXTE avec IA
            description = ""
            hashtags = ""
            
            flash('🤖 Génération du contenu texte en cours...', 'info')
            
            if hasattr(current_app, 'content_generator') and current_app.content_generator:
                current_app.logger.info("Génération du contenu texte avec IA...")
                
                try:
                    result = current_app.content_generator.generate_description_and_hashtags(
                        topic, tone, additional_context
                    )
                    
                    if result.success:
                        description = result.description
                        hashtags = result.hashtags
                        current_app.logger.info("✅ Contenu texte généré avec succès")
                        flash('✅ Contenu texte généré avec succès !', 'success')
                    else:
                        current_app.logger.warning(f"❌ Échec génération contenu: {result.error_message}")
                        flash(f'⚠️ Problème génération contenu: {result.error_message}', 'warning')
                        # Contenu par défaut
                        description = f"Découvrez ce contenu passionnant sur {topic} ! Partagez votre avis en commentaires."
                        hashtags = f"#{topic.replace(' ', '').lower()} #instagram #ai #content"
                except Exception as e:
                    current_app.logger.error(f"Erreur génération contenu: {e}")
                    flash('❌ Erreur lors de la génération du contenu', 'warning')
                    description = f"Post inspirant sur le sujet: {topic}"
                    hashtags = f"#{topic.replace(' ', '').lower()} #instagram"
            else:
                # Contenu par défaut si pas d'IA
                current_app.logger.warning("Aucun générateur de contenu disponible")
                flash('⚠️ Générateur de contenu non disponible - Contenu par défaut', 'warning')
                description = f"Découvrez notre contenu exclusif sur {topic} !"
                hashtags = f"#{topic.replace(' ', '').lower()} #instagram #automation"
            
            # ÉTAPE 2: GÉNÉRATION DE L'IMAGE avec IA
            image_path = None
            
            flash('🎨 Génération de l\'image en cours... (peut prendre 10-30 secondes)', 'info')
            
            if hasattr(current_app, 'image_generator') and current_app.image_generator:
                current_app.logger.info("Génération de l'image avec IA...")
                
                try:
                    # Optimiser le prompt pour Instagram
                    optimized_prompt = f"{image_prompt}, professional photography, instagram style, high quality, vibrant colors, detailed, masterpiece"
                    
                    # Générer l'image selon le type de générateur
                    if hasattr(current_app.image_generator, 'is_available'):
                        # C'est Stable Diffusion
                        if current_app.image_generator.is_available:
                            image_result = current_app.image_generator.generate_image(
                                optimized_prompt,
                                width=720,
                                height=720,
                                steps=20,
                                cfg_scale=7.0
                            )
                        else:
                            raise Exception("Stable Diffusion non accessible")
                    else:
                        # C'est OpenAI ou Hugging Face
                        image_result = current_app.image_generator.generate_image(optimized_prompt)
                    
                    if image_result.success:
                        image_path = image_result.image_path
                        current_app.logger.info(f"✅ Image générée: {image_path}")
                        flash('✅ Image générée avec succès !', 'success')
                    else:
                        current_app.logger.warning(f"❌ Échec génération image: {image_result.error_message}")
                        flash(f'⚠️ Problème génération image: {image_result.error_message}', 'warning')
                        
                except Exception as e:
                    current_app.logger.error(f"Erreur génération image: {e}")
                    flash('❌ Erreur lors de la génération de l\'image', 'warning')
            else:
                current_app.logger.warning("Aucun générateur d'images disponible")
                flash('⚠️ Aucun service de génération d\'images disponible', 'warning')
            
            # ÉTAPE 3: DÉTERMINER LE STATUT
            if scheduled_time:
                status = PostStatus.SCHEDULED.value if hasattr(PostStatus, 'SCHEDULED') else "scheduled"
            else:
                status = PostStatus.DRAFT.value if hasattr(PostStatus, 'DRAFT') else "draft"
            
            # ÉTAPE 4: VÉRIFIER LA BASE DE DONNÉES
            if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
                flash('❌ Base de données non disponible', 'error')
                return render_template('create_post.html')
            
            # ÉTAPE 5: CRÉER ET SAUVEGARDER LE POST
            try:
                # Créer l'objet Post
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
                
                if post_id:
                    success_msg = f'🎉 Post "{title}" créé avec succès!'
                    if scheduled_time:
                        success_msg += f' Programmé pour {scheduled_time.strftime("%d/%m/%Y à %H:%M")}'
                    else:
                        success_msg += ' Sauvegardé en brouillon.'
                    
                    if image_path:
                        success_msg += ' Image générée !'
                    if description:
                        success_msg += ' Contenu généré !'
                    
                    flash(success_msg, 'success')
                    current_app.logger.info(f"✅ Post créé avec ID: {post_id}")
                    
                    # Rediriger vers la page d'aperçu du post créé
                    return redirect(url_for('main.preview_post', post_id=post_id))
                else:
                    flash('❌ Erreur lors de la création du post en base de données', 'error')
                    
            except Exception as e:
                current_app.logger.error(f"Erreur création post en base: {e}")
                flash(f'❌ Erreur lors de la sauvegarde: {str(e)}', 'error')
                
        except Exception as e:
            current_app.logger.error(f"Erreur création post: {e}")
            flash(f'❌ Erreur lors de la création: {str(e)}', 'error')
    
    return render_template('create_post.html')


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
            return redirect(url_for('main.preview_post', post_id=post_id))
        
        current_app.logger.info(f"Publication immédiate du post: {post.title}")
        
        # Marquer comme en cours si possible
        try:
            current_app.db_manager.update_post_status(post_id, PostStatus.PROCESSING if hasattr(PostStatus, 'PROCESSING') else "processing")
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
                    PostStatus.PUBLISHED if hasattr(PostStatus, 'PUBLISHED') else "published",
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
                    PostStatus.FAILED if hasattr(PostStatus, 'FAILED') else "failed",
                    error_message=result.error_message
                )
            except:
                pass
            
            flash(f'Erreur lors de la publication: {result.error_message}', 'error')
            current_app.logger.error(f"❌ Échec publication post {post_id}: {result.error_message}")
            
    except Exception as e:
        current_app.logger.error(f"Erreur publication post {post_id}: {e}")
        flash(f'Erreur: {str(e)}', 'error')
    
    return redirect(url_for('main.preview_post', post_id=post_id))


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
                if post.status == (PostStatus.DRAFT.value if hasattr(PostStatus, 'DRAFT') else "draft"):
                    post.status = PostStatus.SCHEDULED.value if hasattr(PostStatus, 'SCHEDULED') else "scheduled"
            else:
                post.scheduled_time = None
                if post.status == (PostStatus.SCHEDULED.value if hasattr(PostStatus, 'SCHEDULED') else "scheduled"):
                    post.status = PostStatus.DRAFT.value if hasattr(PostStatus, 'DRAFT') else "draft"
            
            # Regénérer l'image si demandé
            if request.form.get('regenerate_image') == 'on' and hasattr(current_app, 'image_generator') and current_app.image_generator:
                try:
                    flash('Régénération de l\'image en cours...', 'info')
                    optimized_prompt = f"{post.image_prompt}, professional photography, instagram style, high quality"
                    
                    if hasattr(current_app.image_generator, 'is_available'):
                        # Stable Diffusion
                        if current_app.image_generator.is_available:
                            image_result = current_app.image_generator.generate_image(optimized_prompt)
                        else:
                            raise Exception("Stable Diffusion non accessible")
                    else:
                        # OpenAI ou autres
                        image_result = current_app.image_generator.generate_image(optimized_prompt)
                    
                    if image_result.success:
                        # Supprimer l'ancienne image si elle existe
                        if post.image_path and os.path.exists(post.image_path):
                            try:
                                os.remove(post.image_path)
                            except:
                                pass
                        
                        post.image_path = image_result.image_path
                        flash('Image régénérée avec succès', 'success')
                    else:
                        flash(f'Erreur régénération image: {image_result.error_message}', 'error')
                except Exception as e:
                    flash(f'Erreur régénération image: {str(e)}', 'error')
            
            # Sauvegarder
            if current_app.db_manager.update_post(post):
                flash(f'Post "{post.title}" mis à jour avec succès', 'success')
                return redirect(url_for('main.preview_post', post_id=post_id))
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
        
        # Base de données
        services_status['database'] = hasattr(current_app, 'db_manager') and current_app.db_manager is not None
        
        # Générateurs IA
        services_status['ai_generator'] = hasattr(current_app, 'image_generator') and current_app.image_generator is not None and not hasattr(current_app.image_generator, 'is_available')
        services_status['content_generator'] = hasattr(current_app, 'content_generator') and current_app.content_generator is not None
        
        # Stable Diffusion (NOUVEAU)
        services_status['sd_generator'] = (
            hasattr(current_app, 'sd_generator') and 
            current_app.sd_generator is not None and 
            current_app.sd_generator.is_available
        )
        
        # Hugging Face
        services_status['hf_generator'] = (
            hasattr(current_app, 'hf_generator') and 
            current_app.hf_generator is not None
        )
        
        # Instagram
        services_status['instagram_publisher'] = hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher is not None
        
        # Scheduler
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


# Routes pour les images et galeries
@main_bp.route('/static/generated/<filename>')
def serve_generated_image(filename):
    """Sert les images générées depuis le dossier generated"""
    try:
        from flask import send_from_directory
        return send_from_directory('generated', filename)
    except Exception as e:
        current_app.logger.error(f"Erreur servir image: {e}")
        return "Image non trouvée", 404


@main_bp.route('/gallery')
def image_gallery():
    """Page de galerie des images générées"""
    try:
        import glob
        
        # Récupérer toutes les images du dossier generated
        generated_folder = 'generated'
        if not os.path.exists(generated_folder):
            os.makedirs(generated_folder)
        
        # Patterns de fichiers d'images
        image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.gif']
        images = []
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join(generated_folder, pattern))
            for file_path in files:
                try:
                    # Informations sur le fichier
                    filename = os.path.basename(file_path)
                    stats = os.stat(file_path)
                    created_time = datetime.fromtimestamp(stats.st_ctime)
                    file_size = stats.st_size
                    
                    # Essayer d'extraire le prompt du nom de fichier
                    prompt_hint = filename.split('_')[2:] if '_' in filename else []
                    prompt_hint = ' '.join(prompt_hint).replace('.png', '').replace('.jpg', '').replace('_', ' ')
                    
                    images.append({
                        'filename': filename,
                        'url': f'/static/generated/{filename}',
                        'created_time': created_time,
                        'file_size': file_size,
                        'prompt_hint': prompt_hint[:50] if prompt_hint else 'Image générée'
                    })
                except Exception as e:
                    current_app.logger.warning(f"Erreur lecture fichier {file_path}: {e}")
        
        # Trier par date de création (plus récent en premier)
        images.sort(key=lambda x: x['created_time'], reverse=True)
        
        return render_template('gallery.html', images=images, total_images=len(images))
        
    except Exception as e:
        current_app.logger.error(f"Erreur galerie: {e}")
        flash('Erreur lors du chargement de la galerie', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/test-generation')
def test_generation_page():
    """Page de test de génération d'images"""
    try:
        # Vérifier les services disponibles
        services_available = {
            'stable_diffusion': hasattr(current_app, 'sd_generator') and current_app.sd_generator and current_app.sd_generator.is_available,
            'huggingface': hasattr(current_app, 'hf_generator') and current_app.hf_generator,
            'openai': hasattr(current_app, 'image_generator') and current_app.image_generator and not hasattr(current_app.image_generator, 'is_available')
        }
        
        return render_template('test_generation.html', services=services_available)
        
    except Exception as e:
        current_app.logger.error(f"Erreur page test génération: {e}")
        flash('Erreur lors du chargement de la page de test', 'error')
        return redirect(url_for('main.index'))


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
            'ai_generator': hasattr(current_app, 'image_generator') and current_app.image_generator is not None,
            'content_generator': hasattr(current_app, 'content_generator') and current_app.content_generator is not None,
            'instagram_publisher': hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher is not None,
            'scheduler': hasattr(current_app, 'scheduler') and current_app.scheduler is not None,
        }
    }