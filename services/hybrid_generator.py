# services/hybrid_generator.py - Service hybride Ollama + DALL-E
class HybridAIGenerator:
    """Générateur hybride utilisant Ollama pour le texte et DALL-E pour les images"""
    
    def __init__(self, openai_api_key: str = None, ollama_url: str = "http://localhost:11434", 
                 ollama_model: str = "mistral:latest"):
        """
        Initialise le générateur hybride
        
        Args:
            openai_api_key: Clé OpenAI pour DALL-E (optionnel)
            ollama_url: URL d'Ollama pour le contenu texte
            ollama_model: Modèle Ollama à utiliser
        """
        # Service de contenu avec Ollama
        self.content_generator = OllamaContentGenerator(ollama_url, ollama_model)
        
        # Service d'images avec OpenAI (si disponible)
        self.image_generator = None
        if openai_api_key:
            try:
                from services.ai_generator import AIImageGenerator
                self.image_generator = AIImageGenerator(openai_api_key)
                print("✅ Service d'images OpenAI/DALL-E activé")
            except ImportError:
                print("⚠️  Service d'images OpenAI non disponible")
        else:
            print("ℹ️  Pas de clé OpenAI - Images non générées automatiquement")
    
    def generate_content(self, topic: str, tone: str = "engageant", 
                        additional_context: str = None) -> ContentGenerationResult:
        """Génère du contenu avec Ollama"""
        return self.content_generator.generate_description_and_hashtags(topic, tone, additional_context)
    
    def generate_image(self, prompt: str, size: str = "720x720"):
        """Génère une image avec DALL-E si disponible"""
        if self.image_generator:
            return self.image_generator.generate_image(prompt, size)
        else:
            print("⚠️  Génération d'images non disponible (pas de clé OpenAI)")
            return None
    
    def get_status(self) -> dict:
        """Retourne le statut des services"""
        return {
            'content_generator': self.content_generator is not None,
            'image_generator': self.image_generator is not None,
            'ollama_model': self.content_generator.model if self.content_generator else None,
            'available_models': self.content_generator.get_available_models() if self.content_generator else []
        }