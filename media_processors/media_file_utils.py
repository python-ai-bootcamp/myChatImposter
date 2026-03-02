import os

# Single source of truth for the shared media staging volume path.
# This is the Docker volume mount point used by both the backend and the
# WhatsApp Baileys server. If the mount path ever changes, update only here.
MEDIA_STAGING_DIR = os.path.join("media_store", "pending_media")


def resolve_media_path(guid: str) -> str:
    """Return the absolute-style file path for a given media GUID on the staging volume."""
    return os.path.join(MEDIA_STAGING_DIR, guid)


def delete_media_file(guid: str) -> None:
    """Silently delete a media staging file by GUID.
    Used by both the worker (BaseMediaProcessor) and the janitorial sweep
    (MediaProcessingService) — any caller that knows only the GUID."""
    if not guid:
        return
    try:
        os.remove(resolve_media_path(guid))
    except Exception:
        pass
