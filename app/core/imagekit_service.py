import asyncio
import base64
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_imagekit_client = None


def get_imagekit() -> ImageKit:
    """Get or create ImageKit client singleton"""
    global _imagekit_client
    if _imagekit_client is None:
        if not settings.IMAGEKIT_PRIVATE_KEY:
            raise RuntimeError("IMAGEKIT_PRIVATE_KEY is not configured")
        _imagekit_client = ImageKit(
            private_key=settings.IMAGEKIT_PRIVATE_KEY,
            public_key=settings.IMAGEKIT_PUBLIC_KEY,
            url_endpoint=settings.IMAGEKIT_URL_ENDPOINT,
        )
    return _imagekit_client


def _sync_upload(ik: ImageKit, b64_file: str, filename: str, user_id: int) -> dict:
    """Synchronous upload wrapper (ImageKit SDK is blocking)"""
    # SDK requires UploadFileRequestOptions object, NOT a plain dict
    options = UploadFileRequestOptions(
        folder=f"/avatars/{user_id}/",
        use_unique_file_name=True,
        tags=[f"user_{user_id}", "avatar"],
    )

    try:
        result = ik.upload_file(
            file=b64_file,
            file_name=filename,
            options=options,
        )
    except Exception as e:
        logger.error(f"❌ [IMAGEKIT] Upload failed for user {user_id}: {e}", exc_info=True)
        raise RuntimeError(f"ImageKit upload failed: {str(e)}")

    # Handle response — SDK returns an object with .response_metadata and data fields
    # The response may be dict-like or object-like depending on version
    if isinstance(result, dict):
        response = result.get("response", result)
        error = result.get("error")
        if error:
            raise RuntimeError(f"ImageKit upload failed: {error}")
        if isinstance(response, dict):
            return {
                "url": response.get("url"),
                "file_id": response.get("fileId"),
            }

    # Object-style response
    url = getattr(result, 'url', None)
    file_id = getattr(result, 'file_id', None) or getattr(result, 'fileId', None)

    if not url:
        # Try nested .response attribute
        inner = getattr(result, 'response', None)
        if inner and isinstance(inner, dict):
            url = inner.get("url")
            file_id = inner.get("fileId")

    if not url:
        logger.warning(f"⚠️ [IMAGEKIT] Unexpected response: {type(result)} — {result}")
        raise RuntimeError("ImageKit upload failed: could not extract URL from response")

    return {
        "url": url,
        "file_id": file_id,
    }


async def upload_avatar(file_bytes: bytes, filename: str, user_id: int, old_file_id: str = None) -> dict:
    """
    Upload avatar to ImageKit CDN.

    Args:
        file_bytes: Raw image bytes
        filename: Original filename (e.g. "photo.jpg")
        user_id: User ID for folder organization
        old_file_id: Previous ImageKit file ID to delete

    Returns:
        dict with: url (full CDN URL), file_id (for future deletion)
    """
    ik = get_imagekit()

    # Delete old avatar if exists
    if old_file_id:
        try:
            await asyncio.to_thread(ik.delete_file, old_file_id)
            logger.info(f"🗑️ [IMAGEKIT] Deleted old avatar: {old_file_id}")
        except Exception as e:
            logger.warning(f"⚠️ [IMAGEKIT] Failed to delete old avatar {old_file_id}: {e}")

    # Upload new avatar (run in thread to avoid blocking event loop)
    b64_file = base64.b64encode(file_bytes).decode("utf-8")
    result = await asyncio.to_thread(_sync_upload, ik, b64_file, filename, user_id)

    logger.info(f"✅ [IMAGEKIT] Uploaded avatar for user {user_id}: {result['url']}")

    return result
