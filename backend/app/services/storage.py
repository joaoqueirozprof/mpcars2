"""Storage service for file uploads (S3/Blob Storage)."""
import os
import uuid
from typing import Optional, BinaryIO
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting local and cloud storage."""

    def __init__(self):
        self.storage_type = os.getenv("STORAGE_TYPE", "local")
        self.bucket_name = os.getenv("STORAGE_BUCKET", "mpcars2-uploads")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.cloudfront_url = os.getenv("CLOUDFRONT_URL", "")
        self.base_path = "/app/uploads"

        if self.storage_type == "s3":
            self._init_s3()
        elif self.storage_type == "azure":
            self._init_azure()
        else:
            self._init_local()

    def _init_local(self):
        """Initialize local storage."""
        Path(self.base_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local storage at {self.base_path}")

    def _init_s3(self):
        """Initialize S3 storage."""
        try:
            import boto3
            self.s3_client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )
            logger.info(f"Using S3 storage bucket: {self.bucket_name}")
        except ImportError:
            logger.warning("boto3 not installed, falling back to local storage")
            self.storage_type = "local"
            self._init_local()

    def _init_azure(self):
        """Initialize Azure Blob storage."""
        try:
            from azure.storage.blob import BlobServiceClient
            self.blob_client = BlobServiceClient.from_connection_string(
                os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            )
            logger.info(f"Using Azure Blob storage container: {self.bucket_name}")
        except ImportError:
            logger.warning("azure-storage-blob not installed, falling back to local storage")
            self.storage_type = "local"
            self._init_local()

    def _get_file_path(self, folder: str, filename: str) -> str:
        """Generate unique file path."""
        ext = Path(filename).suffix.lower()
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return f"{folder}/{unique_name}"

    def upload_file(
        self,
        file: BinaryIO,
        filename: str,
        folder: str = "uploads",
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file and return the public URL."""
        file_path = self._get_file_path(folder, filename)

        if self.storage_type == "s3":
            return self._upload_s3(file, file_path, content_type)
        elif self.storage_type == "azure":
            return self._upload_azure(file, file_path, content_type)
        else:
            return self._upload_local(file, file_path)

    def _upload_s3(self, file: BinaryIO, file_path: str, content_type: Optional[str]) -> str:
        """Upload to S3."""
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self.s3_client.upload_fileobj(
            file,
            self.bucket_name,
            file_path,
            ExtraArgs=extra_args,
        )

        url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_path}"
        if self.cloudfront_url:
            url = f"{self.cloudfront_url}/{file_path}"

        return url

    def _upload_azure(self, file: BinaryIO, file_path: str, content_type: Optional[str]) -> str:
        """Upload to Azure Blob."""
        container = self.blob_client.get_container_client(self.bucket_name)
        blob = container.get_blob_client(file_path)

        blob.upload_blob(file, overwrite=True, content_settings=content_type)

        return blob.url

    def _upload_local(self, file: BinaryIO, file_path: str) -> str:
        """Upload to local storage."""
        full_path = Path(self.base_path) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file.read())

        return f"/uploads/{file_path}"

    def delete_file(self, file_path: str) -> bool:
        """Delete a file."""
        if self.storage_type == "s3":
            try:
                key = file_path.replace(f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/", "")
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception as e:
                logger.error(f"Error deleting S3 file: {e}")
                return False
        elif self.storage_type == "azure":
            try:
                container = self.blob_client.get_container_client(self.bucket_name)
                container.delete_blob(file_path)
                return True
            except Exception as e:
                logger.error(f"Error deleting Azure file: {e}")
                return False
        else:
            try:
                local_path = file_path.replace("/uploads/", "")
                full_path = Path(self.base_path) / local_path
                full_path.unlink(missing_ok=True)
                return True
            except Exception as e:
                logger.error(f"Error deleting local file: {e}")
                return False

    def get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for private files."""
        if self.storage_type == "s3":
            return self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_path},
                ExpiresIn=expires_in,
            )
        return file_path


storage_service = StorageService()
