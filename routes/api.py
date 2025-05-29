from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import os

from models import Post, PostStatus, GenerationRequest, ContentTone

api_bp = Blueprint('api', __name__)


@api_bp.route('/generate-content', methods=['POST'])
def generate_content():
    """API pour générer du contenu en temps réel"""
    try:
        if not current_app.content_generator:
            return jsonify({'error': 'Service de génération de contenu non disponible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        topic = data.get('topic', '').strip()
        tone = data.get('tone', ContentTone.ENGAGING.value)
        additional_context = data.get('additional_context', '').strip()
        
        if not topic:
            return jsonify({'error': 'Le sujet est requis'}), 400
        
        current_app.logger.info(f"API: Génération de contenu pour '{topic}'")
        
        result = current_app.content_generator.generate_description_and_hashtags(
            topic, tone, additional_context
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'description': result.description,
                'hashtags': result.hashtags,
                'topic': topic,
                'tone': tone
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération contenu: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/generate-image', methods=['POST'])
def generate_image():
    """API pour générer une image"""
    try:
        if not current_app.ai_generator:
            return jsonify({'error': 'Service de génération d\'image non disponible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', '').strip()
        size = data.get('size', '1024x1024')
        quality = data.get('quality', 'standard')
        
        if not prompt:
            return jsonify({'error': 'Le prompt est requis'}), 400
        
        # Valider le prompt
        is_valid, validation_msg = current_app.ai_generator.validate_prompt(prompt)
        if not is_valid:
            return jsonify({'error': validation_msg}), 400
        
        current_app.logger.info(f"API: Génération d'image pour '{prompt[:50]}...'")
        
        result = current_app.ai_generator.generate_image(prompt, size, quality)
        
        if result.success:
            # Convertir le chemin en URL accessible
            image_filename = os.path.basename(result.image_path)
            image_url = f"/static/generated/{image_filename}"  # Adapter selon votre config
            
            return jsonify({
                'success': True,
                'image_path': result.image_path,
                'image_url': image_url,
                'prompt_used': result.prompt_used
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération image: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts', methods=['GET'])
def get_posts():
    """API pour récupérer la liste des posts"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        # Limiter per_page pour éviter les surcharges
        per_page = min(per_page, 100)
        offset = (page - 1) * per_page
        
        if status:
            try:
                status_enum = PostStatus(status)
                posts = current_app.db_manager.get_posts_by_status(status_enum)
            except ValueError:
                return jsonify({'error': f'Statut invalide: {status}'}), 400
        else:
            posts = current_app.db_manager.get_all_posts(limit=per_page, offset=offset)
        
        # Convertir en dictionnaires
        posts_data = [post.to_dict() for post in posts]
        
        # Statistiques
        stats = current_app.db_manager.get_posts_stats()
        
        return jsonify({
            'success': True,
            'posts': posts_data,
            'stats': stats,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': stats['total']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API récupération posts: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """API pour récupérer un post spécifique"""
    try:
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            return jsonify({'error': 'Post non trouvé'}), 404
        
        return jsonify({
            'success': True,
            'post': post.to_dict()
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API récupération post {post_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts', methods=['POST'])
def create_post_api():
    """API pour créer un nouveau post"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Validation des champs requis
        required_fields = ['title', 'topic', 'image_prompt']
        for field in required_fields:
            if not data.get(field, '').strip():
                return jsonify({'error': f'Le champ {field} est requis'}), 400
        
        title = data['title'].strip()
        topic = data['topic'].strip()
        image_prompt = data['image_prompt'].strip()
        tone = data.get('tone', ContentTone.ENGAGING.value)
        additional_context = data.get('additional_context', '').strip()
        
        # Date de programmation
        scheduled_time = None
        if data.get('scheduled_time'):
            try:
                scheduled_time = datetime.fromisoformat(data['scheduled_time'])
            except ValueError:
                return jsonify({'error': 'Format de date invalide (ISO format requis)'}), 400
        
        current_app.logger.info(f"API: Création d'un post '{title}'")
        
        # Génération du contenu
        description = ""
        hashtags = ""
        
        if current_app.content_generator:
            result = current_app.content_generator.generate_description_and_hashtags(
                topic, tone, additional_context
            )
            if result.success:
                description = result.description
                hashtags = result.hashtags
        
        if not description:
            description = f"Contenu sur {topic}"
        if not hashtags:
            hashtags = f"#{topic.replace(' ', '').lower()} #instagram"
        
        # Génération de l'image
        image_path = None
        if current_app.ai_generator:
            image_result = current_app.ai_generator.generate_image(image_prompt)
            if image_result.success:
                image_path = image_result.image_path
        
        # Créer le post
        post = Post(
            title=title,
            description=description,
            hashtags=hashtags,
            image_prompt=image_prompt,
            topic=topic,
            tone=tone,
            image_path=image_path,
            scheduled_time=scheduled_time,
            status=PostStatus.SCHEDULED.value if scheduled_time else PostStatus.DRAFT.value
        )
        
        post_id = current_app.db_manager.create_post(post)
        
        if post_id:
            post.id = post_id
            return jsonify({
                'success': True,
                'message': 'Post créé avec succès',
                'post': post.to_dict()
            }), 201
        else:
            return jsonify({'error': 'Erreur lors de la création du post'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API création post: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts/<int:post_id>/publish', methods=['POST'])
def publish_post_api(post_id):
    """API pour publier un post"""
    try:
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            return jsonify({'error': 'Post non trouvé'}), 404
        
        if not post.can_be_published():
            return jsonify({'error': 'Post non prêt pour publication'}), 400
        
        if not current_app.instagram_publisher:
            return jsonify({'error': 'Service Instagram non configuré'}), 503
        
        current_app.logger.info(f"API: Publication du post {post_id}")
        
        # Marquer comme en cours
        current_app.db_manager.update_post_status(post_id, PostStatus.PROCESSING)
        
        # Publier
        caption = post.get_full_caption()
        result = current_app.instagram_publisher.publish_post(post.image_path, caption)
        
        if result.success:
            current_app.db_manager.update_post_status(
                post_id, 
                PostStatus.PUBLISHED,
                instagram_post_id=result.instagram_post_id
            )
            
            return jsonify({
                'success': True,
                'message': 'Post publié avec succès',
                'instagram_post_id': result.instagram_post_id
            })
        else:
            current_app.db_manager.update_post_status(
                post_id, 
                PostStatus.FAILED,
                error_message=result.error_message
            )
            
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API publication post {post_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts/<int:post_id>', methods=['PUT'])
def update_post_api(post_id):
    """API pour mettre à jour un post"""
    try:
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            return jsonify({'error': 'Post non trouvé'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        # Mise à jour des champs
        if 'title' in data:
            post.title = data['title'].strip()
        if 'description' in data:
            post.description = data['description'].strip()
        if 'hashtags' in data:
            post.hashtags = data['hashtags'].strip()
        if 'topic' in data:
            post.topic = data['topic'].strip()
        if 'tone' in data:
            post.tone = data['tone']
        if 'image_prompt' in data:
            post.image_prompt = data['image_prompt'].strip()
        
        # Programmation
        if 'scheduled_time' in data:
            if data['scheduled_time']:
                try:
                    post.scheduled_time = datetime.fromisoformat(data['scheduled_time'])
                    if post.status == PostStatus.DRAFT.value:
                        post.status = PostStatus.SCHEDULED.value
                except ValueError:
                    return jsonify({'error': 'Format de date invalide'}), 400
            else:
                post.scheduled_time = None
                if post.status == PostStatus.SCHEDULED.value:
                    post.status = PostStatus.DRAFT.value
        
        # Sauvegarder
        if current_app.db_manager.update_post(post):
            return jsonify({
                'success': True,
                'message': 'Post mis à jour avec succès',
                'post': post.to_dict()
            })
        else:
            return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API mise à jour post {post_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post_api(post_id):
    """API pour supprimer un post"""
    try:
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            return jsonify({'error': 'Post non trouvé'}), 404
        
        # Supprimer l'image si elle existe
        if post.image_path and os.path.exists(post.image_path):
            try:
                os.remove(post.image_path)
            except Exception as e:
                current_app.logger.warning(f"Impossible de supprimer l'image: {e}")
        
        # Supprimer de la base de données
        if current_app.db_manager.delete_post(post_id):
            return jsonify({
                'success': True,
                'message': 'Post supprimé avec succès'
            })
        else:
            return jsonify({'error': 'Erreur lors de la suppression'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API suppression post {post_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/scheduler/status', methods=['GET'])
def scheduler_status_api():
    """API pour récupérer le statut du scheduler"""
    try:
        if not current_app.scheduler:
            return jsonify({'error': 'Scheduler non disponible'}), 503
        
        stats = current_app.scheduler.get_statistics()
        
        return jsonify({
            'success': True,
            'scheduler': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API statut scheduler: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/scheduler/check', methods=['POST'])
def manual_check_api():
    """API pour déclencher une vérification manuelle du scheduler"""
    try:
        if not current_app.scheduler:
            return jsonify({'error': 'Scheduler non disponible'}), 503
        
        result = current_app.scheduler.manual_check()
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Erreur API vérification manuelle: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """API pour récupérer les statistiques de l'application"""
    try:
        # Statistiques des posts
        posts_stats = current_app.db_manager.get_posts_stats()
        
        # Statistiques du scheduler
        scheduler_stats = None
        if current_app.scheduler:
            scheduler_stats = current_app.scheduler.get_statistics()
        
        # Statut des services
        services_status = {
            'database': True,
            'ai_generator': current_app.ai_generator is not None,
            'content_generator': current_app.content_generator is not None,
            'instagram_publisher': current_app.instagram_publisher is not None,
            'scheduler': current_app.scheduler is not None and current_app.scheduler.is_running
        }
        
        return jsonify({
            'success': True,
            'posts': posts_stats,
            'scheduler': scheduler_stats,
            'services': services_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API statistiques: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/search', methods=['GET'])
def search_posts_api():
    """API pour rechercher des posts"""
    try:
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 20, type=int)
        
        if not query:
            return jsonify({'error': 'Paramètre de recherche requis'}), 400
        
        # Limiter le nombre de résultats
        limit = min(limit, 100)
        
        posts = current_app.db_manager.search_posts(query, limit)
        posts_data = [post.to_dict() for post in posts]
        
        return jsonify({
            'success': True,
            'query': query,
            'results': posts_data,
            'count': len(posts_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API recherche: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


# Gestionnaire d'erreurs pour l'API
@api_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Endpoint non trouvé'}), 404


@api_bp.errorhandler(405)
def api_method_not_allowed(error):
    return jsonify({'error': 'Méthode non autorisée'}), 405


@api_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500


# Middleware pour les logs des requêtes API
@api_bp.before_request
def log_api_request():
    current_app.logger.info(f"API Request: {request.method} {request.path}")


@api_bp.after_request
def log_api_response(response):
    current_app.logger.info(f"API Response: {response.status_code}")
    return response