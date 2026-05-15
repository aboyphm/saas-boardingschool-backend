from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class StorageService:
    """
    Abstraction over object storage (AWS S3 or Cloudflare R2).

    Cloudflare R2 is S3-compatible, so both providers share the same boto3
    client. The ``endpoint_url`` is set only when R2 is configured.
    """

    def __init__(self) -> None:
        try:
            import boto3

            endpoint_url = settings.CLOUDFLARE_R2_ENDPOINT or None
            self._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=endpoint_url,
            )
            self._bucket = settings.AWS_S3_BUCKET
            self._available = True
        except (ImportError, Exception) as exc:
            logger.warning("Storage service unavailable: %s", exc)
            self._client = None
            self._available = False

    def _check_available(self) -> None:
        if not self._available:
            raise RuntimeError("Storage service is not configured.")

    def upload_file(
        self,
        file_bytes: bytes,
        object_key: str,
        content_type: str | None = None,
    ) -> str:
        """
        Upload raw bytes to the configured bucket.

        :param file_bytes: File content as bytes.
        :param object_key: Destination path within the bucket (e.g., ``tenants/abc/logo.png``).
        :param content_type: MIME type. Inferred from extension if omitted.
        :returns: Public URL of the uploaded object.
        """
        self._check_available()

        if content_type is None:
            guessed, _ = mimetypes.guess_type(object_key)
            content_type = guessed or "application/octet-stream"

        self._client.put_object(
            Bucket=self._bucket,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type,
        )

        if settings.CLOUDFLARE_R2_ENDPOINT:
            return f"{settings.CLOUDFLARE_R2_ENDPOINT}/{self._bucket}/{object_key}"
        return f"https://{self._bucket}.s3.amazonaws.com/{object_key}"

    def delete_file(self, object_key: str) -> None:
        """Remove an object from the bucket."""
        self._check_available()
        self._client.delete_object(Bucket=self._bucket, Key=object_key)

    def generate_presigned_url(self, object_key: str, expiry_seconds: int = 3600) -> str:
        """Generate a time-limited pre-signed URL for direct browser access."""
        self._check_available()
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=expiry_seconds,
        )

    @staticmethod
    def build_tenant_key(tenant_id: uuid.UUID, filename: str) -> str:
        """Build a deterministic object key scoped to a tenant."""
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4()}{ext}"
        return f"tenants/{tenant_id}/{unique_name}"
