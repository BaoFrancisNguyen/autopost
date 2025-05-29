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
    
    # Configuration Ollama
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'mistral:latest')
    USE_OLLAMA = os.getenv('USE_OLLAMA', 'True').lower() == 'true'
    
    # Configuration OpenAI (optionnel maintenant)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Configuration Stable Diffusion (NOUVEAU)
    USE_STABLE_DIFFUSION = os.getenv('USE_STABLE_DIFFUSION', 'True').lower() == 'true'
    STABLE_DIFFUSION_URL = os.getenv('STABLE_DIFFUSION_URL', 'http://localhost:7862')
    SD_DEFAULT_STEPS = int(os.getenv('SD_DEFAULT_STEPS', '20'))
    SD_DEFAULT_CFG_SCALE = float(os.getenv('SD_DEFAULT_CFG_SCALE', '7.0'))
    SD_DEFAULT_SIZE = os.getenv('SD_DEFAULT_SIZE', '1024x1024')
    
    # Configuration Hugging Face (alternative gratuite)
    HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')
    USE_HUGGINGFACE = os.getenv('USE_HUGGINGFACE', 'False').lower() == 'true'
    
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
        
        print(f"   🎨 Stable Diffusion: {'✅ Activé' if Config.USE_STABLE_DIFFUSION else '❌ Désactivé'}")
        if Config.USE_STABLE_DIFFUSION:
            print(f"   🖼️  URL: {Config.STABLE_DIFFUSION_URL}")
            print(f"   ⚙️  Étapes par défaut: {Config.SD_DEFAULT_STEPS}")
        
        print(f"   🤗 Hugging Face: {'✅ Activé' if Config.USE_HUGGINGFACE else '❌ Désactivé'}")
    
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
        
        # Validation Stable Diffusion si activé
        if Config.USE_STABLE_DIFFUSION:
            try:
                import requests
                response = requests.get(f"{Config.STABLE_DIFFUSION_URL}/sdapi/v1/options", timeout=5)
                if response.status_code == 200:
                    print(f"✅ Stable Diffusion connecté sur {Config.STABLE_DIFFUSION_URL}")
                else:
                    warnings.append(f'Stable Diffusion non accessible sur {Config.STABLE_DIFFUSION_URL}')
            except Exception as e:
                warnings.append(f'Stable Diffusion non accessible: {str(e)}')
        
        # OpenAI optionnel maintenant
        if not Config.OPENAI_API_KEY:
            warnings.append('OPENAI_API_KEY non configuré - DALL-E indisponible')
        
        # Hugging Face optionnel
        if Config.USE_HUGGINGFACE and not Config.HUGGINGFACE_API_TOKEN:
            warnings.append('HUGGINGFACE_API_TOKEN non configuré - Limites de taux plus strictes')
        
        # Instagram pour la publication
        if not Config.INSTAGRAM_ACCESS_TOKEN:
            warnings.append('INSTAGRAM_ACCESS_TOKEN non configuré - Pas de publication automatique')
        
        if not Config.INSTAGRAM_ACCOUNT_ID:
            warnings.append('INSTAGRAM_ACCOUNT_ID non configuré - Pas de publication automatique')
        
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
        
        # Instructions pour Stable Diffusion
        if Config.USE_STABLE_DIFFUSION:
            print(f"\n💡 Pour utiliser Stable Diffusion :")
            print(f"   1. Téléchargez AUTOMATIC1111 WebUI:")
            print(f"      git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui")
            print(f"   2. Démarrez avec l'API activée:")
            print(f"      ./webui.sh --api")
            print(f"      ou: python launch.py --api")
            print(f"   3. L'interface sera accessible sur {Config.STABLE_DIFFUSION_URL}")
        
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
            'use_stable_diffusion': Config.USE_STABLE_DIFFUSION,
            'stable_diffusion_url': Config.STABLE_DIFFUSION_URL,
            'use_huggingface': Config.USE_HUGGINGFACE,
            'openai_available': bool(Config.OPENAI_API_KEY),
            'content_service': 'Ollama' if Config.USE_OLLAMA else 'OpenAI',
            'image_service': 'Stable Diffusion' if Config.USE_STABLE_DIFFUSION else 'Hugging Face' if Config.USE_HUGGINGFACE else 'OpenAI DALL-E' if Config.OPENAI_API_KEY else 'Non disponible'
        }
    
    @staticmethod
    def get_sd_size_tuple():
        """Convertit la taille SD en tuple (width, height)"""
        try:
            width, height = Config.SD_DEFAULT_SIZE.split('x')
            return int(width), int(height)
        except:
            return 1024, 1024


class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    
class ProductionConfig(Config):
    """Configuration pour la production"""
    DEBUG = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # En production, utiliser des URLs externes si nécessaire
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')  # Docker
    STABLE_DIFFUSION_URL = os.getenv('STABLE_DIFFUSION_URL', 'http://stable-diffusion:7860')  # Docker
    
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