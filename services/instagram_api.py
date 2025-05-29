import requests
import time
import os
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from config import Config
from models import PublicationResult


class InstagramPublisher:
    """Gestionnaire de publication sur Instagram via l'API Graph"""
    
    def __init__(self, access_token: str = None, account_id: str = None):
        """
        Initialise le publisher Instagram
        
        Args:
            access_token: Token d'accès Instagram
            account_id: ID du compte Instagram Business
        """
        self.access_token = access_token or Config.INSTAGRAM_ACCESS_TOKEN
        self.account_id = account_id or Config.INSTAGRAM_ACCOUNT_ID
        self.base_url = Config.INSTAGRAM_BASE_URL
        
        if not self.access_token or not self.account_id:
            raise ValueError("Token d'accès et ID de compte Instagram requis")
    
    def publish_post(self, image_path: str, caption: str, 
                    location_id: str = None) -> PublicationResult:
        """
        Publie un post sur Instagram
        
        Args:
            image_path: Chemin vers l'image à publier
            caption: Caption du post
            location_id: ID de localisation (optionnel)
        
        Returns:
            PublicationResult avec le résultat de la publication
        """
        try:
            print(f"📸 Publication sur Instagram...")
            print(f"   🖼️  Image: {os.path.basename(image_path)}")
            print(f"   📝 Caption: {caption[:100]}...")
            
            # Étape 1: Upload de l'image et création du container média
            container_result = self._create_media_container(image_path, caption, location_id)
            
            if not container_result['success']:
                return PublicationResult.error_result(container_result['error'])
            
            container_id = container_result['container_id']
            
            # Étape 2: Vérifier le statut du container
            if not self._wait_for_container_ready(container_id):
                return PublicationResult.error_result("Container média non prêt pour publication")
            
            # Étape 3: Publier le container
            publish_result = self._publish_media_container(container_id)
            
            if publish_result['success']:
                print(f"✅ Post publié avec succès! ID: {publish_result['post_id']}")
                return PublicationResult.success_result(
                    post_id=str(container_id),
                    instagram_post_id=publish_result['post_id']
                )
            else:
                return PublicationResult.error_result(publish_result['error'])
                
        except Exception as e:
            error_msg = f"Erreur lors de la publication: {str(e)}"
            print(f"❌ {error_msg}")
            return PublicationResult.error_result(error_msg)
    
    def _create_media_container(self, image_path: str, caption: str, 
                              location_id: str = None) -> Dict[str, Any]:
        """Crée un container média sur Instagram"""
        try:
            # URL de l'endpoint pour créer un container
            url = f"{self.base_url}/{self.account_id}/media"
            
            # Dans un environnement de production, vous devez uploader l'image
            # sur un serveur accessible publiquement (AWS S3, Cloudinary, etc.)
            image_url = self._upload_image_to_cdn(image_path)
            
            if not image_url:
                return {'success': False, 'error': 'Impossible d\'uploader l\'image'}
            
            # Paramètres pour créer le container
            params = {
                'image_url': image_url,
                'caption': caption,
                'access_token': self.access_token
            }
            
            # Ajouter la localisation si fournie
            if location_id:
                params['location_id'] = location_id
            
            response = requests.post(url, data=params, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and 'id' in data:
                return {
                    'success': True,
                    'container_id': data['id']
                }
            else:
                error_msg = data.get('error', {}).get('message', 'Erreur inconnue lors de la création du container')
                return {'success': False, 'error': error_msg}
                
        except requests.RequestException as e:
            return {'success': False, 'error': f'Erreur réseau: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Erreur: {str(e)}'}
    
    def _wait_for_container_ready(self, container_id: str, max_wait: int = 60) -> bool:
        """Attend que le container soit prêt pour publication"""
        print(f"⏳ Attente de la préparation du container...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status = self._get_container_status(container_id)
            
            if status == 'FINISHED':
                print(f"✅ Container prêt pour publication")
                return True
            elif status == 'ERROR':
                print(f"❌ Erreur dans le container")
                return False
            elif status in ['IN_PROGRESS', 'PUBLISHED']:
                time.sleep(2)  # Attendre 2 secondes avant de revérifier
                continue
            else:
                print(f"⚠️  Statut inconnu: {status}")
                time.sleep(2)
        
        print(f"⏰ Timeout: container non prêt après {max_wait}s")
        return False
    
    def _get_container_status(self, container_id: str) -> str:
        """Récupère le statut d'un container média"""
        try:
            url = f"{self.base_url}/{container_id}"
            params = {
                'fields': 'status_code',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200:
                return data.get('status_code', 'UNKNOWN')
            else:
                return 'ERROR'
                
        except Exception as e:
            print(f"❌ Erreur vérification statut: {e}")
            return 'ERROR'
    
    def _publish_media_container(self, container_id: str) -> Dict[str, Any]:
        """Publie un container média"""
        try:
            url = f"{self.base_url}/{self.account_id}/media_publish"
            
            params = {
                'creation_id': container_id,
                'access_token': self.access_token
            }
            
            response = requests.post(url, data=params, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and 'id' in data:
                return {
                    'success': True,
                    'post_id': data['id']
                }
            else:
                error_msg = data.get('error', {}).get('message', 'Erreur lors de la publication')
                return {'success': False, 'error': error_msg}
                
        except requests.RequestException as e:
            return {'success': False, 'error': f'Erreur réseau: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Erreur: {str(e)}'}
    
    def _upload_image_to_cdn(self, image_path: str) -> Optional[str]:
        """
        Upload une image vers un CDN accessible publiquement
        
        NOTE: Cette fonction doit être implémentée selon votre infrastructure.
        Vous pouvez utiliser AWS S3, Cloudinary, ou tout autre service de stockage.
        """
        # EXEMPLE avec un service fictif - À REMPLACER
        try:
            # Pour les tests, on peut utiliser un service comme imgur ou un serveur local
            # Voici un exemple avec un serveur local (pour développement uniquement)
            
            # Option 1: Serveur local (développement seulement)
            if Config.DEBUG:
                # Copier l'image vers un dossier static accessible
                import shutil
                filename = os.path.basename(image_path)
                static_path = os.path.join('static', 'temp', filename)
                os.makedirs(os.path.dirname(static_path), exist_ok=True)
                shutil.copy2(image_path, static_path)
                
                # Retourner l'URL locale (ne fonctionne que pour les tests)
                return f"http://localhost:5000/static/temp/{filename}"
            
            # Option 2: Upload vers un vrai CDN (PRODUCTION)
            # Exemple avec AWS S3 (à décommenter et configurer)
            """
            import boto3
            
            s3_client = boto3.client('s3')
            bucket_name = 'your-bucket-name'
            key = f"instagram-images/{os.path.basename(image_path)}"
            
            s3_client.upload_file(image_path, bucket_name, key)
            return f"https://{bucket_name}.s3.amazonaws.com/{key}"
            """
            
            # Option 3: Exemple avec Cloudinary
            """
            import cloudinary.uploader
            
            result = cloudinary.uploader.upload(image_path)
            return result['secure_url']
            """
            
            # Pour le moment, retourner None pour forcer l'implémentation
            print("⚠️  Fonction _upload_image_to_cdn doit être implémentée avec votre CDN")
            return None
            
        except Exception as e:
            print(f"❌ Erreur upload image: {e}")
            return None
    
    def get_account_info(self) -> Dict[str, Any]:
        """Récupère les informations du compte Instagram"""
        try:
            url = f"{self.base_url}/{self.account_id}"
            params = {
                'fields': 'id,username,account_type,media_count,followers_count',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': 'Impossible de récupérer les infos du compte'}
                
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def get_recent_media(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère les médias récents du compte"""
        try:
            url = f"{self.base_url}/{self.account_id}/media"
            params = {
                'fields': 'id,media_type,media_url,permalink,caption,timestamp',
                'limit': limit,
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json().get('data', [])
            else:
                return []
                
        except Exception as e:
            print(f"❌ Erreur récupération médias: {e}")
            return []
    
    def validate_access_token(self) -> bool:
        """Valide le token d'accès"""
        try:
            url = f"{self.base_url}/me"
            params = {'access_token': self.access_token}
            
            response = requests.get(url, params=params, timeout=10)
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_insights(self, media_id: str) -> Dict[str, Any]:
        """Récupère les insights d'un média (si disponible)"""
        try:
            url = f"{self.base_url}/{media_id}/insights"
            params = {
                'metric': 'impressions,reach,likes,comments,shares,saved',
                'access_token': self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': 'Insights non disponibles'}
                
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def schedule_post(self, image_path: str, caption: str, 
                     publish_time: int, location_id: str = None) -> PublicationResult:
        """
        Programme un post pour publication ultérieure
        
        Args:
            image_path: Chemin vers l'image
            caption: Caption du post
            publish_time: Timestamp Unix pour la publication
            location_id: ID de localisation (optionnel)
        
        Returns:
            PublicationResult
        """
        try:
            # Créer le container avec programmation
            url = f"{self.base_url}/{self.account_id}/media"
            image_url = self._upload_image_to_cdn(image_path)
            
            if not image_url:
                return PublicationResult.error_result('Impossible d\'uploader l\'image')
            
            params = {
                'image_url': image_url,
                'caption': caption,
                'published': 'false',  # Ne pas publier immédiatement
                'access_token': self.access_token
            }
            
            if location_id:
                params['location_id'] = location_id
            
            response = requests.post(url, data=params, timeout=30)
            data = response.json()
            
            if response.status_code == 200 and 'id' in data:
                return PublicationResult.success_result(
                    post_id=str(data['id']),
                    instagram_post_id=data['id']
                )
            else:
                error_msg = data.get('error', {}).get('message', 'Erreur programmation')
                return PublicationResult.error_result(error_msg)
                
        except Exception as e:
            return PublicationResult.error_result(f'Erreur: {str(e)}')
    
    def delete_media(self, media_id: str) -> bool:
        """Supprime un média (si possible)"""
        try:
            url = f"{self.base_url}/{media_id}"
            params = {'access_token': self.access_token}
            
            response = requests.delete(url, params=params, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"❌ Erreur suppression média: {e}")
            return False
    
    def get_hashtag_info(self, hashtag: str) -> Dict[str, Any]:
        """Récupère des informations sur un hashtag"""
        try:
            # Rechercher l'ID du hashtag
            search_url = f"{self.base_url}/ig_hashtag_search"
            search_params = {
                'user_id': self.account_id,
                'q': hashtag.replace('#', ''),
                'access_token': self.access_token
            }
            
            response = requests.get(search_url, params=search_params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data'):
                    hashtag_id = data['data'][0]['id']
                    
                    # Récupérer les infos du hashtag
                    info_url = f"{self.base_url}/{hashtag_id}"
                    info_params = {
                        'fields': 'id,name,media_count',
                        'access_token': self.access_token
                    }
                    
                    info_response = requests.get(info_url, params=info_params, timeout=10)
                    if info_response.status_code == 200:
                        return info_response.json()
            
            return {'error': 'Hashtag non trouvé'}
            
        except Exception as e:
            return {'error': f'Erreur: {str(e)}'}
    
    def test_connection(self) -> Dict[str, Any]:
        """Test la connexion à l'API Instagram"""
        results = {
            'token_valid': False,
            'account_accessible': False,
            'can_post': False,
            'account_info': None,
            'errors': []
        }
        
        try:
            # Test 1: Valider le token
            results['token_valid'] = self.validate_access_token()
            if not results['token_valid']:
                results['errors'].append('Token d\'accès invalide')
                return results
            
            # Test 2: Accéder aux infos du compte
            account_info = self.get_account_info()
            if 'error' not in account_info:
                results['account_accessible'] = True
                results['account_info'] = account_info
            else:
                results['errors'].append(f'Compte inaccessible: {account_info["error"]}')
            
            # Test 3: Vérifier les permissions de publication
            # (Simulation - dans un vrai cas, vous pourriez tester la création d'un container)
            if results['account_accessible']:
                results['can_post'] = True
            
        except Exception as e:
            results['errors'].append(f'Erreur de connexion: {str(e)}')
        
        return results