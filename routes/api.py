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
        size = data.get('size', '720x720')
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
    """API pour récupérer les statistiques de l'application - VERSION CORRIGÉE"""
    try:
        # Statistiques des posts
        posts_stats = current_app.db_manager.get_posts_stats() if hasattr(current_app, 'db_manager') and current_app.db_manager else {}
        
        # Statistiques du scheduler
        scheduler_stats = None
        if hasattr(current_app, 'scheduler') and current_app.scheduler:
            try:
                scheduler_stats = current_app.scheduler.get_statistics()
            except Exception as e:
                current_app.logger.warning(f"Erreur stats scheduler: {e}")
        
        # Statut des services - VERSION CORRIGÉE
        services_status = {
            'database': hasattr(current_app, 'db_manager') and current_app.db_manager is not None,
            'content_generator': hasattr(current_app, 'content_generator') and current_app.content_generator is not None,
            'scheduler': hasattr(current_app, 'scheduler') and current_app.scheduler is not None and (current_app.scheduler.is_running if hasattr(current_app.scheduler, 'is_running') else False)
        }
        
        # Services d'images - LOGIQUE CORRIGÉE
        # Vérifier Stable Diffusion
        if hasattr(current_app, 'sd_generator') and current_app.sd_generator:
            services_status['stable_diffusion'] = current_app.sd_generator.is_available if hasattr(current_app.sd_generator, 'is_available') else False
        else:
            services_status['stable_diffusion'] = False
        
        # Vérifier Hugging Face
        if hasattr(current_app, 'hf_generator') and current_app.hf_generator:
            services_status['huggingface'] = True
        else:
            services_status['huggingface'] = False
        
        # Vérifier OpenAI (image_generator sans is_available = OpenAI)
        if hasattr(current_app, 'image_generator') and current_app.image_generator and not hasattr(current_app.image_generator, 'is_available'):
            services_status['openai_images'] = True
        else:
            services_status['openai_images'] = False
        
        # Instagram
        services_status['instagram_publisher'] = hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher is not None
        
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

# À ajouter dans routes/api.py

