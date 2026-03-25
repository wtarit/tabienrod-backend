import asyncio
import logging

from app.config import Settings

logger = logging.getLogger(__name__)


async def upload_pdf_to_s3(
    settings: Settings,
    pdf_bytes: bytes,
    s3_key: str,
) -> bool:
    """Upload PDF bytes to S3. Returns True on success, False on failure.
    Skips silently if S3 is not configured."""
    if not settings.s3_bucket_name:
        return False

    def _upload():
        import boto3

        kwargs = {}
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        if settings.aws_region:
            kwargs["region_name"] = settings.aws_region
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        client = boto3.client("s3", **kwargs)
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

    try:
        await asyncio.to_thread(_upload)
        logger.info(f"Uploaded PDF to s3://{settings.s3_bucket_name}/{s3_key}")
        return True
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        return False
