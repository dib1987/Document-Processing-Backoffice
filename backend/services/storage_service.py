"""
S3 storage service.
- Files stored at: s3://{bucket}/{org_id}/{job_id}/{filename}
- Tenant isolation enforced by key prefix
- Presigned URLs generated for frontend PDF preview (no server proxy needed)
"""
import io

import boto3
from botocore.exceptions import ClientError

from config import get_settings

settings = get_settings()

_s3_client = None


def _get_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
    return _s3_client


def build_s3_key(org_id: str, job_id: str, filename: str) -> str:
    return f"uploads/{org_id}/{job_id}/{filename}"


def upload_file(file_bytes: bytes, s3_key: str, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes to S3."""
    _get_client().put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )


def download_file(s3_key: str) -> bytes:
    """Download file bytes from S3."""
    buffer = io.BytesIO()
    _get_client().download_fileobj(settings.s3_bucket_name, s3_key, buffer)
    buffer.seek(0)
    return buffer.read()


def get_presigned_url(s3_key: str, expiry_seconds: int | None = None) -> str:
    """Generate a presigned GET URL for the frontend PDF viewer."""
    expiry = expiry_seconds or settings.s3_presigned_url_expiry
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
        ExpiresIn=expiry,
    )


def delete_file(s3_key: str) -> None:
    """Delete a file from S3 (used for lifecycle cleanup)."""
    try:
        _get_client().delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
    except ClientError:
        pass  # Best-effort deletion
