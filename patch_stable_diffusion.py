# ============================================================================
# PATCH POUR CORRIGER STABLE DIFFUSION DANS app.py
# ============================================================================
# 
# INSTRUCTIONS:
# 1. Ouvrez votre fichier app.py
# 2. Trouvez la fonction init_services()
# 3. Cherchez la section "GÉNÉRATEUR D'IMAGES" (environ ligne 150-250)
# 4. Remplacez TOUTE la section concernant les images par le code ci-dessous
# 5. Sauvegardez et relancez: python app.py
#
# ============================================================================

    # ===== GÉNÉRATEUR D'IMAGES (Stable Diffusion - CORRECTION MAJEURE) =====
    print("\n🎨 Configuration génération d'images...")
    
    # A. Stable Diffusion (priorité 1 - local et gratuit)
    if Config.USE_STABLE_DIFFUSION:
        try:
            from services.stable_diffusion_generator import StableDiffusionGenerator
            
            print(f"🔄 Initialisation Stable Diffusion sur {Config.STABLE_DIFFUSION_URL}...")
            app.sd_generator = StableDiffusionGenerator(Config.STABLE_DIFFUSION_URL)
            
            # ✅ VÉRIFICATION CRITIQUE - C'est ici que ça coince normalement!
            if hasattr(app.sd_generator, 'is_available') and app.sd_generator.is_available:
                # ✅✅✅ STABLE DIFFUSION FONCTIONNE!
                app.image_generator = app.sd_generator
                print("✅✅✅ Stable Diffusion ACTIF et configuré comme générateur principal!")
                print(f"   🌐 URL: {Config.STABLE_DIFFUSION_URL}")
                
                # Afficher des infos supplémentaires
                try:
                    models = app.sd_generator.get_available_models()
                    if models:
                        print(f"   🧠 {len(models)} modèle(s) disponible(s)")
                        current_model = app.sd_generator.get_current_model()
                        print(f"   📋 Modèle actuel: {current_model}")
                except Exception as e:
                    print(f"   ⚠️  Impossible de récupérer les modèles: {e}")
            else:
                print(f"⚠️  Stable Diffusion configuré mais NON ACCESSIBLE sur {Config.STABLE_DIFFUSION_URL}")
                print(f"💡 Vérifiez que SD est démarré avec: webui-user.bat --api (Windows)")
                print(f"💡 Ou: ./webui.sh --api (Linux/Mac)")
                
        except ImportError as e:
            print(f"❌ Module Stable Diffusion manquant: {e}")
            print("💡 Le fichier services/stable_diffusion_generator.py est requis")
        except Exception as e:
            print(f"❌ Erreur Stable Diffusion: {e}")
            import traceback
            traceback.print_exc()
    
    # B. Hugging Face (priorité 2 - gratuit en ligne)
    if Config.USE_HUGGINGFACE and not app.image_generator:
        try:
            from services.stable_diffusion_generator import HuggingFaceGenerator
            app.hf_generator = HuggingFaceGenerator(Config.HUGGINGFACE_API_TOKEN)
            app.image_generator = app.hf_generator
            print("✅ Hugging Face configuré comme générateur d'images")
        except ImportError as e:
            print(f"❌ Module Hugging Face manquant: {e}")
        except Exception as e:
            print(f"❌ Erreur Hugging Face: {e}")
    
    # C. OpenAI DALL-E (priorité 3 - payant mais fiable)
    if Config.OPENAI_API_KEY and not app.image_generator:
        try:
            import openai
            from services.ai_generator import AIImageGenerator
            openai_generator = AIImageGenerator(Config.OPENAI_API_KEY)
            app.image_generator = openai_generator
            print("✅ OpenAI DALL-E configuré comme générateur d'images")
        except ImportError:
            print("❌ Module OpenAI manquant")
            print("💡 Installez avec: pip install openai")
        except Exception as e:
            print(f"❌ Erreur OpenAI: {e}")
    
    # D. GÉNÉRATEUR PLACEHOLDER si aucun service disponible
    if not app.image_generator:
        print("⚠️  Aucun service de génération d'images disponible")
        print("💡 Pour activer la génération d'images:")
        print("   1. Stable Diffusion: Démarrez l'interface web avec --api")
        print("   2. Hugging Face: Ajoutez HUGGINGFACE_API_TOKEN=your_token dans .env")
        print("   3. OpenAI: Installez openai et ajoutez OPENAI_API_KEY dans .env")
        
        # Créer un générateur factice pour éviter les erreurs
        class PlaceholderImageGenerator:
            def generate_image(self, prompt, **kwargs):
                from models import ImageGenerationResult
                return ImageGenerationResult.error_result(
                    "Aucun service de génération d'images configuré", 
                    service_used="placeholder"
                )
            
            def validate_prompt(self, prompt):
                return True, "OK"
        
        app.image_generator = PlaceholderImageGenerator()
        print("🔧 Générateur placeholder créé (pas de génération réelle)")
    
    # Résumé du service d'images actif
    def get_active_service():
        if hasattr(app, 'sd_generator') and app.sd_generator and getattr(app.sd_generator, 'is_available', False):
            return "Stable Diffusion"
        elif hasattr(app, 'hf_generator') and app.hf_generator:
            return "Hugging Face"
        elif hasattr(app, 'image_generator') and app.image_generator and not hasattr(app.image_generator, 'is_available'):
            return "OpenAI DALL-E"
        else:
            return "Placeholder (aucun service actif)"
    
    service_name = get_active_service()
    print(f"🎨 Service d'images actif: {service_name}")

# ============================================================================
# FIN DU PATCH
# ============================================================================
# 
# APRÈS AVOIR APPLIQUÉ CE PATCH:
# 
# 1. Vérifiez que Stable Diffusion est démarré:
#    - Windows: webui-user.bat --api
#    - Linux/Mac: ./webui.sh --api
#    - Par défaut sur http://localhost:7860
#
# 2. Vérifiez votre .env:
#    USE_STABLE_DIFFUSION=True
#    STABLE_DIFFUSION_URL=http://localhost:7861  (ou 7860 selon votre config)
#
# 3. Relancez l'application:
#    python app.py
#
# 4. Vous devriez voir:
#    ✅✅✅ Stable Diffusion ACTIF et configuré comme générateur principal!
#
# Si vous voyez toujours "NON ACCESSIBLE", vérifiez:
# - Le port (7860 vs 7861)
# - Que SD est bien lancé
# - Qu'il n'y a pas de firewall qui bloque
#
# ============================================================================
