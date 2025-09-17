import mimetypes
import os
from typing import Dict, Any, Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

from fastapi import HTTPException, status, UploadFile

import uuid
import logging

from app.core.s3_config import S3Config
from app.schemas.photo import PresignedUrlRequest, ConfirmUploadRequest

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

class StorageService:
    """Service pour gérer les opérations S3"""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=S3Config.ENDPOINT_URL,
            aws_access_key_id=S3Config.ACCESS_KEY_ID,
            aws_secret_access_key=S3Config.SECRET_ACCESS_KEY,
            region_name=S3Config.REGION,
            config=BotoConfig(
                signature_version="s3v4",
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                s3={
                    "addressing_style": "path",
                    "payload_signing_enabled": True,
                },
            ),
        )
        self.bucket_name = S3Config.BUCKET_NAME
        self._ensure_bucket_exists()
        # self._configure_cors()

    def _ensure_bucket_exists(self):
        """Créer le bucket s'il n'existe pas"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} existe déjà")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    create_params = {'Bucket': self.bucket_name}
                    if S3Config.REGION:
                        create_params['CreateBucketConfiguration'] = {'LocationConstraint': S3Config.REGION}
                    self.s3_client.create_bucket(**create_params)
                    policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": ["s3:GetObject", "s3:PutObject"],
                                "Resource": f"arn:aws:s3:::{self.bucket_name}/*"
                            }
                        ]
                    }
                    self.s3_client.put_bucket_policy(Bucket=self.bucket_name, Policy=str(policy))
                    logger.info(f"Bucket {self.bucket_name} créé avec succès et policy publique appliquée")
                except ClientError as create_error:
                    logger.error(f"Erreur lors de la création du bucket: {create_error}")
                    raise
            else:
                logger.error(f"Erreur lors de la vérification du bucket: {e}")
                raise

    def upload_image(self, file: UploadFile) -> dict:
        """Upload une image vers S3 (legacy)"""
        try:
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension not in S3Config.ALLOWED_EXTENSIONS:
                raise ValueError(f"Extension de fichier non autorisée: {file_extension}")

            unique_filename = f"{uuid.uuid4()}{file_extension}"
            key = f"images/{datetime.now().strftime('%Y/%m/%d')}/{unique_filename}"

            file_content = file.file.read()
            file_size = len(file_content)

            if file_size > S3Config.MAX_FILE_SIZE:
                raise ValueError(f"Fichier trop volumineux: {file_size} octets (max: {S3Config.MAX_FILE_SIZE})")

            content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'image/jpeg'

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original-filename': file.filename,
                    'upload-timestamp': datetime.now().isoformat()
                }
            )

            url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{key}"
            # cdn_url = f"{S3Config.CDN_URL}/{key}" if S3Config.CDN_URL else url

            return {
                "id": unique_filename.split('.')[0],
                "filename": file.filename,
                "url": url,
                "size": file_size,
                "content_type": content_type,
                "uploaded_at": datetime.now()
            }

        except ClientError as e:
            logger.error(f"Erreur S3: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de l'upload vers S3: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur inattendue: {str(e)}")

    def generate_presigned_url_put(self, request: PresignedUrlRequest) -> dict:
        """
        Générer une URL pré-signée pour upload avec PUT
        Idéal pour les applications mobiles et upload simple
        """
        try:
            # Générer un nom unique pour le fichier
            file_extension = os.path.splitext(request.filename)[1].lower()
            file_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime('%Y/%m/%d')
            file_key = f"readings/{timestamp}/{file_id}{file_extension}"

            # Métadonnées à ajouter au fichier
            metadata = {
                'original-filename': request.filename,
                'upload-timestamp': datetime.now().isoformat(),
                'file-id': file_id
            }
            if request.metadata:
                metadata.update(request.metadata)

            # Générer l'URL pré-signée
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': file_key,
                    'ContentType': request.content_type,
                    'Metadata': metadata  # Les métadonnées sont incluses ici pour la signature
                },
                ExpiresIn=S3Config.PRESIGNED_URL_EXPIRATION
            )

            # URL publique finale (similaire à celle de /api/upload)
            public_url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{file_key}"

            # Retourner les headers incluant les x-amz-meta-* pour que le client les envoie
            upload_headers = {
                "Content-Type": request.content_type,
                **{f"x-amz-meta-{k}": v for k, v in metadata.items()}  # Ajout des métadonnées comme en-têtes
            }

            return {
                "upload_url": presigned_url,
                "upload_method": "PUT",
                "upload_headers": upload_headers,  # Headers complets pour le client
                "file_key": file_key,
                "file_id": file_id,
                "expires_at": datetime.now() + timedelta(seconds=S3Config.PRESIGNED_URL_EXPIRATION),
                "public_url": public_url
            }

        except ClientError as e:
            logger.error(f"Erreur génération URL pré-signée: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de la génération de l'URL: {str(e)}"
            )

    def verify_upload(self, file_key: str) -> Optional[dict]:
        """Vérifier qu'un fichier a bien été uploadé"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return {
                "size": response['ContentLength'],
                "content_type": response['ContentType'],
                "etag": response.get('ETag', '').strip('"'),
                "last_modified": response['LastModified'],
                "metadata": response.get('Metadata', {}),
                "version_id": response.get('VersionId')
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            logger.error(f"Erreur vérification upload: {e}")
            raise

    def confirm_upload(self, request: ConfirmUploadRequest) -> dict:
        """Confirmer qu'un upload a réussi et enregistrer les métadonnées"""
        file_info = self.verify_upload(request.file_key)
        if not file_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé sur S3")

        public_url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{request.file_key}"


        return {
            "id": request.file_id or file_info['metadata'].get('file-id', 'unknown'),
            "filename": file_info['metadata'].get('original-filename', 'unknown'),
            "url": public_url,
            "size": file_info['size'],
            "content_type": file_info['content_type'],
            "uploaded_at": file_info['last_modified'],
            "metadata": file_info['metadata'],
            "etag": file_info['etag']
        }

    def list_images(self, limit: int = 100, continuation_token: Optional[str] = None) -> dict:
        """Lister les images avec pagination"""
        try:
            params = {
                'Bucket': self.bucket_name,
                'Prefix': 'images/',
                'MaxKeys': limit
            }
            if continuation_token:
                params['ContinuationToken'] = continuation_token

            response = self.s3_client.list_objects_v2(**params)

            images = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    metadata_response = self.s3_client.head_object(Bucket=self.bucket_name, Key=obj['Key'])
                    public_url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{obj['Key']}"
                    # cdn_url = f"{S3Config.CDN_URL}/{obj['Key']}" if S3Config.CDN_URL else public_url

                    images.append({
                        "id": metadata_response.get('Metadata', {}).get('file-id', os.path.basename(obj['Key']).split('.')[0]),
                        "filename": metadata_response.get('Metadata', {}).get('original-filename', 'unknown'),
                        "url": public_url,
                        "size": obj['Size'],
                        "content_type": metadata_response.get('ContentType', 'image/jpeg'),
                        "uploaded_at": obj['LastModified'],
                        "metadata": metadata_response.get('Metadata', {}),
                        "etag": obj.get('ETag', '').strip('"')
                    })

            return {
                "images": images,
                "total": len(images),
                "next_token": response.get('NextContinuationToken')
            }

        except ClientError as e:
            logger.error(f"Erreur lors de la récupération des images: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de la récupération des images: {str(e)}")

    def upload_apk(self, file: UploadFile, version: Optional[str] = None) -> dict:
        """Upload un fichier APK vers S3"""
        try:
            file_extension = os.path.splitext(file.filename)[1].lower()
            if file_extension != '.apk':
                raise ValueError("Seuls les fichiers APK sont autorisés")

            unique_filename = f"{uuid.uuid4()}{file_extension}"
            timestamp = datetime.now().strftime('%Y/%m/%d')
            key = f"apks/{timestamp}/{unique_filename}"

            file_content = file.file.read()
            file_size = len(file_content)

            if file_size > S3Config.MAX_FILE_SIZE:
                raise ValueError(f"Fichier trop volumineux: {file_size} octets (max: {S3Config.MAX_FILE_SIZE})")

            content_type = 'application/vnd.android.package-archive'

            metadata = {
                'original-filename': file.filename,
                'upload-timestamp': datetime.now().isoformat(),
                'file-id': unique_filename.split('.')[0]
            }
            if version:
                metadata['version'] = version

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=content_type,
                Metadata=metadata,
            )

            public_url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{key}"

            return {
                "id": unique_filename.split('.')[0],
                "filename": file.filename,
                "url": public_url,
                "size": file_size,
                "content_type": content_type,
                "uploaded_at": datetime.now(),
                "metadata": metadata
            }

        except ClientError as e:
            logger.error(f"Erreur S3 lors de l'upload de l'APK: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de l'upload vers S3: {str(e)}")
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'upload de l'APK: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur inattendue: {str(e)}")

    def delete_image(self, file_key: str) -> bool:
        """Supprimer une image"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False

    def generate_presigned_download_url(self, file_key: str, expires_in: int = 3600) -> str:
        """Générer une URL pré-signée pour télécharger un fichier privé"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Erreur génération URL téléchargement: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def get_latest_apk(self) -> Optional[dict]:
        """Récupérer la dernière APK uploadée (par date)"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix="apks/",
                MaxKeys=1000
            )

            if "Contents" not in response or not response["Contents"]:
                return None

            # Trier par LastModified pour avoir le plus récent
            latest_obj = max(response["Contents"], key=lambda x: x["LastModified"])
            key = latest_obj["Key"]

            # Récupérer les métadonnées
            head = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)

            public_url = f"{S3Config.ENDPOINT_URL}/{self.bucket_name}/{key}"

            return {
                "filename": head["Metadata"].get("original-filename", key.split("/")[-1]),
                "version": head["Metadata"].get("version", "unknown"),
                "url": public_url,
                "size": latest_obj["Size"],
                "uploaded_at": latest_obj["LastModified"],
                "etag": latest_obj.get("ETag", "").strip('"')
            }

        except ClientError as e:
            logger.error(f"Erreur récupération APK: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors de la récupération de l'APK")


# Initialiser le service S3
storage_service = StorageService()