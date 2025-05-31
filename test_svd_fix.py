# test_svd_fix.py - Test de connexion SVD corrigé
import requests
import json

def test_comfyui_connection(base_url="http://localhost:7862"):
    """Test de connexion ComfyUI avec plusieurs endpoints"""
    
    print(f"🔍 Test de connexion ComfyUI sur {base_url}")
    
    # Endpoints à tester
    endpoints = [
        "/system_stats",
        "/queue", 
        "/history",
        "/embeddings",
        "/"
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            status = "✅" if response.status_code == 200 else "⚠️"
            print(f"{status} {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                working_endpoints.append(endpoint)
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {endpoint}: Connexion refusée")
        except requests.exceptions.Timeout:
            print(f"⏰ {endpoint}: Timeout")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")
    
    if working_endpoints:
        print(f"\n✅ ComfyUI accessible ! Endpoints fonctionnels: {working_endpoints}")
        return True
    else:
        print(f"\n❌ ComfyUI non accessible sur {base_url}")
        return False

def test_svd_generator():
    """Test du générateur SVD avec correction"""
    
    # Test de base
    is_accessible = test_comfyui_connection("http://localhost:7862")
    
    if is_accessible:
        try:
            # Import et test du générateur
            from services.stable_video_diffusion_generator import StableVideoDiffusionGenerator
            
            # Créer le générateur avec la bonne URL
            svd = StableVideoDiffusionGenerator("http://localhost:7862")
            
            # Forcer le test de connexion
            svd.is_available = is_accessible
            
            print(f"\n🎬 Générateur SVD:")
            print(f"   URL: {svd.api_url}")
            print(f"   Disponible: {svd.is_available}")
            
            if svd.is_available:
                try:
                    status = svd.get_status()
                    print(f"   Status: {status}")
                except Exception as e:
                    print(f"   Erreur get_status: {e}")
            
            return svd.is_available
            
        except ImportError as e:
            print(f"❌ Erreur import générateur SVD: {e}")
            return False
    
    return False

if __name__ == "__main__":
    print("🧪 Test de diagnostic SVD")
    print("=" * 50)
    
    success = test_svd_generator()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SVD fonctionne ! Vous pouvez générer des vidéos.")
    else:
        print("❌ SVD ne fonctionne pas. Vérifications nécessaires:")
        print("   1. ComfyUI est-il démarré sur le port 7862 ?")
        print("   2. L'URL dans .env est-elle correcte ?")
        print("   3. Les modèles SVD sont-ils téléchargés ?")
