# models.py - Modèles de données complets pour Instagram Automation avec support vidéo
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import os
import json


class PostStatus(Enum):
    """Statuts possibles pour un post"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    PROCESSING = "processing"


class ContentTone(Enum):
    """Tons possibles pour le contenu généré"""
    ENGAGING = "engageant"
    PROFESSIONAL = "professionnel"
    CASUAL = "décontracté"
    INSPIRING = "inspirant"
    HUMOROUS = "humoristique"
    EDUCATIONAL = "éducatif"


class MediaType(Enum):
    """Types de médias supportés"""
    IMAGE = "image"
    VIDEO = "video"
    CAROUSEL = "carousel"  # Pour futures extensions


class GenerationService(Enum):
    """Services de génération disponibles"""
    STABLE_DIFFUSION = "stable_diffusion"
    STABLE_VIDEO_DIFFUSION = "stable_video_diffusion"
    HUGGINGFACE = "huggingface"
    OPENAI_DALLE = "openai_dalle"
    OLLAMA = "ollama"


@dataclass
class Post:
    """Modèle pour un post Instagram avec support multimédia"""
    title: str
    description: str
    hashtags: str
    media_prompt: str  # Prompt pour image ou vidéo
    topic: str
    tone: str = ContentTone.ENGAGING.value
    media_type: str = MediaType.IMAGE.value  # "image" ou "video"
    id: Optional[int] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: str = PostStatus.DRAFT.value
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    instagram_post_id: Optional[str] = None
    error_message: Optional[str] = None
    generation_service: Optional[str] = None  # Service utilisé pour générer le média
    generation_params: Optional[str] = None  # Paramètres JSON de génération
    views_count: Optional[int] = None
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    
    def __post_init__(self):
        """Initialisation après création de l'objet"""
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # S'assurer que le statut est une string, pas un Enum
        if hasattr(self.status, 'value'):
            self.status = self.status.value
        
        # S'assurer que le type de média est valide
        if hasattr(self.media_type, 'value'):
            self.media_type = self.media_type.value
    
    def get_media_path(self) -> Optional[str]:
        """Retourne le chemin du média principal selon le type"""
        if self.media_type == MediaType.VIDEO.value and self.video_path:
            return self.video_path
        elif self.media_type == MediaType.IMAGE.value and self.image_path:
            return self.image_path
        # Fallback: retourner le premier média disponible
        return self.video_path or self.image_path
    
    def get_media_url(self, base_url: str = "/static/generated") -> Optional[str]:
        """Retourne l'URL du média pour l'affichage web"""
        media_path = self.get_media_path()
        if not media_path:
            return None
        
        filename = os.path.basename(media_path)
        if self.media_type == MediaType.VIDEO.value:
            return f"{base_url}/videos/{filename}"
        else:
            return f"{base_url}/{filename}"
    
    def has_media(self) -> bool:
        """Vérifie si le post a un média"""
        return bool(self.get_media_path())
    
    def has_image(self) -> bool:
        """Vérifie si le post a une image"""
        return bool(self.image_path and os.path.exists(self.image_path))
    
    def has_video(self) -> bool:
        """Vérifie si le post a une vidéo"""
        return bool(self.video_path and os.path.exists(self.video_path))
    
    def get_full_caption(self) -> str:
        """Retourne le caption complet (description + hashtags)"""
        caption_parts = []
        
        if self.description:
            caption_parts.append(self.description)
        
        if self.hashtags:
            # S'assurer qu'il y a une ligne vide entre description et hashtags
            if caption_parts:
                caption_parts.append("")
            caption_parts.append(self.hashtags)
        
        return "\n".join(caption_parts)
    
    def is_ready_to_publish(self) -> bool:
        """Vérifie si le post est prêt à être publié maintenant"""
        return (
            self.status == PostStatus.SCHEDULED.value and
            self.scheduled_time and
            self.scheduled_time <= datetime.now() and
            self.has_media() and
            self.description
        )
    
    def can_be_published(self) -> bool:
        """Vérifie si le post peut être publié (conditions générales)"""
        return (
            self.status in [PostStatus.DRAFT.value, PostStatus.SCHEDULED.value, PostStatus.FAILED.value] and
            self.description and
            self.has_media()
        )
    
    def is_published(self) -> bool:
        """Vérifie si le post est publié"""
        return self.status == PostStatus.PUBLISHED.value
    
    def is_scheduled(self) -> bool:
        """Vérifie si le post est programmé"""
        return (
            self.status == PostStatus.SCHEDULED.value and
            self.scheduled_time and
            self.scheduled_time > datetime.now()
        )
    
    def get_status_display(self) -> Dict[str, str]:
        """Retourne les informations d'affichage du statut"""
        status_info = {
            PostStatus.DRAFT.value: {"label": "Brouillon", "icon": "fas fa-edit", "class": "secondary"},
            PostStatus.SCHEDULED.value: {"label": "Programmé", "icon": "fas fa-clock", "class": "warning"},
            PostStatus.PUBLISHED.value: {"label": "Publié", "icon": "fas fa-check-circle", "class": "success"},
            PostStatus.FAILED.value: {"label": "Échec", "icon": "fas fa-exclamation-triangle", "class": "danger"},
            PostStatus.PROCESSING.value: {"label": "En cours", "icon": "fas fa-spinner", "class": "info"}
        }
        
        return status_info.get(self.status, {"label": "Inconnu", "icon": "fas fa-question", "class": "secondary"})
    
    def get_media_type_display(self) -> Dict[str, str]:
        """Retourne les informations d'affichage du type de média"""
        media_info = {
            MediaType.IMAGE.value: {"label": "Image", "icon": "fas fa-image", "class": "primary"},
            MediaType.VIDEO.value: {"label": "Vidéo", "icon": "fas fa-video", "class": "success"},
            MediaType.CAROUSEL.value: {"label": "Carrousel", "icon": "fas fa-images", "class": "info"}
        }
        
        return media_info.get(self.media_type, {"label": "Média", "icon": "fas fa-file", "class": "secondary"})
    
    def update_status(self, new_status: Union[str, PostStatus], error_message: str = None):
        """Met à jour le statut du post"""
        if isinstance(new_status, PostStatus):
            new_status = new_status.value
        
        self.status = new_status
        self.error_message = error_message
        self.updated_at = datetime.now()
    
    def set_generation_params(self, service: str, params: Dict[str, Any]):
        """Enregistre les paramètres de génération"""
        self.generation_service = service
        self.generation_params = json.dumps(params) if params else None
    
    def get_generation_params(self) -> Dict[str, Any]:
        """Récupère les paramètres de génération"""
        if not self.generation_params:
            return {}
        try:
            return json.loads(self.generation_params)
        except json.JSONDecodeError:
            return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le post en dictionnaire"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'hashtags': self.hashtags,
            'media_prompt': self.media_prompt,
            'topic': self.topic,
            'tone': self.tone,
            'media_type': self.media_type,
            'image_path': self.image_path,
            'video_path': self.video_path,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'instagram_post_id': self.instagram_post_id,
            'error_message': self.error_message,
            'generation_service': self.generation_service,
            'generation_params': self.get_generation_params(),
            'views_count': self.views_count,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count,
            'media_url': self.get_media_url(),
            'has_media': self.has_media(),
            'has_image': self.has_image(),
            'has_video': self.has_video(),
            'status_display': self.get_status_display(),
            'media_type_display': self.get_media_type_display()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Crée un post à partir d'un dictionnaire"""
        # Conversion des dates
        for date_field in ['scheduled_time', 'created_at', 'updated_at']:
            if data.get(date_field):
                try:
                    data[date_field] = datetime.fromisoformat(data[date_field])
                except (ValueError, TypeError):
                    data[date_field] = None
        
        # Nettoyer les champs qui ne sont pas dans le constructeur
        constructor_fields = {
            'id', 'title', 'description', 'hashtags', 'media_prompt', 'topic', 'tone',
            'media_type', 'image_path', 'video_path', 'scheduled_time', 'status',
            'created_at', 'updated_at', 'instagram_post_id', 'error_message',
            'generation_service', 'generation_params', 'views_count', 'likes_count', 'comments_count'
        }
        
        clean_data = {k: v for k, v in data.items() if k in constructor_fields}
        
        return cls(**clean_data)
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'Post':
        """Crée un post à partir d'une ligne de base de données"""
        # Mapping des colonnes (à adapter selon votre schéma de DB)
        return cls(
            id=row[0],
            title=row[1],
            description=row[2],
            hashtags=row[3],
            media_prompt=row[4],
            topic=row[5],
            tone=row[6] if row[6] else ContentTone.ENGAGING.value,
            media_type=row[7] if row[7] else MediaType.IMAGE.value,
            image_path=row[8],
            video_path=row[9],
            scheduled_time=datetime.fromisoformat(row[10]) if row[10] else None,
            status=row[11] if row[11] else PostStatus.DRAFT.value,
            created_at=datetime.fromisoformat(row[12]) if row[12] else None,
            updated_at=datetime.fromisoformat(row[13]) if row[13] else None,
            instagram_post_id=row[14],
            error_message=row[15],
            generation_service=row[16] if len(row) > 16 else None,
            generation_params=row[17] if len(row) > 17 else None,
            views_count=row[18] if len(row) > 18 else None,
            likes_count=row[19] if len(row) > 19 else None,
            comments_count=row[20] if len(row) > 20 else None
        )


