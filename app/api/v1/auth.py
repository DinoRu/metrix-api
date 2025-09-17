import logging


from fastapi import APIRouter, status, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import auth_service
from app.database import get_session
from app.models.user import User
from app.schemas.auth import UserResponse, RegisterRequest, LoginResponse, LoginRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/register", response_model=UserResponse,
			 status_code=status.HTTP_201_CREATED)
async def register(
		request: RegisterRequest,
		session: AsyncSession = Depends(get_session)
):
	"""Register a new user."""
	async with session as db:
		# Check if user exits
		result = await db.execute(select(User).where(User.username == request.username))
		if result.scalar_one_or_none():
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Username already registered"
			)

		# Create new user
		user = User(
			username=request.username,
			hashed_password=auth_service.hash_password(request.password),
			full_name=request.full_name,
			role=request.role
		)
		db.add(user)
		await db.commit()
		await db.refresh(user)

		logger.info(f"New user registered: {user.username}")

		return user

@router.post("/login", response_model=LoginResponse)
async def login(
		request: LoginRequest,
		session: AsyncSession = Depends(get_session)
):
	"""Login and get access token."""
	async with session as db:
		result = await db.execute(select(User).where(User.username == request.username))
		user = result.scalar_one_or_none()

		if not user or not auth_service.verify_password(request.password, user.hashed_password):
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Incorrect username or password",
				headers={"WWW-Authenticate": "Bearer"}
			)
		if not user.is_active:
			raise HTTPException(
				status_code=status.HTTP_400_BAD_REQUEST,
				detail="Inactive user"
			)
		# Create tokens
		access_token = auth_service.create_access_token({"sub": str(user.id), "role": user.role})
		refresh_token = auth_service.create_refresh_token({"sub": str(user.id)})

		logger.info(f"User logged in: {user.username}")

		return LoginResponse(
			access_token=access_token,
			refresh_token=refresh_token,
			user=UserResponse.model_validate(user)
		)

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
		refresh_token: str,
		session: AsyncSession = Depends(get_session)
):
	"""Refresh access token"""
	payload = auth_service.decode_token(refresh_token)

	if not payload or payload.get("type") != "refresh":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Invalid refresh token"
		)

	user_id = payload.get("sub")
	async with session as db:
		result = await db.execute(select(User).where(User.id == user_id))
		user = result.scalar_one_or_none()

		if not user or not user.is_active:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="User not found or inactive"
			)
		# Create new tokens
		access_token = auth_service.create_access_token({"sub": str(user.id), "role": user.role})
		new_refresh_token = auth_service.create_refresh_token({"sub": str(user.id)})

		return LoginResponse(
			access_token=access_token,
			refresh_token=new_refresh_token,
			user=UserResponse.model_validate(user)
		)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
	"""Get current user information"""
	return current_user

@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
	"""Logout user (a client should remove tokens)"""
	# In a production app, you might want to blocklist the token in Redis
	response.delete_cookie("access_token")
	return {"message": "Successfully logged out"}


