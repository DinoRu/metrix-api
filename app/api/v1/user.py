import logging

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_current_admin
from app.auth.jwt import auth_service
from app.database import get_session
from app.models.user import User
from app.schemas.auth import UserResponse, UpdateProfileRequest, UserProfileResponse, AdminChangePasswordRequest

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/users", response_model=List[UserProfileResponse], status_code=status.HTTP_200_OK)
async def get_users(
        session: AsyncSession = Depends(get_session),
        _: User = Depends(get_current_admin)
):
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users

@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Retrieves the profile of the current user.

    Returns:
    - User information (id, username, full_name, role, is_active)
    """
    try:
        return UserResponse.from_orm(current_user)
    except Exception as e:
        logger.error(f"Error retrieving profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving profile"
        )

@router.put("/{user_id}/password", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def admin_change_password(
        user_id: UUID,
        body: AdminChangePasswordRequest,
        session: AsyncSession = Depends(get_session),
        _: User = Depends(get_current_admin)
):
    if body.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inconsistent user_id between URL and request")
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        hashed = auth_service.hash_password(body.new_password)
        await session.execute(
            update(User).where(User.id == user_id).values(hashed_password=hashed, updated_at=datetime.utcnow())
        )
        await session.commit()
        await session.refresh(user)
        return UserResponse.from_orm(user)
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password"
        )

@router.put("/update/{user_id}", response_model=UserProfileResponse)
async def update_profile(
    user_id: UUID,
    user_data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_admin)
):
    """
    Updates a user's profile (by ID).
    Only admins can modify profiles.

    Possible parameters:
    - **username**: New username
    - **full_name**: New full name
    - **role**: New role (optional)

    Returns:
    - Updated user information
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        update_data = user_data.model_dump(exclude_unset=True)

        # Security: Prevent updating sensitive fields
        protected_fields = {"id", "created_at", "updated_at", "hashed_password"}
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
        logger.error(f"Error updating profile {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while updating profile"
        )

@router.delete("/profile/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_admin: User = Depends(get_current_admin)
):
    """
    Permanently deletes a user's account specified by their ID (admin only).

    Returns:
    - **204 No Content** if deletion is successful.
    """
    try:
        # Check if the user exists
        result = await db.execute(select(User).where(User.id == user_id))
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )

        # Prevent admin from deleting their own account
        if target_user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An administrator cannot delete their own account"
            )

        # Permanently delete the account
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

        logger.info(f"User permanently deleted (ID: {user_id})")

        # No return → 204 No Content
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account (ID: {user_id}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while deleting account"
        )