@dataclass
class GenerationRequest:
    """Modèle pour une demande de génération de contenu"""
    topic: str
    tone: ContentTone
    media_prompt: str
    media_type: MediaType = MediaType.IMAGE
    additional_instructions: Optional[str] = None
    target_audience: Optional[str] = None
    include_call_to_action: bool = True
    max_hashtags: int = 15
    language: str = "fr"
    
    def to_prompt(self) -> str:
        """Convertit la demande en prompt pour l'IA"""
        prompt_parts = [
            f"Créez une description Instagram {self.tone.value} pour le sujet: {self.topic}",
            f"Type de média: {self.media_type.value}",
            f"Langue: {self.language}"
        ]
        
        if self.target_audience:
            prompt_parts.append(f"Audience cible: {self.target_audience}")
        
        if self.additional_instructions:
            prompt_parts.append(f"Instructions supplémentaires: {self.additional_instructions}")
        
        if self.include_call_to_action:
            prompt_parts.append("Incluez un appel à l'action engageant")
        
        prompt_parts.extend([
            f"Utilisez maximum {self.max_hashtags} hashtags pertinents et populaires",
            "",
            "Format de réponse:",
            "DESCRIPTION: [description ici]",
            "HASHTAGS: [hashtags séparés par des espaces]"
        ])
        
        return "\n".join(prompt_parts)


