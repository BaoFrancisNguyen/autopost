# services/local_image_generator.py - Alternative locale pour les images (optionnel)
class LocalImageGenerator:
    """
    Générateur d'images locales - Pour une future intégration avec Stable Diffusion
    ou d'autres solutions locales
    """
    
    def __init__(self):
        print("ℹ️  Générateur d'images local - En développement")
        print("💡 Pour les images, vous pouvez :")
        print("   - Utiliser DALL-E avec une clé OpenAI")
        print("   - Intégrer Stable Diffusion localement")
        print("   - Uploader des images manuellement")
    
    def generate_placeholder(self, prompt: str, size: str = "1024x1024"):
        """Génère une image placeholder"""
        # Pour l'instant, retourne None
        # Dans le futur, pourrait intégrer Stable Diffusion ou autre
        return None