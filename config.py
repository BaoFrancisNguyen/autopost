import os
from datetime import timedelta

class Config:
    """Configuration de base pour l'application"""
    
    # Configuration Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'votre_clé_secrète_très_sécurisée')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Configuration de la base de données
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'posts.db')
    
    # Configuration des dossiers
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'uploads')
    GENERATED_FOLDER = os.getenv('GENERATED_FOLDER', 'generated')
    STATIC_FOLDER = 'static'
    TEMPLATE_FOLDER = 'templates'
    
    # Configuration Ollama (NOUVEAU)
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral:latest')
    USE_OLLAMA = os.getenv('USE_OLLAMA', 'True').lower() == 'true'
    
    # Configuration OpenAI (optionnel maintenant)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # Optionnel si USE_OLLAMA=True
    
    # Configuration Instagram
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID')
    
    # Configuration des images
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Configuration du scheduler
    SCHEDULER_CHECK_INTERVAL = 60  # secondes
    
    # Configuration DALL-E (si utilisé)
    DALLE_IMAGE_SIZE = "1024x1024"
    DALLE_QUALITY = "standard"
    DALLE_MODEL = "dall-e-3"
    
    # Configuration Ollama pour le contenu
    OLLAMA_TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.7'))
    OLLAMA_MAX_TOKENS = int(os.getenv('OLLAMA_MAX_TOKENS', '500'))
    OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', '30'))
    
    # Configuration Instagram API
    INSTAGRAM_API_VERSION = "v18.0"
    INSTAGRAM_BASE_URL = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}"
    
    @staticmethod
    def init_app(app):
        """Initialise la configuration de l'application"""
        # Créer les dossiers nécessaires
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.GENERATED_FOLDER, exist_ok=True)
        os.makedirs(Config.STATIC_FOLDER, exist_ok=True)
        os.makedirs(Config.TEMPLATE_FOLDER, exist_ok=True)
        
        # Configuration Flask
        app.config['SECRET_KEY'] = Config.SECRET_KEY
        app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
        app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
        
        print(f"🔧 Configuration initialisée:")
        print(f"   📁 Dossiers créés: uploads, generated, static, templates")
        print(f"   🤖 Ollama: {'✅ Activé' if Config.USE_OLLAMA else '❌ Désactivé'}")
        if Config.USE_OLLAMA:
            print(f"   🧠 Modèle: {Config.OLLAMA_MODEL}")
            print(f"   🌐 URL: {Config.OLLAMA_BASE_URL}")
        
    @staticmethod
    def validate_config():
        """Valide que toutes les configurations nécessaires sont présentes"""
        missing_configs = []
        warnings = []
        
        # Validation Ollama si activé
        if Config.USE_OLLAMA:
            try:
                import requests
                response = requests.get(f"{Config.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [model['name'] for model in models]
                    if Config.OLLAMA_MODEL not in model_names:
                        warnings.append(f'Modèle Ollama {Config.OLLAMA_MODEL} non trouvé. Disponibles: {model_names}')
                    else:
                        print(f"✅ Ollama connecté - Modèle {Config.OLLAMA_MODEL} disponible")
                else:
                    missing_configs.append(f'Ollama non accessible sur {Config.OLLAMA_BASE_URL}')
            except Exception as e:
                missing_configs.append(f'Erreur connexion Ollama: {str(e)}')
        else:
            # Si Ollama désactivé, OpenAI devient obligatoire pour le contenu
            if not Config.OPENAI_API_KEY:
                missing_configs.append('OPENAI_API_KEY (requis si USE_OLLAMA=False)')
        
        # OpenAI optionnel mais recommandé pour les images
        if not Config.OPENAI_API_KEY:
            warnings.append('OPENAI_API_KEY non configuré - Génération d\'images DALL-E indisponible')
        
        # Instagram toujours nécessaire pour la publication
        if not Config.INSTAGRAM_ACCESS_TOKEN:
            missing_configs.append('INSTAGRAM_ACCESS_TOKEN')
        
        if not Config.INSTAGRAM_ACCOUNT_ID:
            missing_configs.append('INSTAGRAM_ACCOUNT_ID')
        
        # Affichage des résultats
        if missing_configs:
            print("❌ Configuration manquante (critique):")
            for config in missing_configs:
                print(f"   - {config}")
        
        if warnings:
            print("⚠️  Avertissements configuration:")
            for warning in warnings:
                print(f"   - {warning}")
        
        if not missing_configs and not warnings:
            print("✅ Configuration complète et valide")
        elif not missing_configs:
            print("✅ Configuration de base valide (avec avertissements)")
        
        print(f"\n💡 Pour utiliser Ollama, assurez-vous que:")
        print(f"   1. Ollama est installé et en cours d'exécution")
        print(f"   2. Le modèle {Config.OLLAMA_MODEL} est téléchargé")
        print(f"   3. Ollama écoute sur {Config.OLLAMA_BASE_URL}")
        
        return len(missing_configs) == 0
    
    @staticmethod
    def allowed_file(filename):
        """Vérifie si l'extension du fichier est autorisée"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    
    @staticmethod
    def get_ai_config():
        """Retourne la configuration IA active"""
        return {
            'use_ollama': Config.USE_OLLAMA,
            'ollama_url': Config.OLLAMA_BASE_URL,
            'ollama_model': Config.OLLAMA_MODEL,
            'openai_available': bool(Config.OPENAI_API_KEY),
            'content_service': 'Ollama' if Config.USE_OLLAMA else 'OpenAI',
            'image_service': 'OpenAI DALL-E' if Config.OPENAI_API_KEY else 'Non disponible'
        }

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # En production, utiliser des URLs externes si nécessaire
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')  # Docker
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Configuration spécifique à la production
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        if not app.debug:
            file_handler = RotatingFileHandler('logs/instagram_automation.log', 
                                             maxBytes=10240, backupCount=10)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(logging.INFO)
            app.logger.info('Instagram Automation startup')

# Configuration par défaut
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}