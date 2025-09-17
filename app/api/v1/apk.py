from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.s3_config import S3Config
from app.services.storage_service import storage_service

router = APIRouter()
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url=S3Config.ENDPOINT_URL,
    aws_access_key_id=S3Config.ACCESS_KEY_ID,
    aws_secret_access_key=S3Config.SECRET_ACCESS_KEY
)

BUCKET_NAME = S3Config.BUCKET_NAME


class AppVersionResponse(BaseModel):
    version: str
    url: str


@router.get("/app/version", response_model=AppVersionResponse)
async def get_app_version():
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="apk/")
    files = sorted(response.get("Contents", []), key=lambda x: x["LastModified"], reverse=True)

    if not files:
        return {"version": "0.0.0", "url": ""}

    latest = files[0]["Key"]  # ex: apk/mon_app_v1.2.0.apk
    version = latest.split("_v")[-1].replace(".apk", "")  # extrait "1.2.0"
    url = f"https://s3.beget.com/{BUCKET_NAME}/{latest}"

    return {"version": version, "url": url}
