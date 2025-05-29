import openai
import re
from typing import List, Dict, Optional, Tuple

from config import Config
from models import ContentGenerationResult, GenerationRequest, ContentTone


class ContentGenerator:
    """Générateur de contenu pour Instagram utilisant GPT"""
    
    def __init__(self, api_key: str = None):
        """Initialise le générateur avec une clé API OpenAI"""
        self.api_key = api_key or Config.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key
        else:
            raise ValueError("Clé API OpenAI requise")
    
    def generate_description_and_hashtags(self, topic: str, tone: str = "engageant", 
                                        additional_context: str = None) -> ContentGenerationResult:
        """
        Génère une description et des hashtags pour un sujet donné
        
        Args:
            topic: Sujet du post
            tone: Ton du contenu (engageant, professionnel, etc.)
            additional_context: Contexte supplémentaire
        
        Returns:
            ContentGenerationResult avec description et hashtags
        """
        try:
            prompt = self._build_generation_prompt(topic, tone, additional_context)
            
            print(f"✍️  Génération de contenu pour: {topic}")
            print(f"   🎭 Ton: {tone}")
            
            response = openai.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=Config.GPT_MAX_TOKENS,
                temperature=Config.GPT_TEMPERATURE
            )
            
            content = response.choices[0].message.content
            description, hashtags = self._parse_generated_content(content)
            
            if description and hashtags:
                print(f"✅ Contenu généré avec succès")
                return ContentGenerationResult.success_result(description, hashtags)
            else:
                return ContentGenerationResult.error_result("Impossible de parser le contenu généré")
                
        except openai.RateLimitError:
            error_msg = "Limite de taux API atteinte. Veuillez réessayer plus tard."
            print(f"❌ {error_msg}")
            return ContentGenerationResult.error_result(error_msg)
            
        except openai.APIError as e:
            error_msg = f"Erreur API OpenAI: {str(e)}"
            print(f"❌ {error_msg}")
            return ContentGenerationResult.error_result(error_msg)
            
        except Exception as e:
            error_msg = f"Erreur lors de la génération de contenu: {str(e)}"
            print(f"❌ {error_msg}")
            return ContentGenerationResult.error_result(error_msg)
    
    def generate_from_request(self, request: GenerationRequest) -> ContentGenerationResult:
        """Génère du contenu à partir d'une requête structurée"""
        try:
            prompt = request.to_prompt()
            
            response = openai.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=Config.GPT_MAX_TOKENS,
                temperature=Config.GPT_TEMPERATURE
            )
            
            content = response.choices[0].message.content
            description, hashtags = self._parse_generated_content(content)
            
            if description and hashtags:
                return ContentGenerationResult.success_result(description, hashtags)
            else:
                return ContentGenerationResult.error_result("Impossible de parser le contenu généré")
                
        except Exception as e:
            return ContentGenerationResult.error_result(f"Erreur: {str(e)}")
    
    def _build_generation_prompt(self, topic: str, tone: str, additional_context: str = None) -> str:
        """Construit le prompt pour la génération de contenu"""
        
        # Instructions de base
        base_prompt = f"""
Créez une description Instagram {tone} et des hashtags pour le sujet suivant: {topic}

Instructions:
- La description doit être accrocheuse et inciter à l'engagement
- Utilisez un ton {tone} adapté au public Instagram français
- Incluez un appel à l'action subtil
- Limitez la description à 150-200 mots maximum
- Utilisez 10-15 hashtags pertinents et populaires
- Mélangez hashtags génériques et spécifiques
- Évitez les hashtags trop compétitifs ou spam
"""

        # Ajouter le contexte supplémentaire si fourni
        if additional_context:
            base_prompt += f"\nContexte supplémentaire: {additional_context}"
        
        # Instructions spécifiques selon le ton
        tone_instructions = self._get_tone_specific_instructions(tone)
        if tone_instructions:
            base_prompt += f"\n{tone_instructions}"
        
        # Format de sortie
        base_prompt += """

Format de réponse OBLIGATOIRE:
DESCRIPTION: [votre description ici]
HASHTAGS: [vos hashtags séparés par des espaces, commençant par #]

Exemple de format:
DESCRIPTION: Découvrez cette recette incroyable qui va révolutionner vos petits-déjeuners ! 🥞✨
HASHTAGS: #cuisine #recette #petitdejeuner #healthy #foodie #instafood #cooking #breakfast #homemade #delicious
"""
        
        return base_prompt
    
    def _get_tone_specific_instructions(self, tone: str) -> str:
        """Retourne des instructions spécifiques selon le ton choisi"""
        tone_map = {
            "engageant": "Utilisez des émojis, posez des questions, créez de l'interaction",
            "professionnel": "Restez formel mais accessible, mettez l'accent sur la valeur",
            "décontracté": "Soyez naturel, utilisez un langage familier mais respectueux",
            "inspirant": "Motivez et inspirez, utilisez des citations ou messages positifs",
            "humoristique": "Ajoutez une touche d'humour subtil et approprié",
            "éducatif": "Partagez des informations utiles, des conseils pratiques"
        }
        
        return tone_map.get(tone.lower(), "")
    
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
                # Parfois le format peut varier
                elif line.startswith("Description:"):
                    description = line.replace("Description:", "").strip()
                elif line.startswith("Hashtags:"):
                    hashtags = line.replace("Hashtags:", "").strip()
            
            # Nettoyer et valider
            description = self._clean_description(description)
            hashtags = self._clean_hashtags(hashtags)
            
            return description, hashtags
            
        except Exception as e:
            print(f"❌ Erreur lors du parsing: {e}")
            return "", ""
    
    def _clean_description(self, description: str) -> str:
        """Nettoie et valide la description"""
        if not description:
            return ""
        
        # Supprimer les guillemets en début/fin
        description = description.strip('"\'')
        
        # Limiter la longueur
        if len(description) > 2200:  # Limite Instagram
            description = description[:2197] + "..."
        
        return description
    
    def _clean_hashtags(self, hashtags: str) -> str:
        """Nettoie et valide les hashtags"""
        if not hashtags:
            return ""
        
        # Séparer les hashtags
        hashtag_list = re.findall(r'#\w+', hashtags)
        
        # Supprimer les doublons tout en préservant l'ordre
        seen = set()
        unique_hashtags = []
        for hashtag in hashtag_list:
            if hashtag.lower() not in seen:
                seen.add(hashtag.lower())
                unique_hashtags.append(hashtag)
        
        # Limiter à 30 hashtags max (recommandation Instagram)
        unique_hashtags = unique_hashtags[:30]
        
        return " ".join(unique_hashtags)
    
    def generate_multiple_versions(self, topic: str, tone: str, count: int = 3) -> List[ContentGenerationResult]:
        """Génère plusieurs versions du contenu pour le même sujet"""
        results = []
        
        for i in range(count):
            print(f"✍️  Génération version {i+1}/{count}")
            
            # Varier légèrement le prompt pour chaque version
            context_variations = [
                "Créez une version unique et originale",
                "Proposez une approche différente et créative", 
                "Offrez une perspective nouvelle et engageante"
            ]
            
            additional_context = context_variations[i % len(context_variations)]
            result = self.generate_description_and_hashtags(topic, tone, additional_context)
            results.append(result)
            
            # Petite pause entre les appels
            if i < count - 1:
                import time
                time.sleep(1)
        
        return results
    
    def optimize_hashtags(self, hashtags: str, topic: str) -> str:
        """Optimise les hashtags pour une meilleure portée"""
        try:
            prompt = f"""
Optimisez ces hashtags Instagram pour le sujet "{topic}":
{hashtags}

Instructions:
- Gardez les meilleurs hashtags existants
- Ajoutez des hashtags avec différents niveaux de popularité:
  * 2-3 hashtags très populaires (>1M posts)
  * 5-7 hashtags moyennement populaires (100K-1M posts)  
  * 5-7 hashtags de niche (<100K posts)
- Incluez des hashtags français et anglais pertinents
- Maximum 25 hashtags au total
- Évitez les hashtags bannis ou shadowbanés

Retournez uniquement les hashtags optimisés, séparés par des espaces:
"""
            
            response = openai.chat.completions.create(
                model=Config.GPT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.5
            )
            
            optimized = response.choices[0].message.content.strip()
            return self._clean_hashtags(optimized)
            
        except Exception as e:
            print(f"❌ Erreur optimisation hashtags: {e}")
            return hashtags  # Retourner les hashtags originaux en cas d'erreur
    
    def generate_caption_variations(self, base_description: str, count: int = 3) -> List[str]:
        """Génère des variations d'une description de base"""
        variations = []
        
        try:
            for i in range(count):
                prompt = f"""
Réécrivez cette description Instagram en conservant le message principal mais avec un style différent:

Description originale: {base_description}

Variation #{i+1}: Changez le style, la structure ou l'approche tout en gardant l'essence du message.
Gardez la même longueur approximative.
"""
                
                response = openai.chat.completions.create(
                    model=Config.GPT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.8
                )
                
                variation = response.choices[0].message.content.strip()
                variations.append(self._clean_description(variation))
                
        except Exception as e:
            print(f"❌ Erreur génération variations: {e}")
        
        return variations
    
    def analyze_content_performance(self, description: str, hashtags: str) -> Dict[str, any]:
        """Analyse la qualité potentielle du contenu (simulation)"""
        # Dans un vrai projet, vous pourriez utiliser des APIs d'analyse de sentiment
        # ou des données historiques de performance
        
        analysis = {
            "description_length": len(description),
            "hashtag_count": len(hashtags.split()) if hashtags else 0,
            "has_call_to_action": any(word in description.lower() for word in 
                                    ["comment", "tag", "share", "follow", "like", "swipe"]),
            "has_emojis": bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', description)),
            "engagement_potential": "high",  # Simulation
            "recommendations": []
        }
        
        # Recommandations basiques
        if analysis["description_length"] < 50:
            analysis["recommendations"].append("Description trop courte, ajoutez plus de contexte")
        elif analysis["description_length"] > 2000:
            analysis["recommendations"].append("Description trop longue, condensez le message")
        
        if analysis["hashtag_count"] < 5:
            analysis["recommendations"].append("Ajoutez plus de hashtags pour une meilleure portée")
        elif analysis["hashtag_count"] > 30:
            analysis["recommendations"].append("Réduisez le nombre de hashtags (max 30)")
        
        if not analysis["has_call_to_action"]:
            analysis["recommendations"].append("Ajoutez un appel à l'action pour l'engagement")
        
        return analysis