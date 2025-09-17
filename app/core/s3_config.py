

# Configuration Yandex Cloud Storage (S3-compatible)
import os

from dotenv import load_dotenv

load_dotenv()

class S3Config:
    """Configuration pour Yandex Cloud Storage"""
    ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "https://storage.yandexcloud.net")
    ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "mobile-app-images")
    REGION = os.getenv("REGION", "ru-1")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif"}
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg", "image/jpg", "image/png", "image/gif",
        "image/webp", "image/heic", "image/heif"
    }
    PRESIGNED_URL_EXPIRATION = 3600

