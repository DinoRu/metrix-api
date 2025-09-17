import logging

from fastapi import APIRouter, status, HTTPException, Depends, Query


from app.auth.dependencies import get_current_admin
from app.core.s3_config import S3Config

from app.schemas.photo import PresignedUrlResponse, PresignedUrlRequest, ImageResponse, \
	ConfirmUploadRequest
from app.services.storage_service import StorageService

router = APIRouter()
logger = logging.getLogger(__name__)
storage_service = StorageService()

@router.post("/presigned-url", response_model=PresignedUrlResponse, tags=["Direct Upload"])
async def get_presigned_upload_url(request: PresignedUrlRequest):
    logger.info(f"Requête reçue: {request.dict()}")
    result = storage_service.generate_presigned_url_put(request)
    logger.info(f"URL pré-signée générée: {result['upload_url']}")
    return PresignedUrlResponse(**result)


@router.post("/confirm", response_model=ImageResponse, tags=["Direct Upload"])
async def confirm_upload(request: ConfirmUploadRequest):
    """
    Confirmer qu'un upload direct a réussi

    Après un upload direct réussi, le client doit appeler cette route
    pour confirmer l'upload et enregistrer les métadonnées.
    """
    result = storage_service.confirm_upload(request)
    return ImageResponse(**result)


@router.get("/upload/verify/{file_key:path}", tags=["Direct Upload"])
async def verify_upload(file_key: str):
    """
    Vérifier si un fichier existe sur S3

    Utile pour vérifier qu'un upload a réussi avant de confirmer.
    """
    file_info = storage_service.verify_upload(file_key)

    if not file_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier non trouvé"
        )

    return {
        "exists": True,
        "file_key": file_key,
        **file_info
    }



@router.delete("/{image_id}", tags=["Images"])
async def delete_image(image_id: str, current_user= Depends(get_current_admin)):
    """
    Supprimer une image par son ID

    - **image_id**: Identifiant unique de l'image
    """
    success = storage_service.delete_image(image_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image avec l'ID {image_id} non trouvée"
        )

    return {"message": "Image supprimée avec succès", "id": image_id}


@router.get("/{file_key:path}/download-url", tags=["Images"])
async def get_download_url(
        file_key: str,
        expires_in: int = Query(3600, ge=1, le=86400, description="Durée de validité en secondes")
):
    """
    Obtenir une URL de téléchargement temporaire pour une image

    Utile pour partager des images privées de manière sécurisée.
    """
    try:
        url = storage_service.generate_presigned_download_url(file_key, expires_in)
        return {
            "download_url": url,
            "expires_in": expires_in
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/config", tags=["Configuration"])
async def get_upload_config():
    """
    Obtenir la configuration d'upload pour le client

    Retourne les limites et types de fichiers autorisés.
    """
    return {
        "max_file_size": S3Config.MAX_FILE_SIZE,
        "allowed_extensions": list(S3Config.ALLOWED_EXTENSIONS),
        "allowed_content_types": list(S3Config.ALLOWED_CONTENT_TYPES),
        "presigned_url_expiration": S3Config.PRESIGNED_URL_EXPIRATION,
    }
