# services/stable_diffusion_generator.py
import os
import requests
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from PIL import Image
import io
import base64
import time

from models import ImageGenerationResult


class StableDiffusionGenerator:
    """Générateur d'images avec Stable Diffusion (gratuit et local)"""
    
    def __init__(self, api_url: str = "http://localhost:7860"):
        """
        Initialise le générateur Stable Diffusion
        
        Args:
            api_url: URL de l'API Stable Diffusion (AUTOMATIC1111 WebUI)
        """
        self.api_url = api_url.rstrip('/')
        self.txt2img_url = f"{self.api_url}/sdapi/v1/txt2img"
        self.models_url = f"{self.api_url}/sdapi/v1/sd-models"
        self.options_url = f"{self.api_url}/sdapi/v1/options"
        self.progress_url = f"{self.api_url}/sdapi/v1/progress"
        
        print(f"🎨 Générateur Stable Diffusion initialisé")
        print(f"   🌐 URL: {self.api_url}")
        
        # Test de connexion
        self.is_available = self._test_connection()
        if self.is_available:
            print("✅ Stable Diffusion accessible")
            self._print_status()
        else:
            print("⚠️  Stable Diffusion non accessible")
            print("💡 Pour démarrer Stable Diffusion :")
            print("   1. Téléchargez: https://github.com/AUTOMATIC1111/stable-diffusion-webui")
            print("   2. Démarrez avec: ./webui.sh --api")
            print("   3. Ou: python launch.py --api")
    
    def _test_connection(self) -> bool:
        """Teste la connexion à Stable Diffusion"""
        try:
            response = requests.get(self.options_url, timeout=60)
            return response.status_code == 200
        except Exception as e:
            return False
    
    def _print_status(self):
        """Affiche le statut de Stable Diffusion"""
        try:
            models = self.get_available_models()
            if models:
                print(f"   🧠 Modèles disponibles: {len(models)}")
                print(f"   📋 Modèle actuel: {models[0] if models else 'Aucun'}")
            else:
                print("   ⚠️  Aucun modèle trouvé")
        except:
            pass
    
    def generate_image(self, prompt: str, negative_prompt: str = None, 
                      width: int = 720, height: int = 720, 
                      steps: int = 20, cfg_scale: float = 7.0) -> ImageGenerationResult:
        """
        Génère une image avec Stable Diffusion
        
        Args:
            prompt: Description de l'image
            negative_prompt: Ce qu'on ne veut PAS dans l'image
            width: Largeur de l'image
            height: Hauteur de l'image
            steps: Nombre d'étapes de génération (plus = meilleur mais plus lent)
            cfg_scale: Respect du prompt (1-20, 7 recommandé)
        
        Returns:
            ImageGenerationResult
        """
        if not self.is_available:
            return ImageGenerationResult.error_result(
                "Stable Diffusion non disponible. Vérifiez que l'interface web est démarrée avec --api",
                prompt
            )
        
        try:
            # Optimiser le prompt pour Instagram
            optimized_prompt = self._optimize_prompt_for_instagram(prompt)
            
            # Prompt négatif par défaut pour de meilleures images
            if not negative_prompt:
                negative_prompt = self._get_default_negative_prompt()
            
            print(f"🎨 Génération d'image avec Stable Diffusion...")
            print(f"   📝 Prompt: {optimized_prompt[:100]}...")
            print(f"   📐 Taille: {width}x{height}")
            print(f"   ⚙️  Étapes: {steps}, CFG: {cfg_scale}")
            
            # Paramètres pour Stable Diffusion
            payload = {
                "prompt": optimized_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "sampler_name": "DPM++ 2M Karras",  # Excellent sampler
                "seed": -1,  # -1 = aléatoire
                "restore_faces": True,  # Améliorer les visages
                "tiling": False,
                "n_iter": 1,  # Nombre d'images
                "batch_size": 1,
                "enable_hr": True,  # Haute résolution
                "hr_scale": 1.5,    # Facteur d'agrandissement
                "hr_upscaler": "Latent",
                "denoising_strength": 0.7
            }
            
            # Démarrer la génération
            start_time = time.time()
            response = requests.post(
                self.txt2img_url,
                json=payload,
                timeout=300  # 5 minutes max
            )
            
            if response.status_code != 200:
                error_msg = f"Erreur Stable Diffusion: {response.status_code}"
                try:
                    error_detail = response.json().get('error', 'Erreur inconnue')
                    error_msg += f" - {error_detail}"
                except:
                    pass
                return ImageGenerationResult.error_result(error_msg, optimized_prompt)
            
            result = response.json()
            
            if not result.get('images'):
                return ImageGenerationResult.error_result(
                    "Aucune image générée", optimized_prompt
                )
            
            # Décoder l'image (base64 → PIL Image)
            image_b64 = result['images'][0]
            image_data = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_data))
            
            # Sauvegarder l'image
            image_path = self._save_image(image, prompt)
            
            generation_time = time.time() - start_time
            
            if image_path:
                print(f"✅ Image générée avec succès en {generation_time:.1f}s: {image_path}")
                return ImageGenerationResult.success_result(image_path, optimized_prompt)
            else:
                return ImageGenerationResult.error_result(
                    "Erreur lors de la sauvegarde", optimized_prompt
                )
                
        except requests.RequestException as e:
            error_msg = f"Erreur connexion Stable Diffusion: {str(e)}"
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
            
        except Exception as e:
            error_msg = f"Erreur génération image: {str(e)}"
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
    
    def _optimize_prompt_for_instagram(self, prompt: str) -> str:
        """Optimise le prompt pour des images Instagram de qualité"""
        
        # Mots-clés pour améliorer la qualité
        quality_keywords = [
            "high quality", "detailed", "sharp focus", "professional photography",
            "instagram worthy", "vibrant colors", "good lighting", "masterpiece",
            "best quality", "ultra detailed", "8k uhd", "photorealistic"
        ]
        
        # Style Instagram
        instagram_style = "professional photo, instagram style, high resolution, trending on instagram"
        
        # Construire le prompt optimisé
        optimized = f"{prompt}, {instagram_style}, {', '.join(quality_keywords[:4])}"
        
        # Limiter la longueur
        if len(optimized) > 400:
            optimized = optimized[:397] + "..."
        
        return optimized
    
    def _get_default_negative_prompt(self) -> str:
        """Retourne un prompt négatif par défaut pour de meilleures images"""
        return (
            "blurry, low quality, bad anatomy, bad hands, text, error, missing fingers, "
            "extra digit, fewer digits, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, username, blurry, bad art, bad proportions, "
            "gross proportions, ugly, duplicate, morbid, mutilated, out of frame, extra fingers, "
            "mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, "
            "bad anatomy, bad proportions, malformed limbs, extra limbs, cloned face, "
            "disfigured, missing arms, missing legs, extra arms, extra legs, fused fingers, "
            "too many fingers, long neck"
        )
    
    def _save_image(self, image: Image.Image, original_prompt: str) -> Optional[str]:
        """Sauvegarde l'image générée"""
        try:
            # Créer le nom de fichier
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Nettoyer le prompt pour le nom de fichier
            clean_prompt = "".join(c for c in original_prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_prompt = clean_prompt.replace(' ', '_')
            filename = f"sd_{timestamp}_{clean_prompt}.png"
            filepath = os.path.join("generated", filename)
            
            # Créer le dossier si nécessaire
            os.makedirs("generated", exist_ok=True)
            
            # Optimiser pour Instagram (format carré)
            image = self._optimize_for_instagram(image)
            
            # Sauvegarder avec métadonnées
            metadata = {
                "prompt": original_prompt,
                "generator": "Stable Diffusion",
                "timestamp": datetime.now().isoformat()
            }
            
            # Ajouter les métadonnées à l'image
            from PIL.PngImagePlugin import PngInfo
            png_info = PngInfo()
            for key, value in metadata.items():
                png_info.add_text(key, str(value))
            
            # Sauvegarder
            image.save(filepath, "PNG", pnginfo=png_info, quality=95, optimize=True)
            
            return filepath
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde image: {e}")
            return None
    
    def _optimize_for_instagram(self, image: Image.Image) -> Image.Image:
        """Optimise l'image pour Instagram"""
        # Convertir en RGB si nécessaire
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Format carré pour Instagram (1080x1080)
        width, height = image.size
        
        # Si l'image n'est pas carrée, la recadrer au centre
        if width != height:
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            right = left + size
            bottom = top + size
            image = image.crop((left, top, right, bottom))
        
        # Redimensionner à 1080x1080 (optimal Instagram)
        if image.size != (1080, 1080):
            image = image.resize((1080, 1080), Image.Resampling.LANCZOS)
        
        return image
    
    def get_available_models(self) -> List[str]:
        """Récupère la liste des modèles disponibles"""
        if not self.is_available:
            return []
        
        try:
            response = requests.get(self.models_url, timeout=10)
            if response.status_code == 200:
                models = response.json()
                return [model['title'] for model in models]
            return []
        except Exception as e:
            print(f"❌ Erreur récupération modèles: {e}")
            return []
    
    def get_current_model(self) -> str:
        """Récupère le modèle actuellement utilisé"""
        if not self.is_available:
            return "Non disponible"
        
        try:
            response = requests.get(self.options_url, timeout=10)
            if response.status_code == 200:
                options = response.json()
                return options.get('sd_model_checkpoint', 'Inconnu')
            return "Erreur"
        except:
            return "Erreur"
    
    def change_model(self, model_name: str) -> bool:
        """Change le modèle Stable Diffusion utilisé"""
        if not self.is_available:
            return False
        
        try:
            payload = {"sd_model_checkpoint": model_name}
            response = requests.post(
                self.options_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                print(f"✅ Modèle changé pour: {model_name}")
                return True
            else:
                print(f"❌ Erreur changement de modèle: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Erreur changement de modèle: {e}")
            return False
    
    def get_generation_progress(self) -> Dict[str, Any]:
        """Récupère le progrès de génération actuel"""
        if not self.is_available:
            return {"progress": 0, "eta": 0, "current_image": None}
        
        try:
            response = requests.get(self.progress_url, timeout=60)
            if response.status_code == 200:
                return response.json()
            return {"progress": 0, "eta": 0, "current_image": None}
        except:
            return {"progress": 0, "eta": 0, "current_image": None}
    
    def generate_variations(self, prompt: str, count: int = 3, 
                          variation_strength: float = 0.3) -> List[ImageGenerationResult]:
        """Génère plusieurs variations d'une image"""
        variations = []
        
        # Modificateurs pour créer des variations
        variation_modifiers = [
            "different angle",
            "different lighting", 
            "different composition",
            "different style",
            "different mood",
            "different colors"
        ]
        
        for i in range(count):
            print(f"🎨 Génération variation {i+1}/{count}")
            
            # Ajouter un modificateur différent à chaque variation
            modifier = variation_modifiers[i % len(variation_modifiers)]
            varied_prompt = f"{prompt}, {modifier}, variation {i+1}"
            
            result = self.generate_image(varied_prompt)
            variations.append(result)
            
            # Petite pause entre les générations
            if i < count - 1:
                time.sleep(1)
        
        return variations
    
    def upscale_image(self, image_path: str, scale_factor: int = 2) -> Optional[str]:
        """Agrandit une image (si l'upscaler est disponible dans SD)"""
        # Cette fonction nécessiterait l'API d'upscaling de Stable Diffusion
        # Pour l'instant, on peut utiliser PIL pour un upscaling basique
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                new_size = (width * scale_factor, height * scale_factor)
                upscaled = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Nouveau nom de fichier
                base_name = os.path.splitext(image_path)[0]
                upscaled_path = f"{base_name}_upscaled_{scale_factor}x.png"
                
                upscaled.save(upscaled_path, "PNG", quality=95)
                print(f"✅ Image agrandie: {upscaled_path}")
                return upscaled_path
        except Exception as e:
            print(f"❌ Erreur upscaling: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut complet du générateur"""
        return {
            "available": self.is_available,
            "api_url": self.api_url,
            "current_model": self.get_current_model() if self.is_available else None,
            "available_models": self.get_available_models() if self.is_available else [],
            "model_count": len(self.get_available_models()) if self.is_available else 0
        }
    
    def test_generation(self) -> ImageGenerationResult:
        """Test rapide de génération d'image"""
        test_prompt = "a beautiful sunset over mountains, professional photography, high quality"
        print("🧪 Test de génération d'image...")
        return self.generate_image(test_prompt, steps=10)  # Génération rapide pour le test


class HuggingFaceGenerator:
    """Alternative avec Hugging Face (gratuit, en ligne)"""
    
    def __init__(self, api_token: str = None):
        """
        Générateur d'images avec Hugging Face
        
        Args:
            api_token: Token Hugging Face (gratuit sur huggingface.co)
        """
        self.api_token = api_token
        self.api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
        
        self.headers = {"Content-Type": "application/json"}
        if api_token:
            self.headers["Authorization"] = f"Bearer {api_token}"
        
        print("🤗 Générateur Hugging Face initialisé")
        if not api_token:
            print("⚠️  Pas de token API - limites de taux plus strictes")
            print("💡 Obtenez un token gratuit sur: https://huggingface.co/settings/tokens")
    
    def generate_image(self, prompt: str) -> ImageGenerationResult:
        """Génère une image avec Hugging Face"""
        try:
            print(f"🎨 Génération avec Hugging Face: {prompt[:50]}...")
            
            optimized_prompt = f"{prompt}, high quality, detailed, professional"
            
            payload = {
                "inputs": optimized_prompt,
                "parameters": {
                    "negative_prompt": "blurry, low quality, bad anatomy",
                    "num_inference_steps": 20,
                    "guidance_scale": 7.5,
                    "width": 720,
                    "height": 720
                }
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                # Sauvegarder l'image
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                clean_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).rstrip()
                clean_prompt = clean_prompt.replace(' ', '_')
                filename = f"hf_{timestamp}_{clean_prompt}.png"
                filepath = os.path.join("generated", filename)
                
                os.makedirs("generated", exist_ok=True)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Image Hugging Face générée: {filepath}")
                return ImageGenerationResult.success_result(filepath, optimized_prompt)
            
            elif response.status_code == 503:
                return ImageGenerationResult.error_result(
                    "Modèle en cours de chargement, réessayez dans quelques minutes", prompt
                )
            else:
                error_msg = f"Erreur Hugging Face: {response.status_code}"
                try:
                    error_detail = response.json().get('error', '')
                    if error_detail:
                        error_msg += f" - {error_detail}"
                except:
                    pass
                return ImageGenerationResult.error_result(error_msg, prompt)
                
        except Exception as e:
            error_msg = f"Erreur Hugging Face: {str(e)}"
            print(f"❌ {error_msg}")
            return ImageGenerationResult.error_result(error_msg, prompt)
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du générateur Hugging Face"""
        return {
            "available": True,
            "service": "Hugging Face",
            "model": "stable-diffusion-2-1",
            "has_token": bool(self.api_token)
        }