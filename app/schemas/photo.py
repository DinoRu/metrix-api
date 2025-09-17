import os
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from typing import Dict

from pydantic import BaseModel, Field, validator

from app.core.s3_config import S3Config


class PhotoBase(BaseModel):
    reading_id: UUID


class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., description="Nom du fichier à uploader")
    content_type: str = Field(..., description="Type MIME du fichier")
    file_size: Optional[int] = Field(None, description="Taille du fichier en octets (optionnel)")
    metadata: Optional[Dict[str, str]] = Field(None, description="Métadonnées additionnelles")

    @validator('content_type')
    def validate_content_type(cls, v):
        if v not in S3Config.ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Type de contenu non autorisé: {v}")
        return v

    @validator('file_size', always=True)
    def validate_file_size(cls, v):
        if v is not None and v > S3Config.MAX_FILE_SIZE:
            raise ValueError(f"Fichier trop volumineux: {v} octets (max: {S3Config.MAX_FILE_SIZE})")
        return v

    @validator('filename')
    def validate_filename(cls, v):
        ext = os.path.splitext(v)[1].lower()
        if ext not in S3Config.ALLOWED_EXTENSIONS:
            raise ValueError(f"Extension non autorisée: {ext}")
        return v


class PresignedUrlResponse(BaseModel):
    upload_url: str = Field(..., description="URL pré-signée pour l'upload")
    upload_method: str = Field(default="PUT", description="Méthode HTTP à utiliser")
    upload_headers: Dict[str, str] = Field(..., description="Headers à inclure dans la requête")
    file_key: str = Field(..., description="Clé S3 du fichier")
    file_id: str = Field(..., description="ID unique du fichier")
    expires_at: datetime = Field(..., description="Date d'expiration de l'URL")
    public_url: str = Field(..., description="URL publique finale du fichier")


class PresignedPostResponse(BaseModel):
    """Réponse pour upload avec POST (formulaire)"""
    upload_url: str = Field(..., description="URL d'upload")
    form_fields: Dict[str, str] = Field(..., description="Champs du formulaire à envoyer")
    file_key: str = Field(..., description="Clé S3 du fichier")
    file_id: str = Field(..., description="ID unique du fichier")
    expires_at: datetime = Field(..., description="Date d'expiration")
    public_url: str = Field(..., description="URL publique finale")



class ConfirmUploadRequest(BaseModel):
    """Requête pour confirmer un upload réussi"""
    file_id: str = Field(..., description="ID du fichier uploadé")
    file_key: str = Field(..., description="Clé S3 du fichier")
    etag: Optional[str] = Field(None, description="ETag retourné par S3")
    version_id: Optional[str] = Field(None, description="Version ID si versioning activé")



class ImageResponse(BaseModel):
    """Modèle de réponse pour une image"""
    id: str = Field(..., description="Identifiant unique de l'image")
    filename: str = Field(..., description="Nom du fichier original")
    url: str = Field(..., description="URL publique de l'image")
    cdn_url: Optional[str] = Field(None, description="URL CDN si disponible")
    size: int = Field(..., description="Taille du fichier en octets")
    content_type: str = Field(..., description="Type MIME du fichier")
    uploaded_at: datetime = Field(..., description="Date et heure d'upload")
    metadata: Optional[Dict[str, str]] = Field(None, description="Métadonnées")
    etag: Optional[str] = Field(None, description="ETag du fichier")


class ImageListResponse(BaseModel):
    """Modèle de réponse pour la liste des images"""
    images: List[ImageResponse]
    total: int = Field(..., description="Nombre total d'images")
    next_token: Optional[str] = Field(None, description="Token pour la pagination")


class ErrorResponse(BaseModel):
    """Modèle de réponse d'erreur"""
    error: str = Field(..., description="Message d'erreur")
    detail: Optional[str] = Field(None, description="Détails supplémentaires")

class UpdateInfo(BaseModel):
    version: str
    apk_url: str
    changelog: str | None = None
