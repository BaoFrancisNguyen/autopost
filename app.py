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
    """Importe les services disponibles"""
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
            from services.ollama_generator import OllamaContentGenerator, HybridAIGenerator
            services['ollama_content'] = OllamaContentGenerator
            services['hybrid_ai'] = HybridAIGenerator
            print("✅ Services Ollama disponibles")
        else:
            print("⚠️  Ollama désactivé dans la configuration")
    except ImportError as e:
        print(f"⚠️  Services Ollama non disponibles: {e}")
        services['ollama_content'] = None
        services['hybrid_ai'] = None
    
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


def init_services(app, services):
    """Initialise tous les services de l'application"""
    
    # Base de données
    if services.get('db_manager'):
        try:
            app.db_manager = services['db_manager'](Config.DATABASE_PATH)
            print("✅ Base de données initialisée")
        except Exception as e:
            print(f"❌ Erreur base de données: {e}")
            app.db_manager = None
    else:
        app.db_manager = None
    
    # Services IA
    app.content_generator = None
    app.image_generator = None
    app.hybrid_generator = None
    
    # Ollama en priorité si activé
    if Config.USE_OLLAMA and services.get('ollama_content'):
        try:
            app.content_generator = services['ollama_content'](
                base_url=Config.OLLAMA_BASE_URL,
                model=Config.OLLAMA_MODEL
            )
            print(f"✅ Générateur de contenu Ollama initialisé - Modèle: {Config.OLLAMA_MODEL}")
            
            # Service hybride si OpenAI disponible pour les images
            if services.get('hybrid_ai'):
                app.hybrid_generator = services['hybrid_ai'](
                    openai_api_key=Config.OPENAI_API_KEY,
                    ollama_url=Config.OLLAMA_BASE_URL,
                    ollama_model=Config.OLLAMA_MODEL
                )
                print("✅ Générateur hybride (Ollama + OpenAI) initialisé")
            
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
    
    # Générateur d'images (OpenAI uniquement pour l'instant)
    if services.get('openai_image') and Config.OPENAI_API_KEY:
        try:
            app.image_generator = services['openai_image'](Config.OPENAI_API_KEY)
            print("✅ Générateur d'images OpenAI/DALL-E initialisé")
        except Exception as e:
            print(f"❌ Erreur générateur d'images: {e}")
    
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


