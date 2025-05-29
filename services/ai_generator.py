import os
import requests
import openai
from datetime import datetime
from PIL import Image
from typing import Optional, Tuple, List

from config import Config
from models import ImageGenerationResult


class AIImageGenerator:
    """Générateur d'images IA utilisant DALL-E"""
    
    def __init__(self, api_key: str = None):
        """Initialise le générateur avec une clé API OpenAI"""
        self.api_key = api_key or Config.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        else:
            raise ValueError("Clé API OpenAI requise")
    
    def generate_image(self, prompt: str, size: str = None, quality: str = None) -> ImageGenerationResult:
        """
        Génère une image avec DALL-E
        
        Args:
            prompt: Description de l'image à générer
            size: Taille de l'image (1024x1024, 1792x1024, 1024x1792)
            quality: Qualité de l'image (standard, hd)
        
        Returns:
            ImageGenerationResult avec le chemin de l'image ou l'erreur
        """
        try:
            # Optimiser le prompt pour Instagram
            optimized_prompt = self._optimize_prompt_for_instagram(prompt)
            
            # Configuration par défaut
            size = size or Config.DALLE_IMAGE_SIZE
            quality = quality or Config.DALLE_QUALITY
            
            print(f"🎨 Génération d'image avec DALL-E...")
            print(f"   📝 Prompt: {optimized_prompt}")
            print(f"   📐 Taille: {size}")
            
            # Appel à l'API DALL-E
            response = openai.images.generate(
                model=Config.DALLE_MODEL,
                prompt=optimized_prompt,
                size=size,
                quality=quality,
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Télécharger et sauvegarder l'image
            image_path = self._download_and_save_image(image_url)
            
            if image_path:
                print(f"✅ Image générée avec succès: {image_path}")
                return ImageGenerationResult.success_result(image_path, optimized_prompt)
            else:
                return ImageGenerationResult.error_result(
                    "Erreur lors de la sauvegarde de l'image", optimized_prompt
                )
                
        except openai.RateLimitError:
            error_msg = "Limite de taux API atteinte. Veuillez réessayer plus tard."
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
            
        except openai.APIError as e:
            error_msg = f"Erreur API OpenAI: {str(e)}"
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération d'image: {str(e)}"
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
    
    def _optimize_prompt_for_instagram(self, prompt: str) -> str:
        """Optimise le prompt pour générer des images adaptées à Instagram"""
        
        # Mots-clés pour améliorer la qualité visuelle
        quality_keywords = [
            "high quality", "professional photography", "Instagram-worthy",
            "vibrant colors", "good lighting", "sharp focus"
        ]
        
        # Éviter certains termes problématiques
        forbidden_terms = ["nsfw", "explicit", "violence", "harmful"]
        
        # Nettoyer le prompt
        clean_prompt = prompt.lower().strip()
        for term in forbidden_terms:
            if term in clean_prompt:
                clean_prompt = clean_prompt.replace(term, "")
        
        # Ajouter des améliorations pour Instagram
        enhanced_prompt = f"{prompt}, high quality, professional photography, vibrant colors, Instagram-style"
        
        # Limiter la longueur du prompt (max 1000 caractères pour DALL-E)
        if len(enhanced_prompt) > 1000:
            enhanced_prompt = enhanced_prompt[:997] + "..."
        
        return enhanced_prompt
    
    def _download_and_save_image(self, image_url: str) -> Optional[str]:
        """Télécharge et sauvegarde une image depuis une URL"""
        try:
            # Télécharger l'image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Générer un nom de fichier unique
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ai_generated_{timestamp}.png"
            filepath = os.path.join(Config.GENERATED_FOLDER, filename)
            
            # Sauvegarder l'image
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Optimiser l'image pour Instagram (optionnel)
            self._optimize_image_for_instagram(filepath)
            
            return filepath
            
        except requests.RequestException as e:
            print(f"❌ Erreur lors du téléchargement: {e}")
            return None
        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            return None
    
    def _optimize_image_for_instagram(self, image_path: str):
        """Optimise une image pour Instagram (format carré, qualité, taille)"""
        try:
            with Image.open(image_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Instagram préfère les images carrées (1080x1080) ou rectangulaires (1080x1350)
                original_size = img.size
                
                # Si l'image n'est pas au bon format, on peut la recadrer ou la redimensionner
                if original_size[0] != original_size[1]:  # Si pas carrée
                    # Créer une version carrée en prenant le minimum des deux dimensions
                    min_size = min(original_size)
                    left = (original_size[0] - min_size) // 2
                    top = (original_size[1] - min_size) // 2
                    right = left + min_size
                    bottom = top + min_size
                    
                    img = img.crop((left, top, right, bottom))
                
                # Redimensionner pour Instagram (1080x1080 optimal)
                if img.size[0] > 1080:
                    img = img.resize((1080, 1080), Image.Resampling.LANCZOS)
                
                # Sauvegarder avec une qualité optimisée
                img.save(image_path, 'PNG', optimize=True, quality=95)
                
        except Exception as e:
            print(f"⚠️  Erreur lors de l'optimisation de l'image: {e}")
            # Ne pas lever d'exception, l'image originale reste utilisable
    
    def generate_variations(self, base_prompt: str, num_variations: int = 3) -> List[ImageGenerationResult]:
        """Génère plusieurs variations d'une image"""
        variations = []
        
        # Créer des variations du prompt
        variation_prompts = self._create_prompt_variations(base_prompt, num_variations)
        
        for i, prompt in enumerate(variation_prompts):
            print(f"🎨 Génération de la variation {i+1}/{num_variations}")
            result = self.generate_image(prompt)
            variations.append(result)
            
            # Petite pause entre les appels API
            if i < len(variation_prompts) - 1:
                import time
                time.sleep(1)
        
        return variations
    
    def _create_prompt_variations(self, base_prompt: str, num_variations: int) -> List[str]:
        """Crée des variations d'un prompt de base"""
        style_variations = [
            "photorealistic style",
            "artistic style", 
            "minimalist style",
            "vintage style",
            "modern style",
            "cinematic style"
        ]
        
        mood_variations = [
            "bright and cheerful",
            "warm and cozy",
            "cool and serene", 
            "dramatic and bold",
            "soft and dreamy"
        ]
        
        variations = []
        for i in range(num_variations):
            # Ajouter différents styles et ambiances
            style = style_variations[i % len(style_variations)]
            mood = mood_variations[i % len(mood_variations)]
            
            variation = f"{base_prompt}, {style}, {mood}"
            variations.append(variation)
        
        return variations
    
    def validate_prompt(self, prompt: str) -> Tuple[bool, str]:
        """Valide un prompt avant génération"""
        if not prompt or len(prompt.strip()) < 3:
            return False, "Le prompt doit contenir au moins 3 caractères"
        
        if len(prompt) > 1000:
            return False, "Le prompt est trop long (max 1000 caractères)"
        
        # Vérifier les mots interdits
        forbidden_words = [
            "nsfw", "explicit", "nude", "sexual", "violence", "harmful",
            "hate", "discrimination", "illegal", "dangerous"
        ]
        
        prompt_lower = prompt.lower()
        for word in forbidden_words:
            if word in prompt_lower:
                return False, f"Le prompt contient un terme interdit: {word}"
        
        return True, "Prompt valide"
    
    def get_usage_stats(self) -> dict:
        """Retourne des statistiques d'utilisation (simulation)"""
        # Dans un vrai projet, vous pourriez tracker l'utilisation réelle
        return {
            "images_generated_today": 0,  # À implémenter avec un vrai tracking
            "remaining_credits": "Unlimited",  # Dépend de votre plan OpenAI
            "average_generation_time": "10-15 seconds"
        }