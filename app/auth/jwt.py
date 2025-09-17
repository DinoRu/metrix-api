import logging
from datetime import timedelta, datetime, timezone
from typing import Dict, Any, Optional
from jose import JWTError, jwt

from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
	@staticmethod
	def verify_password(plain_password: str, hashed_password: str) -> bool:
		"""Verify a password against its hash"""
		return pwd_context.verify(plain_password, hashed_password)

	@staticmethod
	def hash_password(password: str) -> str:
		"""Hash a password"""
		return pwd_context.hash(password)

	@staticmethod
	def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
		"""Create JWT access token"""
		to_encode = data.copy()
		expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.JWT_EXPIRATION_HOURS))
		to_encode.update({"exp": expire, "type": "access"})
		return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

	@staticmethod
	def create_refresh_token(data: Dict[str, Any]) -> str:
		"""Create JWT refresh token"""
		to_encode = data.copy()
		expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
		to_encode.update({"exp": expire, "type": "refresh"})
		return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

	@staticmethod
	def decode_token(token: str) -> Optional[Dict[str, Any]]:
		"""Decode and validate JWT token"""
		try:
			payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
			return payload
		except JWTError as e:
			logger.error(f"JWT decode error: {e}")
			return None


auth_service = AuthService()