# services/ollama_generator.py - Générateur de contenu avec Ollama
import requests
import json
import re
from typing import Optional, Tuple, List
from datetime import datetime

# Import conditionnel des modèles
try:
    from models import ContentGenerationResult, GenerationRequest, ContentTone, ImageGenerationResult
except ImportError:
    # Modèles de secours si models.py a des problèmes
    class ContentGenerationResult:
        def __init__(self, success, description=None, hashtags=None, error_message=None):
            self.success = success
            self.description = description
            self.hashtags = hashtags
            self.error_message = error_message
        
        @classmethod
        def success_result(cls, description, hashtags):
            return cls(True, description, hashtags)
        
        @classmethod
        def error_result(cls, error_message):
            return cls(False, error_message=error_message)
    
    class ImageGenerationResult:
        def __init__(self, success, image_path=None, error_message=None):
            self.success = success
            self.image_path = image_path
            self.error_message = error_message
        
        @classmethod
        def success_result(cls, image_path, prompt_used):
            return cls(True, image_path)
        
        @classmethod
        def error_result(cls, error_message, prompt_used=None):
            return cls(False, error_message=error_message)


class OllamaContentGenerator:
    """Générateur de contenu utilisant Ollama avec Mistral en local"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral:latest"):
        """
        Initialise le générateur avec Ollama
        
        Args:
            base_url: URL de base d'Ollama (par défaut localhost:11434)
            model: Nom du modèle à utiliser (ex: mistral:latest, llama2, codellama)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_url = f"{self.base_url}/api/generate"
        
        # Vérifier que Ollama est accessible
        try:
            self._test_connection()
            print(f"✅ Connexion Ollama réussie - Modèle: {self.model}")
        except Exception as e:
            print(f"⚠️  Attention: Ollama non accessible - {e}")
    
    def _test_connection(self):
        """Teste la connexion à Ollama"""
        test_url = f"{self.base_url}/api/tags"
        response = requests.get(test_url, timeout=5)
        response.raise_for_status()
        
        # Vérifier que le modèle existe
        models = response.json().get('models', [])
        model_names = [model['name'] for model in models]
        
        if self.model not in model_names:
            print(f"⚠️  Modèle {self.model} non trouvé. Modèles disponibles: {model_names}")
            if model_names:
                self.model = model_names[0]
                print(f"🔄 Utilisation du modèle: {self.model}")
    
    def generate_description_and_hashtags(self, topic: str, tone: str = "engageant", 
                                        additional_context: str = None) -> ContentGenerationResult:
        """
        Génère une description et des hashtags pour un sujet donné
        
        Args:
            topic: Sujet du post
            tone: Ton du contenu
            additional_context: Contexte supplémentaire
        
        Returns:
            ContentGenerationResult avec description et hashtags
        """
        try:
            prompt = self._build_generation_prompt(topic, tone, additional_context)
            
            print(f"✍️  Génération de contenu avec Ollama/Mistral pour: {topic}")
            print(f"   🎭 Ton: {tone}")
            
            # Préparer la requête pour Ollama
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,  # Réponse complète d'un coup
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "top_p": 0.9
                }
            }
            
            # Appel à Ollama
            response = requests.post(
                self.api_url, 
                json=payload, 
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                return ContentGenerationResult.error_result(f"Erreur Ollama: {response.status_code}")
            
            result = response.json()
            content = result.get('response', '')
            
            if not content:
                return ContentGenerationResult.error_result("Réponse vide d'Ollama")
            
            # Parser le contenu généré
            description, hashtags = self._parse_generated_content(content)
            
            if description and hashtags:
                print(f"✅ Contenu généré avec succès par Ollama")
                return ContentGenerationResult.success_result(description, hashtags)
            else:
                return ContentGenerationResult.error_result("Impossible de parser le contenu généré")
                
        except requests.RequestException as e:
            error_msg = f"Erreur de connexion Ollama: {str(e)}"
            print(f"❌ {error_msg}")
            return ContentGenerationResult.error_result(error_msg)
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération de contenu: {str(e)}"
            print(f"❌ {error_msg}")
            return ContentGenerationResult.error_result(error_msg)
    
    def _build_generation_prompt(self, topic: str, tone: str, additional_context: str = None) -> str:
        """Construit le prompt optimisé pour Mistral"""
        
        # Prompt optimisé pour Mistral en français
        base_prompt = f"""Tu es un expert en marketing Instagram français. Crée une publication Instagram engageante.

SUJET: {topic}
TON: {tone}

INSTRUCTIONS:
- Écris une description Instagram accrocheuse en français ({tone})
- Ajoute 10-15 hashtags pertinents mélangant français et anglais
- Inclus un appel à l'action subtil
- Utilise des émojis appropriés
- Maximum 150 mots pour la description

{f"CONTEXTE SUPPLÉMENTAIRE: {additional_context}" if additional_context else ""}

INSTRUCTIONS DE TON:
"""

        # Instructions spécifiques selon le ton
        tone_instructions = {
            "engageant": "Sois interactif, utilise des émojis, pose des questions, crée de l'interaction",
            "professionnel": "Reste formel mais accessible, mets l'accent sur la valeur et l'expertise",
            "décontracté": "Sois naturel et familier, utilise un langage simple et accessible",
            "inspirant": "Motive et inspire, utilise des messages positifs et encourageants",
            "humoristique": "Ajoute une touche d'humour subtil et approprié",
            "éducatif": "Partage des informations utiles et des conseils pratiques"
        }
        
        if tone.lower() in tone_instructions:
            base_prompt += tone_instructions[tone.lower()]
        
        # Format de sortie strict
        base_prompt += """

FORMAT DE RÉPONSE OBLIGATOIRE (respecte exactement ce format):
DESCRIPTION: [ta description ici avec émojis]
HASHTAGS: [tes hashtags séparés par des espaces, commençant par #]

EXEMPLE:
DESCRIPTION: Découvrez cette recette incroyable qui va révolutionner vos petits-déjeuners ! 🥞✨ Qui d'autre adore commencer la journée avec de délicieuses créations ? Partagez vos photos en commentaires ! 👇
HASHTAGS: #cuisine #recette #petitdejeuner #healthy #foodie #instafood #cooking #breakfast #homemade #delicious #food #yummy #nutrition #lifestyle #france

Maintenant, génère le contenu:"""
        
        return base_prompt
    
    def _parse_generated_content(self, content: str) -> Tuple[str, str]:
        """Parse le contenu généré pour extraire description et hashtags"""
        try:
            lines = content.strip().split('\n')
            description = ""
            hashtags = ""
            
            for line in lines:
                line = line.strip()
                if line.startswith("DESCRIPTION:"):
                    description = line.replace("DESCRIPTION:", "").strip()
                elif line.startswith("HASHTAGS:"):
                    hashtags = line.replace("HASHTAGS:", "").strip()
                # Variations possibles
                elif line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                elif line.startswith("Hashtags:"):
                    hashtags = line.replace("Hashtags:", "").strip()
            
            # Si pas trouvé avec le format, essayer de parser différemment
            if not description or not hashtags:
                # Chercher des patterns alternatifs
                text_parts = content.split('#')
                if len(text_parts) >= 2:
                    description = text_parts[0].strip()
                    hashtags = '#' + ' #'.join([part.split()[0] for part in text_parts[1:] if part.strip()])
            
            # Nettoyer et valider
            description = self._clean_description(description)
            hashtags = self._clean_hashtags(hashtags)
            
            return description, hashtags
            
        except Exception as e:
            print(f"❌ Erreur lors du parsing: {e}")
            print(f"Contenu brut: {content}")
            return "", ""
    
    def _clean_description(self, description: str) -> str:
        """Nettoie et valide la description"""
        if not description:
            return ""
        
        # Supprimer les guillemets et nettoyer
        description = description.strip('"\'').strip()
        
        # Limiter la longueur pour Instagram
        if len(description) > 2200:
            description = description[:2197] + "..."
        
        return description
    
    def _clean_hashtags(self, hashtags: str) -> str:
        """Nettoie et valide les hashtags"""
        if not hashtags:
            return ""
        
        # Extraire tous les hashtags
        hashtag_list = re.findall(r'#\w+', hashtags)
        
        # Supprimer les doublons en préservant l'ordre
        seen = set()
        unique_hashtags = []
        for hashtag in hashtag_list:
            if hashtag.lower() not in seen:
                seen.add(hashtag.lower())
                unique_hashtags.append(hashtag)
        
        # Limiter à 30 hashtags max
        unique_hashtags = unique_hashtags[:30]
        
        return " ".join(unique_hashtags)
    
    def generate_multiple_versions(self, topic: str, tone: str, count: int = 3) -> List[ContentGenerationResult]:
        """Génère plusieurs versions du contenu pour le même sujet"""
        results = []
        
        for i in range(count):
            print(f"✍️  Génération version {i+1}/{count} avec Ollama")
            
            # Varier le prompt pour chaque version
            context_variations = [
                "Crée une version unique et originale",
                "Propose une approche différente et créative", 
                "Offre une perspective nouvelle et engageante"
            ]
            
            additional_context = context_variations[i % len(context_variations)]
            result = self.generate_description_and_hashtags(topic, tone, additional_context)
            results.append(result)
        
        return results
    
    def get_available_models(self) -> List[str]:
        """Retourne la liste des modèles disponibles dans Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def switch_model(self, model_name: str) -> bool:
        """Change le modèle utilisé"""
        available_models = self.get_available_models()
        if model_name in available_models:
            self.model = model_name
            print(f"🔄 Modèle changé pour: {model_name}")
            return True
        else:
            print(f"❌ Modèle {model_name} non disponible. Modèles disponibles: {available_models}")
            return False


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
    
    def generate_description_and_hashtags(self, topic: str, tone: str = "engageant", 
                                        additional_context: str = None) -> ContentGenerationResult:
        """Alias pour la compatibilité"""
        return self.generate_content(topic, tone, additional_context)
    
    def generate_image(self, prompt: str, size: str = "1024x1024"):
        """Génère une image avec DALL-E si disponible"""
        if self.image_generator:
            return self.image_generator.generate_image(prompt, size)
        else:
            print("⚠️  Génération d'images non disponible (pas de clé OpenAI)")
            return ImageGenerationResult.error_result("Service d'images non disponible")
    
    def get_status(self) -> dict:
        """Retourne le statut des services"""
        return {
            'content_generator': self.content_generator is not None,
            'image_generator': self.image_generator is not None,
            'ollama_model': self.content_generator.model if self.content_generator else None,
            'available_models': self.content_generator.get_available_models() if self.content_generator else []
        }


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