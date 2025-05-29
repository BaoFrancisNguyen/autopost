# models.py - Version corrigée pour éviter les erreurs de base de données
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

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

@dataclass
class Post:
    """Modèle pour un post Instagram"""
    title: str
    description: str
    hashtags: str
    image_prompt: str
    topic: str
    tone: str = ContentTone.ENGAGING.value
    id: Optional[int] = None
    image_path: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    status: str = PostStatus.DRAFT.value  # Utiliser la valeur string directement
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    instagram_post_id: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialisation après création de l'objet"""
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # S'assurer que le statut est une string, pas un Enum
        if hasattr(self.status, 'value'):
            self.status = self.status.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit le post en dictionnaire"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'hashtags': self.hashtags,
            'image_prompt': self.image_prompt,
            'topic': self.topic,
            'tone': self.tone,
            'image_path': self.image_path,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'status': self.status,  # Toujours une string
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'instagram_post_id': self.instagram_post_id,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Crée un post à partir d'un dictionnaire"""
        # Conversion des dates
        if data.get('scheduled_time'):
            data['scheduled_time'] = datetime.fromisoformat(data['scheduled_time'])
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        return cls(**data)
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'Post':
        """Crée un post à partir d'une ligne de base de données"""
        return cls(
            id=row[0],
            title=row[1],
            description=row[2],
            hashtags=row[3],
            image_prompt=row[4],
            topic=row[5],
            tone=row[6] if row[6] else ContentTone.ENGAGING.value,
            image_path=row[7],
            scheduled_time=datetime.fromisoformat(row[8]) if row[8] else None,
            status=row[9] if row[9] else PostStatus.DRAFT.value,  # String directement
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
            updated_at=datetime.fromisoformat(row[11]) if row[11] else None,
            instagram_post_id=row[12],
            error_message=row[13]
        )
    
    def get_full_caption(self) -> str:
        """Retourne le caption complet (description + hashtags)"""
        if self.hashtags:
            return f"{self.description}\n\n{self.hashtags}"
        return self.description
    
    def is_ready_to_publish(self) -> bool:
        """Vérifie si le post est prêt à être publié"""
        return (
            self.status == PostStatus.SCHEDULED.value and
            self.scheduled_time and
            self.scheduled_time <= datetime.now() and
            self.image_path and
            self.description
        )
    
    def can_be_published(self) -> bool:
        """Vérifie si le post peut être publié"""
        return (
            self.status in [PostStatus.DRAFT.value, PostStatus.SCHEDULED.value, PostStatus.FAILED.value] and
            self.description  # Image pas obligatoire pour tester
        )
    
    def update_status(self, new_status: str, error_message: str = None):
        """Met à jour le statut du post"""
        # S'assurer que c'est une string
        if hasattr(new_status, 'value'):
            new_status = new_status.value
        
        self.status = new_status
        self.error_message = error_message
        self.updated_at = datetime.now()

@dataclass
class GenerationRequest:
    """Modèle pour une demande de génération de contenu"""
    topic: str
    tone: ContentTone
    image_prompt: str
    additional_instructions: Optional[str] = None
    target_audience: Optional[str] = None
    include_call_to_action: bool = True
    max_hashtags: int = 15
    language: str = "fr"
    
    def to_prompt(self) -> str:
        """Convertit la demande en prompt pour l'IA"""
        prompt_parts = [
            f"Créez une description Instagram {self.tone.value} pour le sujet: {self.topic}",
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
    
    @classmethod
    def success_result(cls, post_id: str, instagram_post_id: str) -> 'PublicationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            post_id=post_id,
            instagram_post_id=instagram_post_id
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
    
    @classmethod
    def success_result(cls, image_path: str, prompt_used: str) -> 'ImageGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            image_path=image_path,
            prompt_used=prompt_used
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
class ContentGenerationResult:
    """Résultat d'une génération de contenu"""
    success: bool
    description: Optional[str] = None
    hashtags: Optional[str] = None
    error_message: Optional[str] = None
    
    @classmethod
    def success_result(cls, description: str, hashtags: str) -> 'ContentGenerationResult':
        """Crée un résultat de succès"""
        return cls(
            success=True,
            description=description,
            hashtags=hashtags
        )
    
    @classmethod
    def error_result(cls, error_message: str) -> 'ContentGenerationResult':
        """Crée un résultat d'erreur"""
        return cls(
            success=False,
            error_message=error_message
        )


# Fonctions utilitaires pour éviter les erreurs de conversion
def status_to_string(status) -> str:
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