@dataclass
class PublicationResult:
    """Résultat d'une tentative de publication"""
    success: bool
    post_id: Optional[str] = None
    error_message: Optional[str] = None
    instagram_post_id: Optional[str] = None
    platform_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, post_id: str, instagram_post_id: str, 
                      platform_data: Dict[str, Any] = None) -> 'PublicationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            post_id=post_id,
            instagram_post_id=instagram_post_id,
            platform_data=platform_data or {}
        )
    
    @classmethod
    def error_result(cls, error_message: str, post_id: str = None) -> 'PublicationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            post_id=post_id,
            error_message=error_message
        )


@dataclass
class ImageGenerationResult:
    """Résultat d'une génération d'image"""
    success: bool
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    prompt_used: Optional[str] = None
    generation_time: Optional[float] = None
    service_used: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, image_path: str, prompt_used: str, 
                      generation_time: float = None, service_used: str = None,
                      parameters: Dict[str, Any] = None) -> 'ImageGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            image_path=image_path,
            prompt_used=prompt_used,
            generation_time=generation_time,
            service_used=service_used,
            parameters=parameters or {}
        )
    
    @classmethod
    def error_result(cls, error_message: str, prompt_used: str = None) -> 'ImageGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message,
            prompt_used=prompt_used
        )


@dataclass
class VideoGenerationResult:
    """Résultat d'une génération de vidéo"""
    success: bool
    video_path: Optional[str] = None
    error_message: Optional[str] = None
    source_prompt: Optional[str] = None
    source_image_path: Optional[str] = None
    duration_seconds: Optional[float] = None
    fps: Optional[int] = None
    generation_time: Optional[float] = None
    service_used: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, video_path: str, source_prompt: str = None,
                      source_image_path: str = None, duration: float = None, 
                      fps: int = None, generation_time: float = None,
                      service_used: str = None, parameters: Dict[str, Any] = None) -> 'VideoGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            video_path=video_path,
            source_prompt=source_prompt,
            source_image_path=source_image_path,
            duration_seconds=duration,
            fps=fps,
            generation_time=generation_time,
            service_used=service_used,
            parameters=parameters or {}
        )
    
    @classmethod
    def error_result(cls, error_message: str, source_prompt: str = None,
                    source_image_path: str = None) -> 'VideoGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message,
            source_prompt=source_prompt,
            source_image_path=source_image_path
        )