def setup_system_routes(app, services, routes_ok):
    """Configure les routes système"""
    
    @app.route('/health')
    def health_check():
        """Route de santé de l'application"""
        
        # Test de connexion Ollama
        ollama_status = False
        ollama_models = []
        if Config.USE_OLLAMA:
            ollama_status, ollama_models = test_ollama_connection()
        
        # Statut des services
        services_status = {
            'database': hasattr(app, 'db_manager') and app.db_manager is not None,
            'content_generator': hasattr(app, 'content_generator') and app.content_generator is not None,
            'image_generator': hasattr(app, 'image_generator') and app.image_generator is not None,
            'instagram_publisher': hasattr(app, 'instagram_publisher') and app.instagram_publisher is not None,
            'scheduler': hasattr(app, 'scheduler') and app.scheduler is not None,
            'ollama_accessible': ollama_status,
            'routes_loaded': routes_ok
        }
        
        # Configuration IA
        ai_config = {
            'use_ollama': Config.USE_OLLAMA,
            'ollama_url': Config.OLLAMA_BASE_URL,
            'ollama_model': Config.OLLAMA_MODEL,
            'ollama_accessible': ollama_status,
            'openai_available': bool(Config.OPENAI_API_KEY),
            'content_service': 'Ollama' if Config.USE_OLLAMA and ollama_status else 'OpenAI' if Config.OPENAI_API_KEY else 'Non disponible',
            'image_service': 'OpenAI DALL-E' if Config.OPENAI_API_KEY else 'Non disponible'
        }
        
        return jsonify({
            'status': 'ok',
            'message': 'Instagram Automation avec Ollama',
            'services': services_status,
            'ai_configuration': ai_config,
            'ollama_models': ollama_models,
            'version': '1.0.0-ollama'
        })
    
    @app.route('/debug')
    def debug_info():
        """Route de debug avec informations détaillées"""
        
        ollama_status, ollama_models = test_ollama_connection() if Config.USE_OLLAMA else (False, [])
        
        debug_data = {
            'system': {
                'python_version': sys.version,
                'current_dir': current_dir,
                'files': [f for f in os.listdir(current_dir) if not f.startswith('.')],
                'python_path': sys.path[:3]
            },
            'configuration': {
                'use_ollama': Config.USE_OLLAMA,
                'ollama_url': Config.OLLAMA_BASE_URL,
                'ollama_model': Config.OLLAMA_MODEL,
                'openai_configured': bool(Config.OPENAI_API_KEY),
                'instagram_configured': bool(Config.INSTAGRAM_ACCESS_TOKEN and Config.INSTAGRAM_ACCOUNT_ID)
            },
            'ollama': {
                'accessible': ollama_status,
                'models': ollama_models,
                'test_url': f"{Config.OLLAMA_BASE_URL}/api/tags"
            },
            'services': {
                'database': hasattr(app, 'db_manager') and app.db_manager is not None,
                'content_generator': hasattr(app, 'content_generator') and app.content_generator is not None,
                'image_generator': hasattr(app, 'image_generator') and app.image_generator is not None,
                'instagram': hasattr(app, 'instagram_publisher') and app.instagram_publisher is not None,
                'scheduler': hasattr(app, 'scheduler') and app.scheduler is not None
            },
            'environment': {
                'USE_OLLAMA': os.getenv('USE_OLLAMA', 'True'),
                'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                'OLLAMA_MODEL': os.getenv('OLLAMA_MODEL', 'mistral:latest'),
                'OPENAI_API_KEY': '✅ Configuré' if os.getenv('OPENAI_API_KEY') else '❌ Non configuré',
                'INSTAGRAM_ACCESS_TOKEN': '✅ Configuré' if os.getenv('INSTAGRAM_ACCESS_TOKEN') else '❌ Non configuré'
            }
        }
        
        # Template de debug
        debug_template = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Debug - Instagram Automation</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 12px; }}
                .status-ok {{ color: #28a745; }}
                .status-error {{ color: #dc3545; }}
                .status-warning {{ color: #ffc107; }}
            </style>
        </head>
        <body>
            <div class="container mt-4">
                <h1>🔍 Debug - Instagram Automation</h1>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header"><h5>🤖 Configuration IA</h5></div>
                            <div class="card-body">
                                <ul class="list-unstyled">
                                    <li>Ollama activé: <span class="{'status-ok' if debug_data['configuration']['use_ollama'] else 'status-error'}">{'✅ Oui' if debug_data['configuration']['use_ollama'] else '❌ Non'}</span></li>
                                    <li>Ollama accessible: <span class="{'status-ok' if debug_data['ollama']['accessible'] else 'status-error'}">{'✅ Oui' if debug_data['ollama']['accessible'] else '❌ Non'}</span></li>
                                    <li>Modèle: <code>{debug_data['configuration']['ollama_model']}</code></li>
                                    <li>URL: <code>{debug_data['configuration']['ollama_url']}</code></li>
                                    <li>OpenAI: <span class="{'status-ok' if debug_data['configuration']['openai_configured'] else 'status-warning'}">{'✅ Configuré' if debug_data['configuration']['openai_configured'] else '⚠️ Non configuré'}</span></li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="card mb-4">
                            <div class="card-header"><h5>📊 Services</h5></div>
                            <div class="card-body">
                                <ul class="list-unstyled">
                                    <li>Base de données: <span class="{'status-ok' if debug_data['services']['database'] else 'status-error'}">{'✅' if debug_data['services']['database'] else '❌'} {'OK' if debug_data['services']['database'] else 'Erreur'}</span></li>
                                    <li>Générateur de contenu: <span class="{'status-ok' if debug_data['services']['content_generator'] else 'status-error'}">{'✅' if debug_data['services']['content_generator'] else '❌'} {'OK' if debug_data['services']['content_generator'] else 'Erreur'}</span></li>
                                    <li>Générateur d'images: <span class="{'status-ok' if debug_data['services']['image_generator'] else 'status-warning'}">{'✅' if debug_data['services']['image_generator'] else '⚠️'} {'OK' if debug_data['services']['image_generator'] else 'Non disponible'}</span></li>
                                    <li>Instagram: <span class="{'status-ok' if debug_data['services']['instagram'] else 'status-warning'}">{'✅' if debug_data['services']['instagram'] else '⚠️'} {'OK' if debug_data['services']['instagram'] else 'Non configuré'}</span></li>
                                    <li>Scheduler: <span class="{'status-ok' if debug_data['services']['scheduler'] else 'status-warning'}">{'✅' if debug_data['services']['scheduler'] else '⚠️'} {'OK' if debug_data['services']['scheduler'] else 'Non disponible'}</span></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card mb-4">
                            <div class="card-header"><h5>🧠 Modèles Ollama</h5></div>
                            <div class="card-body">
                                {f'<ul class="list-unstyled">{"".join([f"<li><code>{model}</code></li>" for model in debug_data["ollama"]["models"]])}</ul>' if debug_data['ollama']['models'] else '<p class="text-muted">Aucun modèle trouvé ou Ollama non accessible</p>'}
                            </div>
                        </div>
                        
                        <div class="card mb-4">
                            <div class="card-header"><h5>🔧 Variables d'environnement</h5></div>
                            <div class="card-body">
                                <ul class="list-unstyled small">
                                    <li>USE_OLLAMA: <code>{debug_data['environment']['USE_OLLAMA']}</code></li>
                                    <li>OLLAMA_BASE_URL: <code>{debug_data['environment']['OLLAMA_BASE_URL']}</code></li>
                                    <li>OLLAMA_MODEL: <code>{debug_data['environment']['OLLAMA_MODEL']}</code></li>
                                    <li>OPENAI_API_KEY: {debug_data['environment']['OPENAI_API_KEY']}</li>
                                    <li>INSTAGRAM_ACCESS_TOKEN: {debug_data['environment']['INSTAGRAM_ACCESS_TOKEN']}</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header"><h5>💾 Données complètes</h5></div>
                    <div class="card-body">
                        <pre>{str(debug_data)}</pre>
                    </div>
                </div>
                
                <div class="mt-4 text-center">
                    <a href="/" class="btn btn-primary">← Retour à l'accueil</a>
                    <a href="/health" class="btn btn-success">Health Check</a>
                </div>
            </div>
        </body>
        </html>
        '''
        
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
    """Test la connexion à Ollama et retourne les modèles disponibles"""
    try:
        import requests
        response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return True, models
        return False, []
    except Exception as e:
        print(f"❌ Test connexion Ollama échoué: {e}")
        return False, []


def create_required_directories():
    """Crée les dossiers nécessaires"""
    directories = [
        'templates', 'static', 'uploads', 'generated', 'logs',
        'services', 'routes', 'utils'
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


def create_env_file():
    """Crée un fichier .env d'exemple s'il n'existe pas"""
    if not os.path.exists('.env') and not os.path.exists('.env.example'):
        env_content = '''# Configuration Instagram Automation avec Ollama

# === IA Configuration ===
USE_OLLAMA=True
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:latest
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=500

# OpenAI (optionnel - pour les images uniquement)
# OPENAI_API_KEY=your_openai_api_key_here

# === Instagram Configuration ===
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
INSTAGRAM_ACCOUNT_ID=your_instagram_business_account_id

# === Flask Configuration ===
SECRET_KEY=your_super_secret_key_change_this_in_production
FLASK_ENV=development
FLASK_DEBUG=True

# === Database & Storage ===
DATABASE_PATH=posts.db
UPLOAD_FOLDER=uploads
GENERATED_FOLDER=generated
'''
        
        with open('.env.example', 'w') as f:
            f.write(env_content)
        print("✅ Fichier .env.example créé")


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