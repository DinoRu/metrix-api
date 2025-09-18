from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
	# App
	APP_NAME: str = "Meter Reading API"
	APP_VERSION: str = "1.0.0"
	API_V1_PREFIX: str = "/api/v1"
	API_BASE_URL: str = "http://localhost:8000"
	DEBUG: bool = False
	ENVIRONMENT: str = "development" # development, staging, production

	# Server
	PORT: int = 8000
	WORKERS: int = 4

	# Database
	DATABASE_URL: str
	DB_POOL_SIZE: int = 20
	DB_MAX_OVERFLOW: int = 40
	DB_POOL_PRE_PING: bool = True
	DB_ECHO: bool = False
	AUTO_CREATE_TABLES: bool = False

	# Redis
	REDIS_URL: str
	REDIS_TTL: int = 3600
	REDIS_POOL_SIZE: int = 10

	# JWT
	JWT_SECRET: str
	JWT_ALGORITHM: str = "HS256"
	JWT_EXPIRATION_HOURS: int = 24
	JWT_REFRESH_EXPIRATION_DAYS: int = 7

	# S3 Storage
	S3_ENDPOINT_URL: Optional[str]
	AWS_ACCESS_KEY_ID: str
	AWS_SECRET_ACCESS_KEY: str
	S3_BUCKET_NAME: str
	S3_REGION: str = "ru-central1"
	S3_USE_SSL: bool = True
	PRESIGNED_URL_EXPIRATION: int = 3600
	MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

	# CORS
	CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
	CORS_ALLOW_CREDENTIALS: bool = True
	CORS_ALLOW_METHODS: List[str] = ["*"]
	CORS_ALLOW_HEADERS: List[str] = ["*"]

	# Security
	BCRYPT_ROUNDS: int = 12
	RATE_LIMIT_PER_MINUTE: int = 60
	ALLOWED_HOSTS: List[str] = ["*"]
	REQUIRE_API_KEY: bool = False

	# Monitoring
	EXPOSE_METRICS: bool = True

	# Sync
	SYNC_BATCH_SIZE: int = 100
	OUTBOX_RETRY_LIMIT: int = 5

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=True
	)


@lru_cache()
def get_settings() -> Settings:
	return Settings()


settings = get_settings()