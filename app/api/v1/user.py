import logging
import uuid
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update, select, delete
from sqlalchemy.ext.asyncio import AsyncSession


from app.auth.dependencies import get_current_user, require_role
from app.auth.jwt import auth_service
from app.database import get_session
from app.models.user import User, UserRole
from app.schemas.auth import UserResponse, ChangePasswordRequest, UpdateProfileRequest, UserProfileResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/users", response_model=List[UserProfileResponse], status_code=status.HTTP_200_OK)
async def get_users(
        session = Depends(get_session),
        # current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return users


@router.post("/change-password", response_model=UserResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Modifie le mot de passe de l'utilisateur sans vérification OTP ou email.

    Paramètres:
    - **current_password**: Mot de passe actuel
    - **new_password**: Nouveau mot de passe

    Retourne:
    - Les informations de l'utilisateur mis à jour
    """
    try:
        # Vérifier le mot de passe actuel
        if not auth_service.verify(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )

        # Hacher le nouveau mot de passe
        hashed_password = auth_service.hash_password(request.new_password)

        # Mettre à jour le mot de passe dans la base de données
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(hashed_password=hashed_password)
        )
        await db.commit()

        # Rafraîchir l'utilisateur pour retourner les données à jour
        await db.refresh(current_user)
        return UserResponse.from_orm(current_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du changement de mot de passe: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du changement de mot de passe"
        )

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Récupère le profil de l'utilisateur actuel.

    Retourne:
    - Les informations de l'utilisateur (id, username, full_name, role, is_active)
    """
    try:
        return UserResponse.from_orm(current_user)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du profil: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du profil"
        )

@router.put("/update/{user_id}", response_model=UserProfileResponse)
async def update_profile(
    user_id: UUID,
    user_data: UpdateProfileRequest,
    current_user=Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_session),
):
    """
    Met à jour le profil d'un utilisateur (par ID).
    Seuls les admins peuvent modifier les profils.

    Paramètres possibles :
    - **username**: Nouveau nom d'utilisateur
    - **full_name**: Nouveau nom complet
    - **role**: Nouveau rôle (facultatif)

    Retourne :
    - Les informations de l'utilisateur mis à jour
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    try:
        update_data = user_data.model_dump(exclude_unset=True)

        # Sécurité : éviter la mise à jour de champs sensibles
        protected_fields = {"id", "created_at", "updated_at", "password"}
        for field in protected_fields:
            update_data.pop(field, None)

        for k, v in update_data.items():
            setattr(user, k, v)

        user.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)

        return UserProfileResponse.model_validate(user)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Erreur lors de la mise à jour du profil {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la mise à jour du profil"
        )


@router.delete("/profile/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    user_id: UUID,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_session),
):
    """
    Supprime définitivement le compte d'un utilisateur spécifié par son ID (réservé aux admins).

    Retourne :
    - **204 No Content** si la suppression est réussie.
    """
    try:
        # Vérifier si l'utilisateur existe
        result = await db.execute(select(User).where(User.id == user_id))
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Utilisateur avec l'ID {user_id} non trouvé",
            )

        # Empêcher l'admin de se supprimer lui-même
        if target_user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un administrateur ne peut pas supprimer son propre compte",
            )

        # Supprimer le compte définitivement
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

        logger.info(f"Utilisateur supprimé définitivement (ID: {user_id})")

        # Pas de retour → 204 No Content
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du compte (ID: {user_id}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la suppression du compte",
        )