@dataclass
class ContentGenerationResult:
    """Résultat d'une génération de contenu"""
    success: bool
    description: Optional[str] = None
    hashtags: Optional[str] = None
    error_message: Optional[str] = None
    service_used: Optional[str] = None
    generation_time: Optional[float] = None
    
    @classmethod
    def success_result(cls, description: str, hashtags: str, 
                      service_used: str = None, generation_time: float = None) -> 'ContentGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            description=description,
            hashtags=hashtags,
            service_used=service_used,
            generation_time=generation_time
        )
    
    @classmethod
    def error_result(cls, error_message: str) -> 'ContentGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message
        )


@dataclass
class SchedulerStats:
    """Statistiques du scheduler"""
    is_running: bool
    next_check_in: Optional[int] = None
    posts_ready: int = 0
    posts_scheduled: int = 0
    posts_failed: int = 0
    next_publication_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    total_published_today: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'is_running': self.is_running,
            'next_check_in': self.next_check_in,
            'posts_ready': self.posts_ready,
            'posts_scheduled': self.posts_scheduled,
            'posts_failed': self.posts_failed,
            'next_publication_time': self.next_publication_time.isoformat() if self.next_publication_time else None,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'total_published_today': self.total_published_today
        }


@dataclass
class ServiceStatus:
    """Statut d'un service"""
    name: str
    available: bool
    last_check: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'name': self.name,
            'available': self.available,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'error_message': self.error_message,
            'metadata': self.metadata or {}
        }


# Fonctions utilitaires pour éviter les erreurs de conversion
def status_to_string(status: Union[str, PostStatus]) -> str:
    """Convertit un statut en string de manière sûre"""
    if isinstance(status, str):
        return status
    elif hasattr(status, 'value'):
        return status.value
    else:
        return str(status)


def string_to_status_enum(status_str: str) -> PostStatus:
    """Convertit une string en enum PostStatus"""
    try:
        return PostStatus(status_str)
    except ValueError:
        return PostStatus.DRAFT


def media_type_to_string(media_type: Union[str, MediaType]) -> str:
    """Convertit un type de média en string de manière sûre"""
    if isinstance(media_type, str):
        return media_type
    elif hasattr(media_type, 'value'):
        return media_type.value
    else:
        return MediaType.IMAGE.value


def string_to_media_type_enum(media_type_str: str) -> MediaType:
    """Convertit une string en enum MediaType"""
    try:
        return MediaType(media_type_str)
    except ValueError:
        return MediaType.IMAGE


def validate_post_data(data: Dict[str, Any]) -> List[str]:
    """Valide les données d'un post et retourne les erreurs"""
    errors = []
    
    # Champs obligatoires
    required_fields = ['title', 'description', 'media_prompt', 'topic']
    for field in required_fields:
        if not data.get(field, '').strip():
            errors.append(f"Le champ '{field}' est obligatoire")
    
    # Validation du ton
    if data.get('tone') and data['tone'] not in [t.value for t in ContentTone]:
        errors.append("Ton invalide")
    
    # Validation du type de média
    if data.get('media_type') and data['media_type'] not in [m.value for m in MediaType]:
        errors.append("Type de média invalide")
    
    # Validation du statut
    if data.get('status') and data['status'] not in [s.value for s in PostStatus]:
        errors.append("Statut invalide")
    
    # Validation de la date de programmation
    if data.get('scheduled_time'):
        try:
            scheduled_time = datetime.fromisoformat(data['scheduled_time'])
            if scheduled_time <= datetime.now():
                errors.append("La date de programmation doit être dans le futur")
        except (ValueError, TypeError):
            errors.append("Format de date invalide")
    
    return errors


# Export des classes principales
__all__ = [
    'Post', 'PostStatus', 'ContentTone', 'MediaType', 'GenerationService',
    'GenerationRequest', 'PublicationResult', 'ImageGenerationResult', 
    'VideoGenerationResult', 'ContentGenerationResult', 'SchedulerStats',
    'ServiceStatus', 'status_to_string', 'string_to_status_enum',
    'media_type_to_string', 'string_to_media_type_enum', 'validate_post_data'
]