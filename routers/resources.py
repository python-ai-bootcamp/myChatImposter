"""
Resources Router.

Provides API endpoints for static resources like languages, timezones, etc.
"""

from fastapi import APIRouter
from resources import get_all_languages

router = APIRouter(prefix="/api/internal/resources", tags=["Resources"])


@router.get("/languages")
async def list_languages():
    """
    Get all supported languages.
    
    Returns a list of language objects, each containing:
    - code: ISO 639-1 language code (e.g., 'en', 'ru')
    - name: English language name (e.g., 'Russian')
    - native_name: Native language name (e.g., 'Русский')
    """
    return get_all_languages()

@router.get("/timezones")
async def list_timezones():
    """
    Get all supported timezones.
    
    Returns:
        List of timezone strings (e.g., 'UTC', 'Europe/London').
    """
    from resources import get_all_timezones
    return get_all_timezones()

@router.get("/countries")
async def list_countries():
    """
    Get list of countries (ISO 3166-1 alpha-2).
    
    Returns:
        List of dicts: {name, code, flag}
    """
    from services.resource_service import ResourceService
    return ResourceService.get_countries()