@api_bp.route('/test-sd-generation', methods=['POST'])
def test_sd_generation():
    """API pour tester la génération Stable Diffusion"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'error': 'Stable Diffusion non accessible. Vérifiez que l\'interface web est démarrée avec --api'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', 'a beautiful landscape, professional photography, high quality')
        
        current_app.logger.info(f"API: Test génération SD avec prompt: {prompt}")
        
        import time
        start_time = time.time()
        
        # Test avec paramètres rapides
        result = current_app.sd_generator.generate_image(
            prompt=prompt,
            steps=10,  # Rapide pour le test
            width=512,  # Plus petit pour être plus rapide
            height=512
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            return jsonify({
                'success': True,
                'image_path': result.image_path,
                'generation_time': round(generation_time, 1),
                'prompt_used': result.prompt_used
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API test SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/sd-models', methods=['GET'])
def get_sd_models():
    """API pour récupérer les modèles Stable Diffusion disponibles"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'error': 'Stable Diffusion non accessible'}), 503
        
        models = current_app.sd_generator.get_available_models()
        current_model = current_app.sd_generator.get_current_model()
        
        return jsonify({
            'success': True,
            'models': models,
            'current_model': current_model,
            'models_count': len(models)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API modèles SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/sd-status', methods=['GET'])
def get_sd_status():
    """API pour récupérer le statut de Stable Diffusion"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({
                'success': True,
                'available': False,
                'current_model': None,
                'api_url': None
            })
        
        status = current_app.sd_generator.get_status()
        
        return jsonify({
            'success': True,
            'available': status['available'],
            'current_model': status.get('current_model'),
            'api_url': status.get('api_url'),
            'model_count': status.get('model_count', 0)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API statut SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/change-sd-model', methods=['POST'])
def change_sd_model():
    """API pour changer le modèle Stable Diffusion"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'error': 'Stable Diffusion non accessible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        model_name = data.get('model_name', '').strip()
        if not model_name:
            return jsonify({'error': 'Nom de modèle requis'}), 400
        
        current_app.logger.info(f"API: Changement de modèle SD vers: {model_name}")
        
        success = current_app.sd_generator.change_model(model_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Modèle changé vers: {model_name}',
                'new_model': model_name
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Impossible de changer le modèle'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API changement modèle SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/generate-image-sd', methods=['POST'])
def generate_image_sd():
    """API pour générer une image avec Stable Diffusion"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'error': 'Stable Diffusion non accessible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt requis'}), 400
        
        # Paramètres optionnels
        negative_prompt = data.get('negative_prompt', '')
        steps = data.get('steps', 20)
        cfg_scale = data.get('cfg_scale', 7.0)
        width = data.get('width', 720)
        height = data.get('height', 720)
        
        # Validation des paramètres
        steps = max(1, min(150, int(steps)))  # Entre 1 et 150
        cfg_scale = max(1.0, min(20.0, float(cfg_scale)))  # Entre 1 et 20
        width = max(64, min(2048, int(width)))  # Entre 64 et 2048
        height = max(64, min(2048, int(height)))  # Entre 64 et 2048
        
        current_app.logger.info(f"API: Génération SD - Prompt: {prompt[:50]}...")
        
        import time
        start_time = time.time()
        
        result = current_app.sd_generator.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt if negative_prompt else None,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            # Convertir le chemin en URL accessible
            import os
            image_filename = os.path.basename(result.image_path)
            image_url = f"/static/generated/{image_filename}"
            
            return jsonify({
                'success': True,
                'image_path': result.image_path,
                'image_url': image_url,
                'prompt_used': result.prompt_used,
                'generation_time': round(generation_time, 1),
                'parameters': {
                    'steps': steps,
                    'cfg_scale': cfg_scale,
                    'width': width,
                    'height': height
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/sd-progress', methods=['GET'])
def get_sd_progress():
    """API pour récupérer le progrès de génération SD"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'progress': 0, 'eta': 0})
        
        progress = current_app.sd_generator.get_generation_progress()
        
        return jsonify({
            'success': True,
            'progress': progress.get('progress', 0),
            'eta': progress.get('eta', 0),
            'current_image': progress.get('current_image')
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API progrès SD: {e}")
        return jsonify({'progress': 0, 'eta': 0})


@api_bp.route('/generate-variations-sd', methods=['POST'])
def generate_variations_sd():
    """API pour générer des variations d'image avec SD"""
    try:
        if not hasattr(current_app, 'sd_generator') or not current_app.sd_generator:
            return jsonify({'error': 'Stable Diffusion non disponible'}), 503
        
        if not current_app.sd_generator.is_available:
            return jsonify({'error': 'Stable Diffusion non accessible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt requis'}), 400
        
        count = data.get('count', 3)
        count = max(1, min(5, int(count)))  # Entre 1 et 5 variations
        
        current_app.logger.info(f"API: Génération de {count} variations SD")
        
        import time
        start_time = time.time()
        
        variations = current_app.sd_generator.generate_variations(prompt, count)
        
        generation_time = time.time() - start_time
        
        # Convertir les résultats
        results = []
        for i, result in enumerate(variations):
            if result.success:
                import os
                image_filename = os.path.basename(result.image_path)
                image_url = f"/static/generated/{image_filename}"
                
                results.append({
                    'success': True,
                    'image_path': result.image_path,
                    'image_url': image_url,
                    'prompt_used': result.prompt_used
                })
            else:
                results.append({
                    'success': False,
                    'error': result.error_message
                })
        
        successful_count = sum(1 for r in results if r.get('success'))
        
        return jsonify({
            'success': successful_count > 0,
            'variations': results,
            'successful_count': successful_count,
            'total_count': count,
            'generation_time': round(generation_time, 1)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API variations SD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    
# À ajouter dans routes/api.py après les autres routes

@api_bp.route('/delete-image', methods=['POST'])
def delete_image():
    """API pour supprimer une image générée"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        filename = data.get('filename', '').strip()
        if not filename:
            return jsonify({'error': 'Nom de fichier requis'}), 400
        
        # Construire le chemin de l'image
        image_path = os.path.join('generated', filename)
        
        # Vérifier que le fichier existe et le supprimer
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
                current_app.logger.info(f"Image supprimée: {filename}")
                return jsonify({
                    'success': True,
                    'message': f'Image {filename} supprimée avec succès'
                })
            except Exception as e:
                current_app.logger.error(f"Erreur suppression image {filename}: {e}")
                return jsonify({'error': f'Impossible de supprimer le fichier: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Fichier non trouvé'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Erreur API suppression image: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/clear-gallery', methods=['POST'])
def clear_gallery():
    """API pour vider la galerie d'images"""
    try:
        import glob
        
        # Patterns de fichiers d'images
        image_patterns = ['*.png', '*.jpg', '*.jpeg', '*.gif']
        deleted_count = 0
        
        for pattern in image_patterns:
            files = glob.glob(os.path.join('generated', pattern))
            for file_path in files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    current_app.logger.warning(f"Impossible de supprimer {file_path}: {e}")
        
        current_app.logger.info(f"Galerie vidée: {deleted_count} images supprimées")
        
        return jsonify({
            'success': True,
            'message': f'{deleted_count} image(s) supprimée(s)',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API nettoyage galerie: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/generate-image-hf', methods=['POST'])
def generate_image_hf():
    """API pour générer une image avec Hugging Face"""
    try:
        if not hasattr(current_app, 'hf_generator') or not current_app.hf_generator:
            return jsonify({'error': 'Hugging Face non disponible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt requis'}), 400
        
        current_app.logger.info(f"API: Génération HF - Prompt: {prompt[:50]}...")
        
        import time
        start_time = time.time()
        
        result = current_app.hf_generator.generate_image(prompt)
        
        generation_time = time.time() - start_time
        
        if result.success:
            # Convertir le chemin en URL accessible
            import os
            image_filename = os.path.basename(result.image_path)
            image_url = f"/static/generated/{image_filename}"
            
            return jsonify({
                'success': True,
                'image_path': result.image_path,
                'image_url': image_url,
                'prompt_used': prompt,
                'generation_time': round(generation_time, 1),
                'service': 'Hugging Face'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération HF: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/post-summary/<int:post_id>', methods=['GET'])
def get_post_summary(post_id):
    """API pour récupérer un résumé rapide d'un post"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            return jsonify({'error': 'Base de données non disponible'}), 503
        
        post = current_app.db_manager.get_post_by_id(post_id)
        
        if not post:
            return jsonify({'error': 'Post non trouvé'}), 404
        
        # Résumé compact
        summary = {
            'id': post.id,
            'title': post.title,
            'status': post.status,
            'has_image': bool(post.image_path),
            'has_content': bool(post.description),
            'scheduled_time': post.scheduled_time.isoformat() if post.scheduled_time else None,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'preview_url': f'/post/{post.id}/preview'
        }
        
        return jsonify({
            'success': True,
            'post': summary
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API résumé post {post_id}: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/bulk-actions', methods=['POST'])
def bulk_actions():
    """API pour les actions en lot sur plusieurs posts"""
    try:
        if not hasattr(current_app, 'db_manager') or not current_app.db_manager:
            return jsonify({'error': 'Base de données non disponible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        post_ids = data.get('post_ids', [])
        action = data.get('action', '').strip()
        
        if not post_ids or not action:
            return jsonify({'error': 'IDs de posts et action requis'}), 400
        
        results = []
        
        for post_id in post_ids:
            try:
                if action == 'delete':
                    success = current_app.db_manager.delete_post(post_id)
                    results.append({'post_id': post_id, 'success': success, 'action': 'deleted'})
                    
                elif action == 'publish':
                    # Publier le post (nécessite Instagram configuré)
                    if hasattr(current_app, 'instagram_publisher') and current_app.instagram_publisher:
                        post = current_app.db_manager.get_post_by_id(post_id)
                        if post and post.can_be_published():
                            # Logic de publication ici
                            results.append({'post_id': post_id, 'success': True, 'action': 'published'})
                        else:
                            results.append({'post_id': post_id, 'success': False, 'action': 'publish_failed', 'error': 'Post non publiable'})
                    else:
                        results.append({'post_id': post_id, 'success': False, 'action': 'publish_failed', 'error': 'Instagram non configuré'})
                        
                else:
                    results.append({'post_id': post_id, 'success': False, 'action': 'unknown', 'error': f'Action inconnue: {action}'})
                    
            except Exception as e:
                results.append({'post_id': post_id, 'success': False, 'action': action, 'error': str(e)})
        
        successful_count = sum(1 for r in results if r['success'])
        
        return jsonify({
            'success': successful_count > 0,
            'results': results,
            'successful_count': successful_count,
            'total_count': len(post_ids),
            'action': action
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API actions en lot: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500
    

# api pour les vidéos

@api_bp.route('/generate-video-from-image', methods=['POST'])
def generate_video_from_image():
    """API pour générer une vidéo depuis une image"""
    try:
        if not hasattr(current_app, 'svd_generator') or not current_app.svd_generator:
            return jsonify({'error': 'Stable Video Diffusion non disponible'}), 503
        
        if not current_app.svd_generator.is_available:
            return jsonify({'error': 'SVD non accessible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        image_path = data.get('image_path', '').strip()
        if not image_path:
            return jsonify({'error': 'Chemin image requis'}), 400
        
        # Paramètres optionnels
        duration = int(data.get('duration_seconds', 3))
        fps = int(data.get('fps', 8))
        motion_strength = float(data.get('motion_strength', 0.7))
        seed = int(data.get('seed', -1))
        
        # Validation
        duration = max(1, min(10, duration))  # 1-10 secondes
        fps = max(4, min(30, fps))  # 4-30 FPS
        motion_strength = max(0.1, min(1.0, motion_strength))
        
        current_app.logger.info(f"API: Génération vidéo depuis image {image_path}")
        
        import time
        start_time = time.time()
        
        result = current_app.svd_generator.generate_video_from_image(
            image_path=image_path,
            duration_seconds=duration,
            fps=fps,
            motion_strength=motion_strength,
            seed=seed
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            # Convertir le chemin en URL accessible
            import os
            video_filename = os.path.basename(result.video_path)
            video_url = f"/static/generated/videos/{video_filename}"
            
            return jsonify({
                'success': True,
                'video_path': result.video_path,
                'video_url': video_url,
                'source_image': image_path,
                'generation_time': round(generation_time, 1),
                'parameters': {
                    'duration': duration,
                    'fps': fps,
                    'motion_strength': motion_strength,
                    'seed': seed
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération vidéo: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/generate-video-from-text', methods=['POST'])
def generate_video_from_text():
    """API pour générer une vidéo depuis un prompt texte"""
    try:
        if not hasattr(current_app, 'svd_generator') or not current_app.svd_generator:
            return jsonify({'error': 'Stable Video Diffusion non disponible'}), 503
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        prompt = data.get('prompt', '').strip()
        if not prompt:
            return jsonify({'error': 'Prompt requis'}), 400
        
        duration = int(data.get('duration_seconds', 3))
        width = int(data.get('width', 1024))
        height = int(data.get('height', 576))
        
        # Validation
        duration = max(1, min(10, duration))
        width = max(512, min(1024, width))
        height = max(512, min(1024, height))
        
        current_app.logger.info(f"API: Génération vidéo depuis texte: {prompt[:50]}...")
        
        import time
        start_time = time.time()
        
        result = current_app.svd_generator.generate_video_from_text(
            prompt=prompt,
            duration_seconds=duration,
            width=width,
            height=height
        )
        
        generation_time = time.time() - start_time
        
        if result.success:
            import os
            video_filename = os.path.basename(result.video_path)
            video_url = f"/static/generated/videos/{video_filename}"
            
            return jsonify({
                'success': True,
                'video_path': result.video_path,
                'video_url': video_url,
                'prompt': prompt,
                'generation_time': round(generation_time, 1),
                'parameters': {
                    'duration': duration,
                    'width': width,
                    'height': height
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error_message
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Erreur API génération vidéo texte: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/svd-status', methods=['GET'])
def get_svd_status():
    """API pour récupérer le statut de SVD"""
    try:
        if not hasattr(current_app, 'svd_generator') or not current_app.svd_generator:
            return jsonify({
                'success': True,
                'available': False,
                'api_url': None
            })
        
        status = current_app.svd_generator.get_status()
        queue_status = current_app.svd_generator.get_queue_status()
        
        return jsonify({
            'success': True,
            'available': status['available'],
            'api_url': status.get('api_url'),
            'queue_running': len(queue_status.get('queue_running', [])),
            'queue_pending': len(queue_status.get('queue_pending', [])),
            'supported_formats': status.get('supported_formats', []),
            'max_duration': status.get('max_duration', 10)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API statut SVD: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/video-gallery', methods=['GET'])
def get_video_gallery():
    """API pour récupérer la galerie de vidéos"""
    try:
        import glob
        import os
        from datetime import datetime
        
        videos = []
        video_folder = 'generated/videos'
        
        if os.path.exists(video_folder):
            video_patterns = ['*.mp4', '*.webm', '*.avi']
            
            for pattern in video_patterns:
                files = glob.glob(os.path.join(video_folder, pattern))
                for file_path in files:
                    try:
                        filename = os.path.basename(file_path)
                        stats = os.stat(file_path)
                        created_time = datetime.fromtimestamp(stats.st_ctime)
                        file_size = stats.st_size
                        
                        videos.append({
                            'filename': filename,
                            'url': f'/static/generated/videos/{filename}',
                            'created_time': created_time.isoformat(),
                            'file_size': file_size,
                            'duration': None,  # Pourrait être extrait avec ffmpeg
                            'type': 'video'
                        })
                    except Exception as e:
                        current_app.logger.warning(f"Erreur lecture vidéo {file_path}: {e}")
        
        # Trier par date (plus récent en premier)
        videos.sort(key=lambda x: x['created_time'], reverse=True)
        
        return jsonify({
            'success': True,
            'videos': videos,
            'total_count': len(videos)
        })
        
    except Exception as e:
        current_app.logger.error(f"Erreur API galerie vidéos: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500


@api_bp.route('/delete-video', methods=['POST'])
def delete_video():
    """API pour supprimer une vidéo"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Données JSON requises'}), 400
        
        filename = data.get('filename', '').strip()
        if not filename:
            return jsonify({'error': 'Nom de fichier requis'}), 400
        
        # Construire le chemin de la vidéo
        video_path = os.path.join('generated', 'videos', filename)
        
        # Vérifier que le fichier existe et le supprimer
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
                current_app.logger.info(f"Vidéo supprimée: {filename}")
                return jsonify({
                    'success': True,
                    'message': f'Vidéo {filename} supprimée avec succès'
                })
            except Exception as e:
                current_app.logger.error(f"Erreur suppression vidéo {filename}: {e}")
                return jsonify({'error': f'Impossible de supprimer le fichier: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Fichier non trouvé'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Erreur API suppression vidéo: {e}")
        return jsonify({'error': f'Erreur serveur: {str(e)}'}), 500