#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram Automation avec Ollama
Application Flask pour automatiser les publications Instagram avec IA locale
"""

import os
import sys
import logging
import atexit
import argparse
import subprocess
import platform
from flask import Flask, jsonify
import json
from datetime import datetime
from config import Config

# Ajouter le répertoire courant au path Python
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

print("🚀 Démarrage Instagram Automation avec Ollama...")

# Imports de base
try:
    from config import Config, config
    from database import DatabaseManager
    from models import Post, PostStatus, ContentTone
    print("✅ Imports de base réussis")
except ImportError as e:
    print(f"❌ Erreur imports de base: {e}")
    sys.exit(1)


def import_services():
    """Importe tous les services disponibles (VERSION COMPLÈTE)"""
    services = {}
    
    # Service de base de données
    try:
        from database import DatabaseManager
        services['db_manager'] = DatabaseManager
        print("✅ Service base de données disponible")
    except ImportError as e:
        print(f"❌ Erreur service base de données: {e}")
        services['db_manager'] = None
    
    # Services de contenu IA (Ollama en priorité)
    try:
        if Config.USE_OLLAMA:
            from services.ollama_generator import OllamaContentGenerator
            services['ollama_content'] = OllamaContentGenerator
            print("✅ Service Ollama disponible")
        else:
            print("⚠️  Ollama désactivé dans la configuration")
            services['ollama_content'] = None
    except ImportError as e:
        print(f"⚠️  Service Ollama non disponible: {e}")
        services['ollama_content'] = None
    
    # Services OpenAI (fallback)
    try:
        from services.ai_generator import AIImageGenerator
        from services.content_generator import ContentGenerator
        services['openai_image'] = AIImageGenerator
        services['openai_content'] = ContentGenerator
        print("✅ Services OpenAI disponibles")
    except ImportError as e:
        print(f"⚠️  Services OpenAI non disponibles: {e}")
        services['openai_image'] = None
        services['openai_content'] = None
    
    # Service Stable Diffusion (images)
    try:
        from services.stable_diffusion_generator import StableDiffusionGenerator
        services['stable_diffusion'] = StableDiffusionGenerator
        print("✅ Service Stable Diffusion disponible")
    except ImportError as e:
        print(f"⚠️  Service Stable Diffusion non disponible: {e}")
        services['stable_diffusion'] = None
    
    # Service Hugging Face (images alternative)
    try:
        from services.stable_diffusion_generator import HuggingFaceGenerator
        services['huggingface'] = HuggingFaceGenerator
        print("✅ Service Hugging Face disponible")
    except ImportError as e:
        print(f"⚠️  Service Hugging Face non disponible: {e}")
        services['huggingface'] = None
    
    # Service Stable Video Diffusion (NOUVEAU)
    try:
        from services.stable_video_diffusion_generator import StableVideoDiffusionGenerator
        services['svd_generator'] = StableVideoDiffusionGenerator
        print("✅ Service Stable Video Diffusion disponible")
    except ImportError as e:
        print(f"⚠️  Service SVD non disponible: {e}")
        services['svd_generator'] = None
    
    # Service Instagram
    try:
        from services.instagram_api import InstagramPublisher
        services['instagram'] = InstagramPublisher
        print("✅ Service Instagram disponible")
    except ImportError as e:
        print(f"⚠️  Service Instagram non disponible: {e}")
        services['instagram'] = None
    
    # Scheduler
    try:
        from utils.scheduler import PostScheduler
        services['scheduler'] = PostScheduler
        print("✅ Scheduler disponible")
    except ImportError as e:
        print(f"⚠️  Scheduler non disponible: {e}")
        services['scheduler'] = None
    
    return services


def import_routes():
    """Importe les routes disponibles"""
    try:
        from routes.main import main_bp
        from routes.api import api_bp
        print("✅ Routes importées")
        return main_bp, api_bp, True
    except ImportError as e:
        print(f"⚠️  Erreur import routes: {e}")
        return create_fallback_routes()


def create_fallback_routes():
    """Crée des routes de secours"""
    from flask import Blueprint, render_template_string
    
    main_bp = Blueprint('main', __name__)
    api_bp = Blueprint('api', __name__)
    
    @main_bp.route('/')
    def index():
        return render_template_string(get_fallback_template())
    
    @api_bp.route('/status')
    def api_status():
        return jsonify({
            'status': 'running',
            'mode': 'fallback',
            'message': 'Application en mode dégradé'
        })
    
    return main_bp, api_bp, False


def get_fallback_template():
    """Template de secours"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Automation - Configuration</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .card { box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: none; }
        .gradient-text { background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
</head>
<body>
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="card">
                    <div class="card-body p-5 text-center">
                        <h1 class="display-4 gradient-text mb-4">
                            <i class="fab fa-instagram me-3"></i>Instagram Automation
                        </h1>
                        <p class="lead text-muted mb-4">Application en cours de configuration avec Ollama</p>
                        
                        <div class="row mb-4">
                            <div class="col-md-4">
                                <div class="p-3 bg-light rounded">
                                    <i class="fas fa-robot fa-2x text-primary mb-2"></i>
                                    <h6>IA Locale</h6>
                                    <small class="text-muted">Ollama + Mistral</small>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-3 bg-light rounded">
                                    <i class="fab fa-instagram fa-2x text-danger mb-2"></i>
                                    <h6>Publication</h6>
                                    <small class="text-muted">Instagram API</small>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="p-3 bg-light rounded">
                                    <i class="fas fa-clock fa-2x text-warning mb-2"></i>
                                    <h6>Automatisation</h6>
                                    <small class="text-muted">Scheduler</small>
                                </div>
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <h6><i class="fas fa-info-circle me-2"></i>Configuration Ollama</h6>
                            <ol class="text-start">
                                <li>Installer Ollama: <code>curl -fsSL https://ollama.ai/install.sh | sh</code></li>
                                <li>Démarrer Ollama: <code>ollama serve</code></li>
                                <li>Télécharger Mistral: <code>ollama pull mistral:latest</code></li>
                                <li>Redémarrer l'application</li>
                            </ol>
                        </div>
                        
                        <div class="d-flex gap-3 justify-content-center">
                            <a href="/health" class="btn btn-success">
                                <i class="fas fa-heartbeat me-2"></i>Vérifier l'état
                            </a>
                            <a href="/debug" class="btn btn-outline-primary">
                                <i class="fas fa-bug me-2"></i>Informations debug
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
    '''


def create_app(config_name='default'):
    """Factory pour créer l'application Flask"""
    
    # Créer l'application Flask
    app = Flask(__name__)
    
    # Configuration
    config_class = config.get(config_name, config['default'])
    app.config.from_object(config_class)
    config_class.init_app(app)
    
    # Configuration des logs
    setup_logging(app)
    
    # Import des services et routes
    services = import_services()
    main_bp, api_bp, routes_ok = import_routes()
    
    # Initialisation des services
    init_services(app, services)
    
    # Enregistrement des blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Routes système
    setup_system_routes(app, services, routes_ok)
    
    # Gestionnaires d'erreurs
    setup_error_handlers(app)
    
    print("✅ Application Flask créée avec succès")
    return app


def setup_logging(app):
    """Configure le système de logs"""
    if not app.debug:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = logging.FileHandler('logs/instagram_automation.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Instagram Automation startup with Ollama')

def get_active_image_service_name(app) -> str:
    """Retourne le nom du service d'images actif"""
    if hasattr(app, 'sd_generator') and app.sd_generator and getattr(app.sd_generator, 'is_available', False):
        return "Stable Diffusion"
    elif hasattr(app, 'hf_generator') and app.hf_generator:
        return "Hugging Face"
    elif hasattr(app, 'image_generator') and app.image_generator and not hasattr(app.image_generator, 'is_available'):
        return "OpenAI DALL-E"
    else:
        return "Non disponible"


def init_services(app, services):
    """Initialise tous les services de l'application (VERSION CORRIGÉE)"""
    
    # Base de données - CORRECTION
    if services.get('db_manager'):
        try:
            app.db_manager = services['db_manager'](Config.DATABASE_PATH)
            print("✅ Base de données initialisée")
        except Exception as e:
            print(f"❌ Erreur base de données: {e}")
            print("💡 Lancez: python database_fix.py pour corriger")
            app.db_manager = None
    else:
        app.db_manager = None
    
    # Services IA - CORRECTION POUR LES IMAGES
    app.content_generator = None
    app.image_generator = None
    app.sd_generator = None
    app.hf_generator = None
    
    print("\n📝 Configuration génération de contenu...")
    
    # 1. GÉNÉRATEUR DE CONTENU (Ollama en priorité)
    if Config.USE_OLLAMA and services.get('ollama_content'):
        try:
            app.content_generator = services['ollama_content'](
                base_url=Config.OLLAMA_BASE_URL,
                model=Config.OLLAMA_MODEL
            )
            print(f"✅ Générateur de contenu Ollama - Modèle: {Config.OLLAMA_MODEL}")
        except Exception as e:
            print(f"❌ Erreur services Ollama: {e}")
            # Fallback vers OpenAI si disponible
            if services.get('openai_content') and Config.OPENAI_API_KEY:
                try:
                    app.content_generator = services['openai_content'](Config.OPENAI_API_KEY)
                    print("🔄 Fallback vers OpenAI pour le contenu")
                except Exception as e2:
                    print(f"❌ Erreur fallback OpenAI: {e2}")
    elif services.get('openai_content') and Config.OPENAI_API_KEY:
        try:
            app.content_generator = services['openai_content'](Config.OPENAI_API_KEY)
            print("✅ Générateur de contenu OpenAI initialisé")
        except Exception as e:
            print(f"❌ Erreur service OpenAI: {e}")
    
    print("\n🎨 Configuration génération d'images...")
    
    # 2. GÉNÉRATEUR D'IMAGES - CORRECTION MAJEURE
    
    # A. Stable Diffusion (priorité 1 - local et gratuit)
    if Config.USE_STABLE_DIFFUSION:
        try:
            from services.stable_diffusion_generator import StableDiffusionGenerator
            
            print(f"🔄 Initialisation Stable Diffusion sur {Config.STABLE_DIFFUSION_URL}...")
            app.sd_generator = StableDiffusionGenerator(Config.STABLE_DIFFUSION_URL)
            
            # ✅ VÉRIFICATION CRITIQUE - C'est ici que ça coince normalement!
            if hasattr(app.sd_generator, 'is_available') and app.sd_generator.is_available:
                # ✅✅✅ STABLE DIFFUSION FONCTIONNE!
                app.image_generator = app.sd_generator
                print("✅✅✅ Stable Diffusion ACTIF et configuré comme générateur principal!")
                print(f"   🌐 URL: {Config.STABLE_DIFFUSION_URL}")
                
                # Afficher des infos supplémentaires
                try:
                    models = app.sd_generator.get_available_models()
                    if models:
                        print(f"   🧠 {len(models)} modèle(s) disponible(s)")
                        current_model = app.sd_generator.get_current_model()
                        print(f"   📋 Modèle actuel: {current_model}")
                except Exception as e:
                    print(f"   ⚠️  Impossible de récupérer les modèles: {e}")
            else:
                print(f"⚠️  Stable Diffusion configuré mais NON ACCESSIBLE sur {Config.STABLE_DIFFUSION_URL}")
                print(f"💡 Vérifiez que SD est démarré avec: webui-user.bat --api (Windows)")
                print(f"💡 Ou: ./webui.sh --api (Linux/Mac)")
                
        except ImportError as e:
            print(f"❌ Module Stable Diffusion manquant: {e}")
            print("💡 Le fichier services/stable_diffusion_generator.py est requis")
        except Exception as e:
            print(f"❌ Erreur Stable Diffusion: {e}")
            import traceback
            traceback.print_exc()
    
    # B. Hugging Face (priorité 2 - gratuit en ligne)
    if Config.USE_HUGGINGFACE and not app.image_generator:
        try:
            from services.stable_diffusion_generator import HuggingFaceGenerator
            app.hf_generator = HuggingFaceGenerator(Config.HUGGINGFACE_API_TOKEN)
            app.image_generator = app.hf_generator
            print("✅ Hugging Face configuré comme générateur d'images")
        except ImportError as e:
            print(f"❌ Module Hugging Face manquant: {e}")
        except Exception as e:
            print(f"❌ Erreur Hugging Face: {e}")
    
    # C. OpenAI DALL-E (priorité 3 - payant mais fiable)
    if Config.OPENAI_API_KEY and not app.image_generator:
        try:
            import openai
            from services.ai_generator import AIImageGenerator
            openai_generator = AIImageGenerator(Config.OPENAI_API_KEY)
            app.image_generator = openai_generator
            print("✅ OpenAI DALL-E configuré comme générateur d'images")
        except ImportError:
            print("❌ Module OpenAI manquant")
            print("💡 Installez avec: pip install openai")
        except Exception as e:
            print(f"❌ Erreur OpenAI: {e}")
    
    # D. GÉNÉRATEUR PLACEHOLDER si aucun service disponible
    if not app.image_generator:
        print("⚠️  Aucun service de génération d'images disponible")
        print("💡 Pour activer la génération d'images:")
        print("   1. Stable Diffusion: Démarrez l'interface web avec --api")
        print("   2. Hugging Face: Ajoutez HUGGINGFACE_API_TOKEN=your_token dans .env")
        print("   3. OpenAI: Installez openai et ajoutez OPENAI_API_KEY dans .env")
        
        # Créer un générateur factice pour éviter les erreurs
        class PlaceholderImageGenerator:
            def generate_image(self, prompt, **kwargs):
                from models import ImageGenerationResult
                return ImageGenerationResult.error_result(
                    "Aucun service de génération d'images configuré", 
                    service_used="placeholder"
                )
            
            def validate_prompt(self, prompt):
                return True, "OK"
        
        app.image_generator = PlaceholderImageGenerator()
        print("🔧 Générateur placeholder créé (pas de génération réelle)")
    
    # Résumé du service d'images actif
    def get_active_service():
        if hasattr(app, 'sd_generator') and app.sd_generator and getattr(app.sd_generator, 'is_available', False):
            return "Stable Diffusion"
        elif hasattr(app, 'hf_generator') and app.hf_generator:
            return "Hugging Face"
        elif hasattr(app, 'image_generator') and app.image_generator and not hasattr(app.image_generator, 'is_available'):
            return "OpenAI DALL-E"
        else:
            return "Placeholder (aucun service actif)"
    
    service_name = get_active_service()
    print(f"🎨 Service d'images actif: {service_name}")
    
    # Service Instagram
    if services.get('instagram') and Config.INSTAGRAM_ACCESS_TOKEN and Config.INSTAGRAM_ACCOUNT_ID:
        try:
            app.instagram_publisher = services['instagram'](
                Config.INSTAGRAM_ACCESS_TOKEN,
                Config.INSTAGRAM_ACCOUNT_ID
            )
            print("✅ Service Instagram initialisé")
        except Exception as e:
            print(f"❌ Erreur service Instagram: {e}")
            app.instagram_publisher = None
    else:
        app.instagram_publisher = None
        missing_config = []
        if not Config.INSTAGRAM_ACCESS_TOKEN:
            missing_config.append("INSTAGRAM_ACCESS_TOKEN")
        if not Config.INSTAGRAM_ACCOUNT_ID:
            missing_config.append("INSTAGRAM_ACCOUNT_ID")
        if missing_config:
            print(f"⚠️  Configuration Instagram manquante: {', '.join(missing_config)}")
    
    print("\n⏰ Configuration Scheduler...")
    
    # Scheduler
    if services.get('scheduler') and app.db_manager:
        try:
            app.scheduler = services['scheduler'](app.db_manager, app.instagram_publisher)
            
            # Callbacks du scheduler
            def on_post_published(post, result):
                app.logger.info(f"📸 Post publié automatiquement: {post.title}")
            
            def on_post_failed(post, error):
                app.logger.error(f"❌ Échec publication automatique: {post.title} - {error}")
            
            def on_scheduler_error(error):
                app.logger.error(f"🚨 Erreur scheduler: {error}")
            
            app.scheduler.set_callbacks(on_post_published, on_post_failed, on_scheduler_error)
            app.scheduler.start()
            print("✅ Scheduler démarré")
        except Exception as e:
            print(f"❌ Erreur scheduler: {e}")
            app.scheduler = None
    else:
        app.scheduler = None
        if not app.db_manager:
            print("⚠️  Scheduler nécessite la base de données")
    
    # RÉSUMÉ FINAL
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES SERVICES")
    print("=" * 50)
    
    services_status = {
        'Base de données': '✅' if app.db_manager else '❌',
        'Contenu (IA)': '✅' if app.content_generator else '❌',
        'Images (IA)': '✅' if app.image_generator and not isinstance(app.image_generator, type(app.image_generator)) or hasattr(app.image_generator, 'api_key') or (hasattr(app.image_generator, 'is_available') and app.image_generator.is_available) else '❌',
        'Instagram': '✅' if app.instagram_publisher else '⚠️',
        'Scheduler': '✅' if app.scheduler else '⚠️'
    }
    
    for service, status in services_status.items():
        print(f"{status} {service}")
    
    # Service IA actif
    ai_services = []
    if app.content_generator:
        if hasattr(app.content_generator, 'model'):
            ai_services.append(f"Contenu: Ollama ({app.content_generator.model})")
        else:
            ai_services.append("Contenu: OpenAI")
    
    if app.image_generator:
        if hasattr(app.image_generator, 'is_available'):
            if app.sd_generator and app.sd_generator.is_available:
                ai_services.append("Images: Stable Diffusion")
            elif app.hf_generator:
                ai_services.append("Images: Hugging Face")
        elif hasattr(app.image_generator, 'api_key'):
            ai_services.append("Images: OpenAI DALL-E")
        else:
            ai_services.append("Images: Non disponible")
    
    if ai_services:
        print(f"\n🎯 Services IA actifs: {', '.join(ai_services)}")
    else:
        print(f"\n⚠️  Aucun service IA actif")
    
    # Score
    active_count = sum(1 for status in services_status.values() if status == '✅')
    total_count = len(services_status)
    print(f"\n📈 Score: {active_count}/{total_count} services actifs")
    
    if active_count >= 4:
        print("✅ Configuration complète")
    elif active_count >= 2:
        print("⚠️  Configuration minimale - Certaines fonctionnalités limitées")
    else:
        print("❌ Configuration insuffisante")

    # 3. GÉNÉRATEUR DE VIDÉOS - STABLE VIDEO DIFFUSION
    app.svd_generator = None
    
    if Config.USE_STABLE_VIDEO_DIFFUSION:
        try:
            from services.stable_video_diffusion_generator import StableVideoDiffusionGenerator
            app.svd_generator = StableVideoDiffusionGenerator(Config.SVD_API_URL)
            
            if app.svd_generator.is_available:
                print("✅ Stable Video Diffusion configuré et accessible")
                
                # Test rapide de la queue
                try:
                    queue_status = app.svd_generator.get_queue_status()
                    running_jobs = len(queue_status.get('queue_running', []))
                    pending_jobs = len(queue_status.get('queue_pending', []))
                    print(f"   📊 Queue: {running_jobs} en cours, {pending_jobs} en attente")
                except Exception as e:
                    print(f"   ⚠️  Impossible de vérifier la queue: {e}")
            else:
                print(f"⚠️  Stable Video Diffusion configuré mais non accessible sur {Config.SVD_API_URL}")
                print("💡 Vérifiez que ComfyUI est démarré avec: python main.py --port 7862")
                
        except ImportError as e:
            print(f"❌ Module Stable Video Diffusion manquant: {e}")
            print("💡 Le fichier services/stable_video_diffusion_generator.py est requis")
        except Exception as e:
            print(f"❌ Erreur Stable Video Diffusion: {e}")
    else:
        print("⚠️  Stable Video Diffusion désactivé dans la configuration")
        print("💡 Pour activer : SET USE_STABLE_VIDEO_DIFFUSION=True dans .env")
    
    # Si aucun générateur de vidéos n'est disponible
    if not app.svd_generator or not getattr(app.svd_generator, 'is_available', False):
        print("⚠️  Aucun service de génération de vidéos disponible")
        print("💡 Pour activer la génération de vidéos:")
        print("   1. Installez ComfyUI: git clone https://github.com/comfyanonymous/ComfyUI")
        print("   2. Téléchargez SVD: huggingface-cli download stabilityai/stable-video-diffusion-img2vid")
        print("   3. Démarrez: cd ComfyUI && python main.py --port 7862")
        print("   4. Activez dans .env: USE_STABLE_VIDEO_DIFFUSION=True")
        
        # Créer un générateur factice pour éviter les erreurs
        class PlaceholderVideoGenerator:
            def __init__(self):
                self.is_available = False
            
            def generate_video_from_image(self, *args, **kwargs):
                from models import VideoGenerationResult
                return VideoGenerationResult.error_result(
                    "Aucun service de génération de vidéos configuré"
                )
            
            def generate_video_from_text(self, *args, **kwargs):
                from models import VideoGenerationResult
                return VideoGenerationResult.error_result(
                    "Aucun service de génération de vidéos configuré"
                )
            
            def get_status(self):
                return {
                    'available': False,
                    'service': 'Non configuré'
                }
            
            def get_queue_status(self):
                return {'queue_running': [], 'queue_pending': []}
        
        app.svd_generator = PlaceholderVideoGenerator()
        print("🔧 Générateur vidéo placeholder créé")
    
    # ... (reste du code existant) ...
    
    # RÉSUMÉ FINAL (mise à jour)
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES SERVICES")
    print("=" * 50)
    
    services_status = {
        'Base de données': '✅' if app.db_manager else '❌',
        'Contenu (IA)': '✅' if app.content_generator else '❌',
        'Images (IA)': '✅' if app.image_generator and (not hasattr(app.image_generator, 'is_available') or app.image_generator.is_available) else '❌',
        'Vidéos (IA)': '✅' if app.svd_generator and getattr(app.svd_generator, 'is_available', False) else '⚠️',
        'Instagram': '✅' if app.instagram_publisher else '⚠️',
        'Scheduler': '✅' if app.scheduler else '⚠️'
    }
    
    for service, status in services_status.items():
        print(f"{status} {service}")
    
    # Services IA actifs (mise à jour)
    ai_services = []
    if app.content_generator:
        if hasattr(app.content_generator, 'model'):
            ai_services.append(f"Contenu: Ollama ({app.content_generator.model})")
        else:
            ai_services.append("Contenu: OpenAI")
    
    if app.image_generator:
        if hasattr(app.image_generator, 'is_available'):
            if hasattr(app, 'sd_generator') and app.sd_generator and app.sd_generator.is_available:
                ai_services.append("Images: Stable Diffusion")
            elif hasattr(app, 'hf_generator') and app.hf_generator:
                ai_services.append("Images: Hugging Face")
        elif hasattr(app.image_generator, 'api_key'):
            ai_services.append("Images: OpenAI DALL-E")
        else:
            ai_services.append("Images: Non disponible")
    
    if app.svd_generator and getattr(app.svd_generator, 'is_available', False):
        ai_services.append("Vidéos: Stable Video Diffusion")
    else:
        ai_services.append("Vidéos: Non disponible")
    
    if ai_services:
        print(f"\n🎯 Services IA actifs: {', '.join(ai_services)}")
    else:
        print(f"\n⚠️  Aucun service IA actif")
    
    # Score (mise à jour)
    active_count = sum(1 for status in services_status.values() if status == '✅')
    total_count = len(services_status)
    print(f"\n📈 Score: {active_count}/{total_count} services actifs")
    
    if active_count >= 5:
        print("✅ Configuration complète")
    elif active_count >= 3:
        print("⚠️  Configuration fonctionnelle - Certaines fonctionnalités limitées")
    else:
        print("❌ Configuration insuffisante")


def import_services():
    """Importe les services disponibles (VERSION MISE À JOUR)"""
    services = {}
    
    # Service de base de données
    try:
        services['db_manager'] = DatabaseManager
        print("✅ Service base de données disponible")
    except Exception as e:
        print(f"❌ Erreur service base de données: {e}")
        services['db_manager'] = None
    
    # Services IA
    try:
        if Config.USE_OLLAMA:
            from services.ollama_generator import OllamaContentGenerator
            services['ollama_content'] = OllamaContentGenerator
            print("✅ Service Ollama disponible")
        else:
            print("⚠️  Ollama désactivé dans la configuration")
    except ImportError as e:
        print(f"⚠️  Service Ollama non disponible: {e}")
        services['ollama_content'] = None
    
    # Services OpenAI (fallback)
    try:
        from services.ai_generator import AIImageGenerator
        from services.content_generator import ContentGenerator
        services['openai_image'] = AIImageGenerator
        services['openai_content'] = ContentGenerator
        print("✅ Services OpenAI disponibles")
    except ImportError as e:
        print(f"⚠️  Services OpenAI non disponibles: {e}")
        services['openai_image'] = None
        services['openai_content'] = None
    
    # Service Instagram
    try:
        from services.instagram_api import InstagramPublisher
        services['instagram'] = InstagramPublisher
        print("✅ Service Instagram disponible")
    except ImportError as e:
        print(f"⚠️  Service Instagram non disponible: {e}")
        services['instagram'] = None
    
    # Scheduler
    try:
        from utils.scheduler import PostScheduler
        services['scheduler'] = PostScheduler
        print("✅ Scheduler disponible")
    except ImportError as e:
        print(f"⚠️  Scheduler non disponible: {e}")
        services['scheduler'] = None
    
    return services

def generate_debug_template(debug_data):
    """Génère le template HTML de debug"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug - Instagram Automation 2.0</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 12px; }}
            .status-ok {{ color: #28a745; }}
            .status-error {{ color: #dc3545; }}
            .status-warning {{ color: #ffc107; }}
            .service-card {{ transition: transform 0.2s; }}
            .service-card:hover {{ transform: translateY(-2px); }}
        </style>
    </head>
    <body>
        <div class="container mt-4">
            <div class="row mb-4">
                <div class="col-12">
                    <h1><i class="fas fa-bug me-3"></i>Debug - Instagram Automation 2.0</h1>
                    <p class="text-muted">Informations complètes du système avec support vidéo</p>
                </div>
            </div>
            
            <!-- Services Grid -->
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card service-card h-100">
                        <div class="card-header bg-primary text-white">
                            <h6><i class="fas fa-brain me-2"></i>Génération de Contenu</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li>Ollama: <span class="{'status-ok' if debug_data['ollama']['accessible'] else 'status-error'}">{'✅' if debug_data['ollama']['accessible'] else '❌'}</span></li>
                                <li>OpenAI: <span class="{'status-ok' if debug_data['configuration']['openai_configured'] else 'status-warning'}">{'✅' if debug_data['configuration']['openai_configured'] else '⚠️'}</span></li>
                                <li>Modèles: {len(debug_data['ollama']['models'])}</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card service-card h-100">
                        <div class="card-header bg-success text-white">
                            <h6><i class="fas fa-image me-2"></i>Génération d'Images</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li>Stable Diffusion: <span class="{'status-ok' if debug_data['configuration']['use_stable_diffusion'] else 'status-warning'}">{'✅' if debug_data['configuration']['use_stable_diffusion'] else '⚠️'}</span></li>
                                <li>Hugging Face: <span class="{'status-ok' if debug_data['configuration']['use_huggingface'] else 'status-warning'}">{'✅' if debug_data['configuration']['use_huggingface'] else '⚠️'}</span></li>
                                <li>OpenAI DALL-E: <span class="{'status-ok' if debug_data['configuration']['openai_configured'] else 'status-warning'}">{'✅' if debug_data['configuration']['openai_configured'] else '⚠️'}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card service-card h-100">
                        <div class="card-header bg-warning text-dark">
                            <h6><i class="fas fa-video me-2"></i>Génération de Vidéos</h6>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li>SVD activé: <span class="{'status-ok' if debug_data['configuration']['use_stable_video_diffusion'] else 'status-warning'}">{'✅' if debug_data['configuration']['use_stable_video_diffusion'] else '⚠️'}</span></li>
                                <li>SVD accessible: <span class="{'status-ok' if debug_data['stable_video_diffusion']['accessible'] else 'status-error'}">{'✅' if debug_data['stable_video_diffusion']['accessible'] else '❌'}</span></li>
                                <li>URL: <code>{debug_data['configuration']['svd_url']}</code></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Configuration détaillée -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-cog me-2"></i>Configuration IA</h5>
                        </div>
                        <div class="card-body">
                            <h6>Ollama</h6>
                            <ul class="list-unstyled small">
                                <li>Activé: {debug_data['configuration']['use_ollama']}</li>
                                <li>URL: <code>{debug_data['configuration']['ollama_url']}</code></li>
                                <li>Modèle: <code>{debug_data['configuration']['ollama_model']}</code></li>
                                <li>Accessible: {'✅' if debug_data['ollama']['accessible'] else '❌'}</li>
                            </ul>
                            
                            <h6>Stable Diffusion</h6>
                            <ul class="list-unstyled small">
                                <li>Activé: {debug_data['configuration']['use_stable_diffusion']}</li>
                                <li>URL: <code>{debug_data['configuration']['stable_diffusion_url']}</code></li>
                            </ul>
                            
                            <h6>Stable Video Diffusion</h6>
                            <ul class="list-unstyled small">
                                <li>Activé: {debug_data['configuration']['use_stable_video_diffusion']}</li>
                                <li>URL: <code>{debug_data['configuration']['svd_url']}</code></li>
                                <li>Accessible: {'✅' if debug_data['stable_video_diffusion']['accessible'] else '❌'}</li>
                            </ul>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-server me-2"></i>Services Application</h5>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li>Base de données: <span class="{'status-ok' if debug_data['services']['database'] else 'status-error'}">{'✅' if debug_data['services']['database'] else '❌'}</span></li>
                                <li>Générateur contenu: <span class="{'status-ok' if debug_data['services']['content_generator'] else 'status-error'}">{'✅' if debug_data['services']['content_generator'] else '❌'}</span></li>
                                <li>Générateur images: <span class="{'status-ok' if debug_data['services']['image_generator'] else 'status-warning'}">{'✅' if debug_data['services']['image_generator'] else '⚠️'}</span></li>
                                <li>Générateur vidéos: <span class="{'status-ok' if debug_data['services']['video_generator'] else 'status-warning'}">{'✅' if debug_data['services']['video_generator'] else '⚠️'}</span></li>
                                <li>Instagram: <span class="{'status-ok' if debug_data['services']['instagram'] else 'status-warning'}">{'✅' if debug_data['services']['instagram'] else '⚠️'}</span></li>
                                <li>Scheduler: <span class="{'status-ok' if debug_data['services']['scheduler'] else 'status-warning'}">{'✅' if debug_data['services']['scheduler'] else '⚠️'}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Modèles disponibles -->
            <div class="row mb-4">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-brain me-2"></i>Modèles Ollama</h5>
                        </div>
                        <div class="card-body">
                            {f'<ul class="list-unstyled">{"".join([f"<li><code>{model}</code></li>" for model in debug_data["ollama"]["models"]])}</ul>' if debug_data['ollama']['models'] else '<p class="text-muted">Aucun modèle ou Ollama non accessible</p>'}
                        </div>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-folder me-2"></i>Structure Dossiers</h5>
                        </div>
                        <div class="card-body">
                            <ul class="list-unstyled">
                                <li>generated/: <span class="{'status-ok' if debug_data['folders']['generated'] else 'status-error'}">{'✅' if debug_data['folders']['generated'] else '❌'}</span></li>
                                <li>generated/videos/: <span class="{'status-ok' if debug_data['folders']['generated_videos'] else 'status-error'}">{'✅' if debug_data['folders']['generated_videos'] else '❌'}</span></li>
                                <li>uploads/: <span class="{'status-ok' if debug_data['folders']['uploads'] else 'status-error'}">{'✅' if debug_data['folders']['uploads'] else '❌'}</span></li>
                                <li>static/: <span class="{'status-ok' if debug_data['folders']['static'] else 'status-error'}">{'✅' if debug_data['folders']['static'] else '❌'}</span></li>
                                <li>templates/: <span class="{'status-ok' if debug_data['folders']['templates'] else 'status-error'}">{'✅' if debug_data['folders']['templates'] else '❌'}</span></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Variables d'environnement -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5><i class="fas fa-env me-2"></i>Variables d'environnement</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Services IA</h6>
                            <ul class="list-unstyled small">
                                <li>USE_OLLAMA: <code>{debug_data['environment']['USE_OLLAMA']}</code></li>
                                <li>OLLAMA_BASE_URL: <code>{debug_data['environment']['OLLAMA_BASE_URL']}</code></li>
                                <li>OLLAMA_MODEL: <code>{debug_data['environment']['OLLAMA_MODEL']}</code></li>
                                <li>USE_STABLE_DIFFUSION: <code>{debug_data['environment']['USE_STABLE_DIFFUSION']}</code></li>
                                <li>USE_STABLE_VIDEO_DIFFUSION: <code>{debug_data['environment']['USE_STABLE_VIDEO_DIFFUSION']}</code></li>
                                <li>USE_HUGGINGFACE: <code>{debug_data['environment']['USE_HUGGINGFACE']}</code></li>
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>APIs et Tokens</h6>
                            <ul class="list-unstyled small">
                                <li>OPENAI_API_KEY: {debug_data['environment']['OPENAI_API_KEY']}</li>
                                <li>INSTAGRAM_ACCESS_TOKEN: {debug_data['environment']['INSTAGRAM_ACCESS_TOKEN']}</li>
                                <li>HUGGINGFACE_API_TOKEN: {debug_data['environment']['HUGGINGFACE_API_TOKEN']}</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Tests de connexion -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5><i class="fas fa-network-wired me-2"></i>Tests de connexion</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <h6>Ollama</h6>
                            <p>
                                <a href="{debug_data['ollama']['test_url']}" target="_blank" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-external-link-alt me-1"></i>Tester
                                </a>
                            </p>
                        </div>
                        <div class="col-md-4">
                            <h6>Stable Diffusion</h6>
                            <p>
                                <a href="{debug_data['configuration']['stable_diffusion_url']}" target="_blank" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-external-link-alt me-1"></i>Interface Web
                                </a>
                            </p>
                        </div>
                        <div class="col-md-4">
                            <h6>Stable Video Diffusion</h6>
                            <p>
                                {f'<a href="{debug_data["stable_video_diffusion"]["test_url"]}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="fas fa-external-link-alt me-1"></i>Tester</a>' if debug_data['stable_video_diffusion']['test_url'] else '<span class="text-muted">Non configuré</span>'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Instructions de dépannage -->
            <div class="card mb-4">
                <div class="card-header">
                    <h5><i class="fas fa-tools me-2"></i>Guide de dépannage</h5>
                </div>
                <div class="card-body">
                    <div class="accordion" id="troubleshootingAccordion">
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#ollama-help">
                                    Problèmes Ollama
                                </button>
                            </h2>
                            <div id="ollama-help" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    <ol>
                                        <li>Installer: <code>curl -fsSL https://ollama.ai/install.sh | sh</code></li>
                                        <li>Démarrer: <code>ollama serve</code></li>
                                        <li>Télécharger modèle: <code>ollama pull mistral:latest</code></li>
                                        <li>Tester: <code>curl {debug_data['ollama']['test_url']}</code></li>
                                    </ol>
                                </div>
                            </div>
                        </div>
                        
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#svd-help">
                                    Problèmes Stable Video Diffusion
                                </button>
                            </h2>
                            <div id="svd-help" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    <ol>
                                        <li>Installer ComfyUI: <code>git clone https://github.com/comfyanonymous/ComfyUI</code></li>
                                        <li>Installer dépendances: <code>cd ComfyUI && pip install -r requirements.txt</code></li>
                                        <li>Télécharger SVD: <code>huggingface-cli download stabilityai/stable-video-diffusion-img2vid-xt</code></li>
                                        <li>Démarrer avec API: <code>python main.py --port 7862</code></li>
                                        <li>Tester: <code>curl {debug_data['configuration']['svd_url']}/system_stats</code></li>
                                    </ol>
                                </div>
                            </div>
                        </div>
                        
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#gpu-help">
                                    Problèmes GPU
                                </button>
                            </h2>
                            <div id="gpu-help" class="accordion-collapse collapse">
                                <div class="accordion-body">
                                    <ul>
                                        <li>Vérifier CUDA: <code>nvidia-smi</code></li>
                                        <li>Vérifier PyTorch GPU: <code>python -c "import torch; print(torch.cuda.is_available())"</code></li>
                                        <li>VRAM recommandé: 8GB+ pour images, 12GB+ pour vidéos</li>
                                        <li>Si VRAM insuffisant: <code>--lowvram</code> pour ComfyUI</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Raw data -->
            <div class="card">
                <div class="card-header">
                    <h5><i class="fas fa-code me-2"></i>Données brutes (JSON)</h5>
                </div>
                <div class="card-body">
                    <pre class="small">{json.dumps(debug_data, indent=2, default=str)}</pre>
                </div>
            </div>
            
            <!-- Navigation -->
            <div class="mt-4 text-center">
                <a href="/" class="btn btn-primary me-2">
                    <i class="fas fa-home me-1"></i>Accueil
                </a>
                <a href="/health" class="btn btn-success me-2">
                    <i class="fas fa-heartbeat me-1"></i>Health Check
                </a>
                <a href="/settings" class="btn btn-secondary me-2">
                    <i class="fas fa-cog me-1"></i>Paramètres
                </a>
                <button onclick="location.reload()" class="btn btn-outline-primary">
                    <i class="fas fa-sync me-1"></i>Actualiser
                </button>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''


def setup_system_routes(app, services, routes_ok):
    """Configure les routes système avec support vidéo (VERSION COMPLÈTE)"""
    
    @app.route('/health')
    def health_check():
        """Route de santé complète avec tous les services"""
        
        # Test Ollama
        ollama_status = False
        ollama_models = []
        if Config.USE_OLLAMA:
            ollama_status, ollama_models = test_ollama_connection()
        
        # Test SVD
        svd_status = False
        svd_queue_info = {}
        if hasattr(app, 'svd_generator') and app.svd_generator:
            svd_status = app.svd_generator.is_available
            if svd_status:
                try:
                    svd_queue_info = app.svd_generator.get_queue_status()
                except:
                    pass
        
        # Statut détaillé des services
        services_status = {
            'database': {
                'available': hasattr(app, 'db_manager') and app.db_manager is not None,
                'type': 'SQLite',
                'path': Config.DATABASE_PATH if hasattr(app, 'db_manager') and app.db_manager else None
            },
            'content_generator': {
                'available': hasattr(app, 'content_generator') and app.content_generator is not None,
                'service': "Ollama" if hasattr(app, 'content_generator') and hasattr(app.content_generator, 'base_url') else "OpenAI" if hasattr(app, 'content_generator') else None,
                'model': Config.OLLAMA_MODEL if Config.USE_OLLAMA else None
            },
            'image_generator': {
                'available': hasattr(app, 'image_generator') and app.image_generator is not None,
                'service': get_active_image_service_name(app),
                'stable_diffusion_available': hasattr(app, 'sd_generator') and app.sd_generator and getattr(app.sd_generator, 'is_available', False),
                'huggingface_available': hasattr(app, 'hf_generator') and app.hf_generator is not None,
                'openai_available': bool(Config.OPENAI_API_KEY)
            },
            'video_generator': {
                'available': svd_status,
                'service': 'Stable Video Diffusion' if svd_status else None,
                'api_url': Config.SVD_API_URL if Config.USE_STABLE_VIDEO_DIFFUSION else None,
                'queue_running': svd_queue_info.get('queue_running', []),
                'queue_pending': svd_queue_info.get('queue_pending', []),
                'max_duration': Config.SVD_MAX_DURATION if Config.USE_STABLE_VIDEO_DIFFUSION else None
            },
            'instagram_publisher': {
                'available': hasattr(app, 'instagram_publisher') and app.instagram_publisher is not None,
                'account_id': Config.INSTAGRAM_ACCOUNT_ID if Config.INSTAGRAM_ACCOUNT_ID else None,
                'token_configured': bool(Config.INSTAGRAM_ACCESS_TOKEN)
            },
            'scheduler': {
                'available': hasattr(app, 'scheduler') and app.scheduler is not None,
                'running': hasattr(app, 'scheduler') and app.scheduler and getattr(app.scheduler, 'is_running', False),
                'check_interval': Config.SCHEDULER_CHECK_INTERVAL
            },
            'routes_loaded': routes_ok
        }
        
        # Configuration IA complète
        ai_config = {
            'content': {
                'use_ollama': Config.USE_OLLAMA,
                'ollama_url': Config.OLLAMA_BASE_URL,
                'ollama_model': Config.OLLAMA_MODEL,
                'ollama_accessible': ollama_status,
                'openai_available': bool(Config.OPENAI_API_KEY),
                'active_service': services_status['content_generator']['service']
            },
            'images': {
                'use_stable_diffusion': Config.USE_STABLE_DIFFUSION,
                'stable_diffusion_url': Config.STABLE_DIFFUSION_URL,
                'use_huggingface': Config.USE_HUGGINGFACE,
                'openai_available': bool(Config.OPENAI_API_KEY),
                'active_service': services_status['image_generator']['service']
            },
            'videos': {
                'use_stable_video_diffusion': Config.USE_STABLE_VIDEO_DIFFUSION,
                'svd_url': Config.SVD_API_URL,
                'svd_accessible': svd_status,
                'max_duration': Config.SVD_MAX_DURATION,
                'default_fps': Config.SVD_DEFAULT_FPS,
                'active_service': services_status['video_generator']['service']
            }
        }
        
        # Statistiques si disponibles
        stats = {}
        if hasattr(app, 'db_manager') and app.db_manager:
            try:
                stats = app.db_manager.get_posts_stats()
            except:
                stats = {}
        
        # Score de santé global
        total_services = len(services_status)
        available_services = sum(1 for service in services_status.values() if service.get('available', False))
        health_score = (available_services / total_services) * 100
        
        # Statut global
        if health_score >= 80:
            global_status = "excellent"
        elif health_score >= 60:
            global_status = "good"
        elif health_score >= 40:
            global_status = "fair"
        else:
            global_status = "poor"
        
        return jsonify({
            'status': 'ok',
            'global_status': global_status,
            'health_score': round(health_score, 1),
            'message': 'Instagram Automation avec IA complète (Images + Vidéos)',
            'services': services_status,
            'ai_configuration': ai_config,
            'ollama_models': ollama_models,
            'statistics': stats,
            'version': '2.0.0-video',
            'timestamp': datetime.now().isoformat(),
            'uptime': 'N/A'  # Pourrait être calculé si besoin
        })
    
    @app.route('/debug')
    def debug_info():
        """Route de debug avec informations complètes"""
        
        ollama_status, ollama_models = test_ollama_connection() if Config.USE_OLLAMA else (False, [])
        
        # Test SVD
        svd_status = False
        svd_info = {}
        if hasattr(app, 'svd_generator') and app.svd_generator:
            svd_status = app.svd_generator.is_available
            if svd_status:
                try:
                    svd_info = app.svd_generator.get_status()
                except:
                    pass
        
        debug_data = {
            'system': {
                'python_version': sys.version,
                'current_dir': current_dir,
                'files': [f for f in os.listdir(current_dir) if not f.startswith('.')],
                'python_path': sys.path[:3],
                'platform': platform.system(),
                'architecture': platform.machine()
            },
            'configuration': {
                'use_ollama': Config.USE_OLLAMA,
                'ollama_url': Config.OLLAMA_BASE_URL,
                'ollama_model': Config.OLLAMA_MODEL,
                'use_stable_diffusion': Config.USE_STABLE_DIFFUSION,
                'stable_diffusion_url': Config.STABLE_DIFFUSION_URL,
                'use_stable_video_diffusion': Config.USE_STABLE_VIDEO_DIFFUSION,
                'svd_url': Config.SVD_API_URL,
                'use_huggingface': Config.USE_HUGGINGFACE,
                'openai_configured': bool(Config.OPENAI_API_KEY),
                'instagram_configured': bool(Config.INSTAGRAM_ACCESS_TOKEN and Config.INSTAGRAM_ACCOUNT_ID)
            },
            'ollama': {
                'accessible': ollama_status,
                'models': ollama_models,
                'test_url': f"{Config.OLLAMA_BASE_URL}/api/tags"
            },
            'stable_video_diffusion': {
                'accessible': svd_status,
                'info': svd_info,
                'test_url': f"{Config.SVD_API_URL}/system_stats" if Config.USE_STABLE_VIDEO_DIFFUSION else None
            },
            'services': {
                'database': hasattr(app, 'db_manager') and app.db_manager is not None,
                'content_generator': hasattr(app, 'content_generator') and app.content_generator is not None,
                'image_generator': hasattr(app, 'image_generator') and app.image_generator is not None,
                'video_generator': hasattr(app, 'svd_generator') and app.svd_generator is not None and getattr(app.svd_generator, 'is_available', False),
                'instagram': hasattr(app, 'instagram_publisher') and app.instagram_publisher is not None,
                'scheduler': hasattr(app, 'scheduler') and app.scheduler is not None
            },
            'environment': {
                'USE_OLLAMA': os.getenv('USE_OLLAMA', 'True'),
                'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', 'mistral:latest'),
                'USE_STABLE_DIFFUSION': os.getenv('USE_STABLE_DIFFUSION', 'True'),
                'STABLE_DIFFUSION_URL': os.getenv('STABLE_DIFFUSION_URL', 'http://localhost:7861'),
                'USE_STABLE_VIDEO_DIFFUSION': os.getenv('USE_STABLE_VIDEO_DIFFUSION', 'False'),
                'SVD_API_URL': os.getenv('SVD_API_URL', 'http://localhost:7862'),
                'USE_HUGGINGFACE': os.getenv('USE_HUGGINGFACE', 'False'),
                'OPENAI_API_KEY': '✅ Configuré' if os.getenv('OPENAI_API_KEY') else '❌ Non configuré',
                'INSTAGRAM_ACCESS_TOKEN': '✅ Configuré' if os.getenv('INSTAGRAM_ACCESS_TOKEN') else '❌ Non configuré',
                'HUGGINGFACE_API_TOKEN': '✅ Configuré' if os.getenv('HUGGINGFACE_API_TOKEN') else '❌ Non configuré'
            },
            'folders': {
                'generated': os.path.exists('generated'),
                'generated_videos': os.path.exists('generated/videos'),
                'uploads': os.path.exists('uploads'),
                'static': os.path.exists('static'),
                'templates': os.path.exists('templates')
            }
        }
        
        # Template de debug amélioré
        debug_template = generate_debug_template(debug_data)
        return debug_template


def setup_error_handlers(app):
    """Configure les gestionnaires d'erreurs"""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Page non trouvée'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Erreur serveur: {error}')
        return jsonify({'error': 'Erreur interne du serveur'}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Exception non gérée: {e}')
        return jsonify({'error': 'Erreur inattendue'}), 500


def test_ollama_connection():
    """Test la connexion à Ollama et retourne les modèles (VERSION AMÉLIORÉE)"""
    try:
        import requests
        response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            
            # Test rapide de génération si le modèle configuré existe
            if Config.OLLAMA_MODEL in models:
                try:
                    test_response = requests.post(
                        f"{Config.OLLAMA_BASE_URL}/api/generate",
                        json={
                            "model": Config.OLLAMA_MODEL,
                            "prompt": "Hello",
                            "stream": False
                        },
                        timeout=15
                    )
                    if test_response.status_code == 200:
                        print(f"✅ Test génération Ollama réussi avec {Config.OLLAMA_MODEL}")
                except Exception as e:
                    print(f"⚠️  Test génération Ollama échoué: {e}")
            
            return True, models
        return False, []
    except Exception as e:
        print(f"❌ Test connexion Ollama échoué: {e}")
        return False, []


def create_required_directories():
    """Crée tous les dossiers nécessaires (VERSION COMPLÈTE)"""
    directories = [
        'templates', 'static', 'uploads', 'generated', 'generated/videos', 'logs',
        'services', 'routes', 'utils', 'static/temp', 'static/generated'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Dossier {directory} créé")
    
    # Créer les fichiers __init__.py
    init_files = ['services/__init__.py', 'routes/__init__.py', 'utils/__init__.py']
    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'# {init_file}\n')
            print(f"✅ Fichier {init_file} créé")
    
    # Créer un .gitkeep pour les dossiers vides
    gitkeep_dirs = ['generated/videos', 'uploads', 'static/temp']
    for dir_path in gitkeep_dirs:
        gitkeep_file = os.path.join(dir_path, '.gitkeep')
        if not os.path.exists(gitkeep_file):
            with open(gitkeep_file, 'w') as f:
                f.write('# Garde ce dossier dans Git\n')


def create_env_file():
    """Crée un fichier .env complet avec toutes les variables (VERSION MISE À JOUR)"""
    if not os.path.exists('.env') and not os.path.exists('.env.example'):
        env_content = '''# Configuration Instagram Automation 2.0 avec IA complète

# === SERVICES IA - CONTENU ===
USE_OLLAMA=True
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:latest
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=500
OLLAMA_TIMEOUT=30

# === SERVICES IA - IMAGES ===
USE_STABLE_DIFFUSION=True
STABLE_DIFFUSION_URL=http://localhost:7861
SD_DEFAULT_STEPS=20
SD_DEFAULT_CFG_SCALE=7.0
SD_DEFAULT_SIZE=1024x1024

USE_HUGGINGFACE=False
HUGGINGFACE_API_TOKEN=your_hf_token_here

# === SERVICES IA - VIDÉOS (NOUVEAU) ===
USE_STABLE_VIDEO_DIFFUSION=True
SVD_API_URL=http://localhost:7862
SVD_MAX_DURATION=10
SVD_DEFAULT_FPS=8
SVD_DEFAULT_MOTION=0.7

# === OPENAI (OPTIONNEL) ===
# OPENAI_API_KEY=your_openai_api_key_here

# === INSTAGRAM CONFIGURATION ===
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id

# === FLASK CONFIGURATION ===
SECRET_KEY=your_super_secret_key_change_this_in_production
FLASK_ENV=development
FLASK_DEBUG=True

# === DATABASE & STORAGE ===
DATABASE_PATH=posts.db
UPLOAD_FOLDER=uploads
GENERATED_FOLDER=generated
VIDEO_FOLDER=generated/videos

# === SCHEDULER ===
SCHEDULER_CHECK_INTERVAL=60

# === NOTES D'INSTALLATION ===
# 1. Ollama:
#    curl -fsSL https://ollama.ai/install.sh | sh
#    ollama serve
#    ollama pull mistral:latest
#
# 2. Stable Diffusion:
#    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
#    ./webui.sh --api
#
# 3. Stable Video Diffusion:
#    git clone https://github.com/comfyanonymous/ComfyUI
#    cd ComfyUI && python main.py --port 7862
#
# 4. GPU requis pour génération d'images/vidéos (8GB+ VRAM recommandé)
'''
        
        with open('.env.example', 'w') as f:
            f.write(env_content)
        print("✅ Fichier .env.example créé avec configuration complète")


def test_ollama_cli():
    """Test Ollama depuis la ligne de commande"""
    print("🧪 Test de connexion Ollama...")
    
    try:
        import requests
        
        # Test de base
        print(f"📡 Test connexion sur {Config.OLLAMA_BASE_URL}")
        response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            
            print("✅ Ollama accessible")
            print(f"📋 Modèles disponibles: {models}")
            
            if Config.OLLAMA_MODEL in models:
                print(f"✅ Modèle {Config.OLLAMA_MODEL} trouvé")
                
                # Test de génération
                print("🧠 Test de génération de contenu...")
                test_response = requests.post(
                    f"{Config.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": Config.OLLAMA_MODEL,
                        "prompt": "Écris une courte description Instagram pour un café le matin en une phrase.",
                        "stream": False
                    },
                    timeout=30
                )
                
                if test_response.status_code == 200:
                    result = test_response.json()
                    generated_text = result.get('response', 'Pas de réponse')
                    print(f"✅ Génération réussie: {generated_text[:100]}...")
                    return True
                else:
                    print(f"❌ Erreur génération: {test_response.status_code}")
                    return False
            else:
                print(f"❌ Modèle {Config.OLLAMA_MODEL} non trouvé")
                if models:
                    print(f"💡 Téléchargez-le avec: ollama pull {Config.OLLAMA_MODEL}")
                return False
        else:
            print(f"❌ Ollama non accessible: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à Ollama")
        print("💡 Vérifiez qu'Ollama est démarré avec: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False


def setup_ollama_service():
    """Guide d'installation automatique d'Ollama"""
    print("🔧 Configuration d'Ollama...")
    
    # Vérifier si Ollama est déjà installé
    try:
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama déjà installé")
            print(f"   Version: {result.stdout.strip()}")
            
            # Vérifier si le service tourne
            if test_ollama_connection()[0]:
                print("✅ Service Ollama en cours d'exécution")
                return True
            else:
                print("⚠️  Service Ollama non démarré")
                print("💡 Démarrez-le avec: ollama serve")
                return False
        else:
            print("❌ Ollama installé mais non fonctionnel")
            return False
            
    except FileNotFoundError:
        print("❌ Ollama non installé")
        
        # Instructions d'installation selon l'OS
        system = platform.system().lower()
        if system == "windows":
            print("💡 Installation Windows:")
            print("   1. Téléchargez depuis: https://ollama.ai/download/windows")
            print("   2. Ou utilisez: winget install ollama")
        elif system == "darwin":  # macOS
            print("💡 Installation macOS:")
            print("   1. curl -fsSL https://ollama.ai/install.sh | sh")
            print("   2. Ou utilisez: brew install ollama")
        else:  # Linux
            print("💡 Installation Linux:")
            print("   1. curl -fsSL https://ollama.ai/install.sh | sh")
        
        return False
    except Exception as e:
        print(f"❌ Erreur vérification Ollama: {e}")
        return False


def create_systemd_service():
    """Crée un service systemd pour Ollama (Linux seulement)"""
    if platform.system().lower() != "linux":
        print("ℹ️  Service systemd disponible uniquement sur Linux")
        return
    
    service_content = """[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
    
    print("🔧 Pour créer un service systemd:")
    print("sudo tee /etc/systemd/system/ollama.service > /dev/null << EOF")
    print(service_content)
    print("EOF")
    print("\nsudo systemctl daemon-reload")
    print("sudo systemctl enable ollama")
    print("sudo systemctl start ollama")


def download_recommended_models():
    """Télécharge les modèles recommandés"""
    recommended_models = [
        "mistral:latest",      # Modèle principal
        "llama2:7b",          # Alternative rapide
        "codellama:7b",       # Pour le code si nécessaire
    ]
    
    print("📥 Modèles recommandés pour Instagram Automation:")
    for model in recommended_models:
        print(f"   - {model}")
    
    print("\n💡 Pour télécharger:")
    for model in recommended_models:
        print(f"ollama pull {model}")


def main():
    """Point d'entrée principal"""
    
    print("=" * 60)
    print("🤖 INSTAGRAM AUTOMATION AVEC OLLAMA")
    print("=" * 60)
    
    # Créer les dossiers et fichiers nécessaires
    create_required_directories()
    create_env_file()
    
    # Charger les variables d'environnement si disponible
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Variables d'environnement chargées depuis .env")
    except ImportError:
        print("⚠️  python-dotenv non installé - Variables d'environnement depuis le système")
    
    # Valider la configuration
    print("\n🔧 Validation de la configuration...")
    try:
        config_valid = Config.validate_config()
        if not config_valid:
            print("⚠️  Configuration incomplète - L'application fonctionnera en mode limité")
    except Exception as e:
        print(f"❌ Erreur validation configuration: {e}")
    
    # Créer l'application
    print("\n🚀 Création de l'application...")
    app = create_app(os.getenv('FLASK_ENV', 'default'))
    
    # Configuration de l'arrêt propre
    def shutdown_scheduler():
        if hasattr(app, 'scheduler') and app.scheduler:
            print("🔄 Arrêt du scheduler...")
            app.scheduler.stop()
    
    atexit.register(shutdown_scheduler)
    
    # Informations de démarrage
    print("\n" + "=" * 60)
    print("🌟 APPLICATION PRÊTE")
    print("=" * 60)
    print(f"📍 URL principale: http://localhost:5000")
    print(f"🔍 Health check: http://localhost:5000/health")
    print(f"🐛 Debug info: http://localhost:5000/debug")
    print(f"🤖 Configuration IA: {'Ollama' if Config.USE_OLLAMA else 'OpenAI'}")
    
    if Config.USE_OLLAMA:
        print(f"🧠 Modèle: {Config.OLLAMA_MODEL}")
        print(f"🌐 URL Ollama: {Config.OLLAMA_BASE_URL}")
        print("\n💡 Pour utiliser Ollama:")
        print("   1. Installer: curl -fsSL https://ollama.ai/install.sh | sh")
        print("   2. Démarrer: ollama serve")
        print("   3. Télécharger le modèle: ollama pull mistral:latest")
    
    print("\n🚀 Démarrage du serveur...")
    
    # Lancer l'application
    try:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=app.config.get('DEBUG', True),
            use_reloader=False  # Éviter les problèmes avec le scheduler
        )
    except KeyboardInterrupt:
        print("\n🛑 Arrêt de l'application demandé")
    except Exception as e:
        print(f"\n❌ Erreur lors du démarrage: {e}")
    finally:
        print("👋 Application fermée")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Instagram Automation avec Ollama')
    parser.add_argument('--test-ollama', action='store_true', 
                       help='Tester la connexion Ollama')
    parser.add_argument('--setup-ollama', action='store_true',
                       help='Guide de configuration Ollama')
    parser.add_argument('--create-service', action='store_true',
                       help='Créer un service systemd (Linux)')
    parser.add_argument('--download-models', action='store_true',
                       help='Afficher les commandes pour télécharger les modèles')
    parser.add_argument('--config-check', action='store_true',
                       help='Vérifier la configuration seulement')
    
    args = parser.parse_args()
    
    if args.test_ollama:
        test_ollama_cli()
    elif args.setup_ollama:
        setup_ollama_service()
    elif args.create_service:
        create_systemd_service()
    elif args.download_models:
        download_recommended_models()
    elif args.config_check:
        print("🔧 Vérification de la configuration...")
        try:
            Config.validate_config()
            print("✅ Configuration valide")
        except Exception as e:
            print(f"❌ Erreur de configuration: {e}")
    else:
        # Lancement normal de l'application
        main()