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
    image_prompt: str  # ✅ CORRIGÉ: Changé de media_prompt à image_prompt
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
        
        # S'assurer que media_type est une string
        if hasattr(self.media_type, 'value'):
            self.media_type = self.media_type.value
        
        # S'assurer que tone est une string
        if hasattr(self.tone, 'value'):
            self.tone = self.tone.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le post en dictionnaire"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'hashtags': self.hashtags,
            'image_prompt': self.image_prompt,  # ✅ CORRIGÉ
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
            'generation_params': self.generation_params,
            'views_count': self.views_count,
            'likes_count': self.likes_count,
            'comments_count': self.comments_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Crée un post à partir d'un dictionnaire"""
        # Convertir les dates ISO en datetime
        if data.get('scheduled_time') and isinstance(data['scheduled_time'], str):
            data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'])
        if data.get('created_at') and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at') and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Filtrer les champs qui ne sont pas dans le constructeur
        constructor_fields = {
            'id', 'title', 'description', 'hashtags', 'image_prompt', 'topic', 'tone',
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
            image_prompt=row[4],  # ✅ CORRIGÉ
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
    image_prompt: str  # ✅ CORRIGÉ
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
            prompt_parts.append(f"Public cible: {self.target_audience}")
        
        if self.additional_instructions:
            prompt_parts.append(f"Instructions supplémentaires: {self.additional_instructions}")
        
        if self.include_call_to_action:
            prompt_parts.append("Incluez un appel à l'action engageant")
        
        prompt_parts.append(f"Générez jusqu'à {self.max_hashtags} hashtags pertinents")
        
        return "\n".join(prompt_parts)


@dataclass
class GenerationResult:
    """Modèle pour le résultat d'une génération"""
    success: bool
    content: Optional[str] = None
    hashtags: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    image_prompt: Optional[str] = None  # ✅ CORRIGÉ
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    service_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'success': self.success,
            'content': self.content,
            'hashtags': self.hashtags,
            'image_path': self.image_path,
            'video_path': self.video_path,
            'image_prompt': self.image_prompt,  # ✅ CORRIGÉ
            'error_message': self.error_message,
            'generation_time': self.generation_time,
            'service_used': self.service_used
        }


@dataclass
class ImageGenerationResult:
    """Modèle pour le résultat d'une génération d'image"""
    success: bool
    image_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    service_used: Optional[str] = None
    prompt_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'success': self.success,
            'image_path': self.image_path,
            'error_message': self.error_message,
            'generation_time': self.generation_time,
            'service_used': self.service_used,
            'prompt_used': self.prompt_used
        }
    
    @classmethod
    def error_result(cls, error_message: str, service_used: str = "unknown") -> 'ImageGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message,
            service_used=service_used
        )
    
    @classmethod
    def success_result(cls, image_path: str, service_used: str, prompt_used: str = None, generation_time: float = None) -> 'ImageGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            image_path=image_path,
            service_used=service_used,
            prompt_used=prompt_used,
            generation_time=generation_time
        )


@dataclass
class VideoGenerationResult:
    """Modèle pour le résultat d'une génération de vidéo"""
    success: bool
    video_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    service_used: Optional[str] = None
    prompt_used: Optional[str] = None
    duration: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'success': self.success,
            'video_path': self.video_path,
            'error_message': self.error_message,
            'generation_time': self.generation_time,
            'service_used': self.service_used,
            'prompt_used': self.prompt_used,
            'duration': self.duration
        }
    
    @classmethod
    def error_result(cls, error_message: str, service_used: str = "unknown") -> 'VideoGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message,
            service_used=service_used
        )
    
    @classmethod
    def success_result(cls, video_path: str, service_used: str, prompt_used: str = None, 
                      generation_time: float = None, duration: float = None) -> 'VideoGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            video_path=video_path,
            service_used=service_used,
            prompt_used=prompt_used,
            generation_time=generation_time,
            duration=duration
        )


@dataclass
class InstagramMediaMetrics:
    """Métadonnées pour un média Instagram"""
    media_id: str
    media_type: str
    caption: Optional[str] = None
    permalink: Optional[str] = None
    timestamp: Optional[datetime] = None
    like_count: int = 0
    comments_count: int = 0
    views_count: int = 0  # Pour les vidéos
    saved_count: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'InstagramMediaMetrics':
        """Crée des métriques depuis une réponse API Instagram"""
        timestamp = None
        if data.get('timestamp'):
            try:
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
            except:
                pass
        
        return cls(
            media_id=data.get('id', ''),
            media_type=data.get('media_type', 'IMAGE'),
            caption=data.get('caption', ''),
            permalink=data.get('permalink', ''),
            timestamp=timestamp,
            like_count=data.get('like_count', 0),
            comments_count=data.get('comments_count', 0),
            views_count=data.get('video_views', 0),
            saved_count=data.get('saved', 0),
            reach=data.get('reach', 0),
            impressions=data.get('impressions', 0)
        )


@dataclass
class ScheduledPost:
    """Modèle pour un post planifié"""
    post_id: int
    scheduled_time: datetime
    status: str = PostStatus.SCHEDULED.value
    retry_count: int = 0
    last_retry: Optional[datetime] = None
    
    def should_retry(self, max_retries: int = 3) -> bool:
        """Vérifie si un nouveau essai est possible"""
        return self.retry_count < max_retries
    
    def increment_retry(self):
        """Incrémente le compteur de tentatives"""
        self.retry_count += 1
        self.last_retry = datetime.now()


@dataclass
class PublicationResult:
    """Résultat d'une publication Instagram"""
    success: bool
    instagram_post_id: Optional[str] = None
    error_message: Optional[str] = None
    permalink: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'success': self.success,
            'instagram_post_id': self.instagram_post_id,
            'error_message': self.error_message,
            'permalink': self.permalink,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def success_result(cls, instagram_post_id: str, permalink: str = None) -> 'PublicationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            instagram_post_id=instagram_post_id,
            permalink=permalink,
            timestamp=datetime.now()
        )
    
    @classmethod
    def error_result(cls, error_message: str) -> 'PublicationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message,
            timestamp=datetime.now()
        )


class ConfigurationSettings:
    """Paramètres de configuration de l'application"""
    
    def __init__(self):
        self.ai_service: str = "ollama"
        self.ollama_model: str = "mistral:latest"
        self.ollama_url: str = "http://localhost:11434"
        self.stable_diffusion_url: str = "http://localhost:7861"
        self.default_steps: int = 20
        self.default_cfg_scale: float = 7.0
        self.auto_publish: bool = False
        self.notification_email: Optional[str] = None
        self.backup_enabled: bool = True
        self.backup_frequency_hours: int = 24
        
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            'ai_service': self.ai_service,
            'ollama_model': self.ollama_model,
            'ollama_url': self.ollama_url,
            'stable_diffusion_url': self.stable_diffusion_url,
            'default_steps': self.default_steps,
            'default_cfg_scale': self.default_cfg_scale,
            'auto_publish': self.auto_publish,
            'notification_email': self.notification_email,
            'backup_enabled': self.backup_enabled,
            'backup_frequency_hours': self.backup_frequency_hours
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigurationSettings':
        """Crée depuis un dictionnaire"""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config