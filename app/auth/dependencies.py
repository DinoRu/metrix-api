from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import auth_service
from app.database import get_session
from app.models.user import User, UserRole

security = HTTPBearer()

async def get_current_user(
		credentials: HTTPAuthorizationCredentials = Depends(security),
		session: AsyncSession = Depends(get_session)
) -> User:
	"""Get current authenticated user"""
	token = credentials.credentials
	payload = auth_service.decode_token(token)

	if not payload:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid authentication credentials",
			headers={"WWW-Authenticate": "Bearer"}
		)
	user_id = payload.get("sub")
	if not user_id:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid token payload"
		)

	async with session as db:
		result = await db.execute(select(User).where(User.id == user_id))
		user = result.scalar_one_or_none()

	if not user:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="User not found"
		)

	if not user.is_active:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Inactive user"
		)
	return user

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
	"""Require admin role"""
	if current_user.role != UserRole.ADMIN:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Admin access required"
		)
	return current_user

def require_role(roles: list[UserRole]):
	"""Role-based access control decorator"""
	async def role_checker(current_user: User = Depends(get_current_user)) -> User:
		if current_user.role not in roles:
			raise HTTPException(
				status_code=status.HTTP_403_FORBIDDEN,
				detail=f"Insufficient permissions. Required roles: {roles}"
			)
		return current_user
	return role_checker



