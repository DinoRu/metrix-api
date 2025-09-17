import io
from typing import Optional

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime

from app.core.s3_config import S3Config
from app.database import get_session
from app.auth.dependencies import get_current_user

from app.models.user import UserRole, User
from app.schemas.photo import UpdateInfo
from app.services.export_service import ExportService
from app.services.storage_service import storage_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/readings/excel")
async def export_readings_excel(
        start_date: date = Query(..., description="Date de début (YYYY-MM-DD)"),
        end_date: date = Query(..., description="Date de fin (YYYY-MM-DD)"),
        include_photos: bool = Query(True, description="Inclure les liens vers les photos"),
        user_id: Optional[str] = Query(None, description="Filtrer par ID utilisateur"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session)
):
    """
    Exporte les relevés de compteurs en fichier Excel.

    Paramètres:
    - **start_date**: Date de début de la période (format: YYYY-MM-DD)
    - **end_date**: Date de fin de la période (format: YYYY-MM-DD)
    - **include_photos**: Inclure ou non les liens vers les photos (défaut: true)
    - **user_id**: ID de l'utilisateur pour filtrer les relevés (optionnel)

    Retourne un fichier Excel avec:
    - Feuille principale avec tous les relevés et leurs détails
    - Liens cliquables vers les photos
    - Feuille de résumé avec statistiques
    """
    try:
        # Validation des dates
        if start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="La date de début doit être antérieure à la date de fin"
            )

        # Vérification des permissions si un user_id est spécifié
        if user_id and current_user.role not in ["admin", "supervisor"]:
            # Un utilisateur normal ne peut exporter que ses propres données
            if user_id != str(current_user.id):
                raise HTTPException(
                    status_code=403,
                    detail="Vous n'avez pas les permissions pour exporter les données d'autres utilisateurs"
                )

        # Génération du fichier Excel
        export_service = ExportService(db)
        excel_buffer = await export_service.export_readings(
            start_date=start_date,
            end_date=end_date,
            include_photos=include_photos,
            user_id=user_id
        )

        # Nom du fichier avec dates
        filename = f"readings_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"

        # Retour du fichier Excel en streaming
        return StreamingResponse(
            io.BytesIO(excel_buffer.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export Excel: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du fichier Excel: {str(e)}"
        )

@router.get("/readings/stats")
async def get_export_stats(
        start_date: date = Query(..., description="Date de début"),
        end_date: date = Query(..., description="Date de fin"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_session)
):
    """
    Obtient les statistiques pour la période donnée avant l'export.
    Utile pour prévisualiser ce qui sera exporté.
    """
    from sqlalchemy import select, func, and_
    from app.models.reading import Reading
    from app.models.meter import Meter

    try:
        # Construction de la requête de base
        query = (
            select(
                func.count(Reading.id).label("total_readings"),
                func.count(func.distinct(Reading.meter_id)).label("unique_meters"),
                func.count(func.distinct(Reading.user_id)).label("unique_users")
            )
            .join(Meter, Reading.meter_id == Meter.id)
            .where(
                and_(
                    Reading.reading_date >= datetime.combine(start_date, datetime.min.time()),
                    Reading.reading_date <= datetime.combine(end_date, datetime.max.time())
                )
            )
        )

        # Filtrer par utilisateur si ce n'est pas un admin
        if current_user.role not in ["admin", "supervisor"]:
            query = query.where(Reading.user_id == current_user.id)

        result = await db.execute(query)
        stats = result.one()

        # Statistiques par type de compteur
        type_stats_query = (
            select(
                Meter.type,
                func.count(Reading.id).label("count")
            )
            .join(Reading, Meter.id == Reading.meter_id)
            .where(
                and_(
                    Reading.reading_date >= datetime.combine(start_date, datetime.min.time()),
                    Reading.reading_date <= datetime.combine(end_date, datetime.max.time())
                )
            )
            .group_by(Meter.type)
        )

        if current_user.role not in ["admin", "supervisor"]:
            type_stats_query = type_stats_query.where(Reading.user_id == current_user.id)

        type_result = await db.execute(type_stats_query)
        readings_by_type = {row.type: row.count for row in type_result}

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "statistics": {
                "total_readings": stats.total_readings,
                "unique_meters": stats.unique_meters,
                "unique_users": stats.unique_users,
                "readings_by_type": readings_by_type
            },
            "user_filter": current_user.role not in ["admin", "supervisor"],
            "estimated_file_size_kb": (stats.total_readings * 2) + 100  # Estimation approximative
        }

    except Exception as e:
        logger.error(f"Erreur lors du calcul des statistiques: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du calcul des statistiques: {str(e)}"
        )


@router.get("/readings/excel/all")
async def export_readings_all(
    include_photos: bool = Query(True, description="Inclure les liens vers les photos"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Exporte tous les relevés de compteurs en fichier Excel, sans filtrer par date.

    Paramètres:
    - **include_photos**: Inclure ou non les liens vers les photos (défaut: true)

    Retourne un fichier Excel avec:
    - Feuille principale avec tous les relevés
    - Liens cliquables vers les photos (si include_photos est true)
    - Feuille de résumé avec statistiques
    """
    try:
        # Filtrer par utilisateur si ce n'est pas un admin ou superviseur
        user_id = None
        if current_user.role not in [UserRole.ADMIN]:
            user_id = str(current_user.id)

        # Génération du fichier Excel
        export_service = ExportService(db)
        excel_buffer = await export_service.export_readings_all(
            include_photos=include_photos,
            user_id=user_id
        )

        # Nom du fichier avec la date actuelle
        today = date.today()
        filename = f"readings_export_all_{today.strftime('%Y%m%d')}.xlsx"

        # Retour du fichier Excel en streaming
        return StreamingResponse(
            io.BytesIO(excel_buffer.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Cache-Control": "no-cache",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )

    except Exception as e:
        logger.error(f"Erreur lors de l'export Excel: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du fichier Excel: {str(e)}"
        )


@router.get("/check-update", response_model=UpdateInfo)
async def check_update():
    try:
        # List the most recent APK in the apks/ prefix
        response = storage_service.s3_client.list_objects_v2(
            Bucket=storage_service.bucket_name,
            Prefix='apks/',
            MaxKeys=1
        )

        if 'Contents' not in response or not response['Contents']:
            logger.error("Aucun APK trouvé dans le bucket")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun APK trouvé dans le bucket"
            )

        # Get the latest APK key (most recent by default sorting)
        latest_key = response['Contents'][0]['Key']

        # Fetch metadata to get version
        metadata_response = storage_service.s3_client.head_object(
            Bucket=storage_service.bucket_name,
            Key=latest_key
        )
        metadata = metadata_response.get('Metadata', {})
        version = metadata.get('version', '1.0.0')  # Fallback version if not set
        changelog = metadata.get('changelog', 'Latest update')  # Optional changelog metadata

        # Construct public URL
        public_url = f"{S3Config.ENDPOINT_URL}/{storage_service.bucket_name}/{latest_key}"

        return UpdateInfo(
            version=version,
            apk_url=public_url,
            changelog=changelog
        )

    except ClientError as e:
        logger.error(f"Erreur lors de la récupération des métadonnées APK: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des métadonnées: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la vérification de mise à jour: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur inattendue: {str(e)}"
        )

