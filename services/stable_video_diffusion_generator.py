# services/stable_video_diffusion_generator.py
import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from PIL import Image
import base64
import io

from models import VideoGenerationResult


class StableVideoDiffusionGenerator:
    """Générateur de vidéos avec Stable Video Diffusion (local)"""
    
    def __init__(self, api_url: str = "http://localhost:7862"):
        """
        Initialise le générateur SVD
        
        Args:
            api_url: URL de l'API ComfyUI avec SVD
        """
        self.api_url = api_url.rstrip('/')
        self.queue_url = f"{self.api_url}/prompt"
        self.history_url = f"{self.api_url}/history"
        self.status_url = f"{self.api_url}/queue"
        
        print(f"🎬 Générateur Stable Video Diffusion initialisé")
        print(f"   🌐 URL: {self.api_url}")
        
        # Test de connexion
        self.is_available = self._test_connection()
        if self.is_available:
            print("✅ SVD accessible")
        else:
            print("⚠️  SVD non accessible")
            print("💡 Pour démarrer SVD avec ComfyUI :")
            print("   1. Installez ComfyUI : git clone https://github.com/comfyanonymous/ComfyUI")
            print("   2. Téléchargez SVD : huggingface-cli download stabilityai/stable-video-diffusion-img2vid")
            print("   3. Démarrez : python main.py --port 7862")
    
    def _test_connection(self) -> bool:
        """Teste la connexion à ComfyUI/SVD"""
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_video_from_image(self, image_path: str, 
                                 duration_seconds: int = 3,
                                 fps: int = 8,
                                 motion_strength: float = 0.7,
                                 seed: int = -1) -> 'VideoGenerationResult':
        """
        Génère une vidéo à partir d'une image
        
        Args:
            image_path: Chemin vers l'image source
            duration_seconds: Durée de la vidéo en secondes
            fps: Images par seconde
            motion_strength: Force du mouvement (0.0-1.0)
            seed: Graine pour la reproductibilité (-1 = aléatoire)
        
        Returns:
            VideoGenerationResult
        """
        if not self.is_available:
            return VideoGenerationResult.error_result(
                "Stable Video Diffusion non disponible", image_path
            )
        
        try:
            print(f"🎬 Génération vidéo SVD...")
            print(f"   🖼️  Image source: {os.path.basename(image_path)}")
            print(f"   ⏱️  Durée: {duration_seconds}s à {fps} FPS")
            print(f"   🎯 Motion: {motion_strength}")
            
            # Calculer le nombre de frames
            num_frames = duration_seconds * fps
            
            # Préparer l'image
            image_base64 = self._encode_image_to_base64(image_path)
            if not image_base64:
                return VideoGenerationResult.error_result(
                    "Impossible d'encoder l'image", image_path
                )
            
            # Workflow ComfyUI pour SVD
            workflow = self._create_svd_workflow(
                image_base64, num_frames, motion_strength, seed
            )
            
            # Soumettre le job
            start_time = time.time()
            prompt_id = self._submit_workflow(workflow)
            
            if not prompt_id:
                return VideoGenerationResult.error_result(
                    "Impossible de soumettre le workflow", image_path
                )
            
            # Attendre la completion
            result_data = self._wait_for_completion(prompt_id)
            
            if not result_data:
                return VideoGenerationResult.error_result(
                    "Timeout ou erreur de génération", image_path
                )
            
            # Sauvegarder la vidéo
            video_path = self._save_video_result(result_data, image_path)
            
            generation_time = time.time() - start_time
            
            if video_path:
                print(f"✅ Vidéo générée en {generation_time:.1f}s: {video_path}")
                return VideoGenerationResult.success_result(
                    video_path, f"Video from {os.path.basename(image_path)}"
                )
            else:
                return VideoGenerationResult.error_result(
                    "Erreur lors de la sauvegarde", image_path
                )
                
        except Exception as e:
            error_msg = f"Erreur génération vidéo: {str(e)}"
            print(f"❌ {error_msg}")
            return VideoGenerationResult.error_result(error_msg, image_path)
    
    def _encode_image_to_base64(self, image_path: str) -> Optional[str]:
        """Encode une image en base64"""
        try:
            with Image.open(image_path) as img:
                # Redimensionner pour SVD (1024x576 optimal)
                img = img.resize((1024, 576), Image.Resampling.LANCZOS)
                
                # Convertir en RGB si nécessaire
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Encoder en base64
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                return img_base64
        except Exception as e:
            print(f"❌ Erreur encodage image: {e}")
            return None
    
    def _create_svd_workflow(self, image_base64: str, num_frames: int, 
                           motion_strength: float, seed: int) -> Dict[str, Any]:
        """Crée le workflow ComfyUI pour SVD"""
        
        # Workflow JSON pour SVD (simplifié)
        workflow = {
            "1": {
                "inputs": {
                    "image": image_base64,
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {"title": "Load Image"}
            },
            "2": {
                "inputs": {
                    "ckpt_name": "svd.safetensors"  # ou svd_xt.safetensors
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load SVD Model"}
            },
            "3": {
                "inputs": {
                    "seed": seed if seed != -1 else int(time.time()),
                    "steps": 20,
                    "cfg": 2.5,
                    "sampler_name": "euler",
                    "scheduler": "karras",
                    "denoise": motion_strength,
                    "model": ["2", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "SVD Sampler"}
            },
            "4": {
                "inputs": {
                    "text": f"high quality video, smooth motion, {num_frames} frames",
                    "clip": ["2", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "Positive Prompt"}
            },
            "5": {
                "inputs": {
                    "text": "blurry, low quality, distorted",
                    "clip": ["2", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "Negative Prompt"}
            },
            "6": {
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["2", 2]
                },
                "class_type": "VAEEncode",
                "_meta": {"title": "VAE Encode"}
            },
            "7": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["2", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "8": {
                "inputs": {
                    "images": ["7", 0],
                    "fps": 8,
                    "loop_count": 0,
                    "filename_prefix": "svd_output",
                    "format": "video/mp4"
                },
                "class_type": "SaveAnimatedWEBP",  # ou SaveVideo si disponible
                "_meta": {"title": "Save Video"}
            }
        }
        
        return workflow
    
    def _submit_workflow(self, workflow: Dict[str, Any]) -> Optional[str]:
        """Soumet un workflow à ComfyUI"""
        try:
            payload = {
                "prompt": workflow,
                "client_id": "svd_generator"
            }
            
            response = requests.post(
                self.queue_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("prompt_id")
            else:
                print(f"❌ Erreur soumission workflow: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur soumission: {e}")
            return None
    
    def _wait_for_completion(self, prompt_id: str, max_wait: int = 300) -> Optional[Dict]:
        """Attend la completion d'un job"""
        print(f"⏳ Attente génération vidéo (max {max_wait}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Vérifier le statut
                response = requests.get(f"{self.history_url}/{prompt_id}", timeout=10)
                
                if response.status_code == 200:
                    history = response.json()
                    
                    if prompt_id in history:
                        job_data = history[prompt_id]
                        
                        if 'outputs' in job_data:
                            print(f"✅ Génération terminée")
                            return job_data['outputs']
                
                # Vérifier si le job est encore en queue
                queue_response = requests.get(self.status_url, timeout=10)
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    
                    # Chercher notre job dans la queue
                    running = queue_data.get('queue_running', [])
                    pending = queue_data.get('queue_pending', [])
                    
                    if not any(job[1] == prompt_id for job in running + pending):
                        print(f"❌ Job non trouvé dans la queue")
                        break
                
                time.sleep(5)  # Attendre 5 secondes
                
            except Exception as e:
                print(f"❌ Erreur vérification statut: {e}")
                time.sleep(5)
        
        print(f"⏰ Timeout après {max_wait}s")
        return None
    
    def _save_video_result(self, outputs: Dict, source_image: str) -> Optional[str]:
        """Sauvegarde le résultat vidéo"""
        try:
            # Générer nom de fichier
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(os.path.basename(source_image))[0]
            filename = f"svd_{timestamp}_{base_name}.mp4"
            filepath = os.path.join("generated", "videos", filename)
            
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Extraire la vidéo des outputs ComfyUI
            # La structure exacte dépend du workflow utilisé
            for node_id, node_output in outputs.items():
                if 'videos' in node_output:
                    video_data = node_output['videos'][0]
                    
                    # Télécharger la vidéo depuis ComfyUI
                    video_url = f"{self.api_url}/view?filename={video_data['filename']}"
                    
                    video_response = requests.get(video_url, timeout=60)
                    if video_response.status_code == 200:
                        with open(filepath, 'wb') as f:
                            f.write(video_response.content)
                        
                        print(f"💾 Vidéo sauvegardée: {filepath}")
                        return filepath
            
            print(f"❌ Aucune vidéo trouvée dans les outputs")
            return None
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde vidéo: {e}")
            return None
    
    def generate_video_from_text(self, prompt: str, 
                                duration_seconds: int = 3,
                                width: int = 1024, height: int = 576) -> 'VideoGenerationResult':
        """
        Génère une vidéo directement depuis un prompt texte
        (nécessite d'abord de générer une image, puis la vidéo)
        """
        try:
            print(f"🎬 Génération vidéo depuis texte: {prompt[:50]}...")
            
            # Étape 1: Générer une image avec Stable Diffusion
            # (Utiliser votre générateur d'images existant)
            from services.stable_diffusion_generator import StableDiffusionGenerator
            
            sd_generator = StableDiffusionGenerator()
            if not sd_generator.is_available:
                return VideoGenerationResult.error_result(
                    "Stable Diffusion requis pour générer l'image source", prompt
                )
            
            # Générer l'image source
            optimized_prompt = f"{prompt}, cinematic, high quality, suitable for video animation"
            image_result = sd_generator.generate_image(
                optimized_prompt, width=width, height=height
            )
            
            if not image_result.success:
                return VideoGenerationResult.error_result(
                    f"Impossible de générer l'image source: {image_result.error_message}", 
                    prompt
                )
            
            # Étape 2: Générer la vidéo depuis l'image
            video_result = self.generate_video_from_image(
                image_result.image_path, duration_seconds
            )
            
            return video_result
            
        except Exception as e:
            error_msg = f"Erreur génération vidéo depuis texte: {str(e)}"
            print(f"❌ {error_msg}")
            return VideoGenerationResult.error_result(error_msg, prompt)
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du générateur"""
        return {
            "available": self.is_available,
            "api_url": self.api_url,
            "service": "Stable Video Diffusion",
            "supported_formats": ["mp4", "webm", "gif"],
            "max_duration": 10,  # secondes
            "recommended_fps": [8, 12, 24]
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Récupère le statut de la queue ComfyUI"""
        try:
            response = requests.get(self.status_url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {"queue_running": [], "queue_pending": []}
        except:
            return {"queue_running": [], "queue_pending": []}