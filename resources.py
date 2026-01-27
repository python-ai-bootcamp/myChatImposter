"""
Centralized Resources Module.

Contains static resource data used across the application.
This is the single source of truth for language codes, names, etc.
"""

from typing import Optional


# Comprehensive language list with ISO 639-1 codes, English names, and native names
LANGUAGES = [
    {"code": "en", "name": "English", "native_name": "English"},
    {"code": "he", "name": "Hebrew", "native_name": "עברית"},
    {"code": "ar", "name": "Arabic", "native_name": "العربية"},
    {"code": "es", "name": "Spanish", "native_name": "Español"},
    {"code": "fr", "name": "French", "native_name": "Français"},
    {"code": "de", "name": "German", "native_name": "Deutsch"},
    {"code": "ru", "name": "Russian", "native_name": "Русский"},
    {"code": "zh", "name": "Chinese", "native_name": "中文"},
    {"code": "ja", "name": "Japanese", "native_name": "日本語"},
    {"code": "pt", "name": "Portuguese", "native_name": "Português"},
    {"code": "it", "name": "Italian", "native_name": "Italiano"},
    {"code": "ko", "name": "Korean", "native_name": "한국어"},
    {"code": "nl", "name": "Dutch", "native_name": "Nederlands"},
    {"code": "pl", "name": "Polish", "native_name": "Polski"},
    {"code": "tr", "name": "Turkish", "native_name": "Türkçe"},
    {"code": "hi", "name": "Hindi", "native_name": "हिन्दी"},
    {"code": "th", "name": "Thai", "native_name": "ไทย"},
    {"code": "vi", "name": "Vietnamese", "native_name": "Tiếng Việt"},
    {"code": "uk", "name": "Ukrainian", "native_name": "Українська"},
    {"code": "sv", "name": "Swedish", "native_name": "Svenska"},
]

# Build lookup dictionary for O(1) access
_LANGUAGE_BY_CODE = {lang["code"]: lang for lang in LANGUAGES}


def get_language_by_code(code: str) -> Optional[dict]:
    """
    Get the full language object by ISO 639-1 code.
    
    Args:
        code: ISO 639-1 language code (e.g., 'en', 'ru')
        
    Returns:
        Language dict with code, name, native_name, or None if not found.
    """
    return _LANGUAGE_BY_CODE.get(code)


def get_language_name(code: str, fallback: Optional[str] = None) -> str:
    """
    Get the English name of a language by its ISO code.
    
    Args:
        code: ISO 639-1 language code (e.g., 'en', 'ru')
        fallback: Value to return if code not found. Defaults to the code itself.
        
    Returns:
        English language name (e.g., 'Russian') or fallback.
    """
    lang = _LANGUAGE_BY_CODE.get(code)
    if lang:
        return lang["name"]
    return fallback if fallback is not None else code


def get_language_native_name(code: str, fallback: Optional[str] = None) -> str:
    """
    Get the native name of a language by its ISO code.
    
    Args:
        code: ISO 639-1 language code (e.g., 'ru')
        fallback: Value to return if code not found. Defaults to the code itself.
        
    Returns:
        Native language name (e.g., 'Русский') or fallback.
    """
    lang = _LANGUAGE_BY_CODE.get(code)
    if lang:
        return lang["native_name"]
    return fallback if fallback is not None else code


def get_all_languages() -> list:
    """
    Get all supported languages.
    
    Returns:
        List of language dicts, each with code, name, native_name.
    """
    return LANGUAGES.copy()


# Common IANA timezones (Centralized Source of Truth)
TIMEZONES = [
    'UTC',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Europe/Moscow',
    'Asia/Jerusalem',
    'Asia/Dubai',
    'Asia/Kolkata',
    'Asia/Bangkok',
    'Asia/Singapore',
    'Asia/Hong_Kong',
    'Asia/Tokyo',
    'Australia/Sydney',
    'Pacific/Auckland',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'America/Sao_Paulo',
    'Africa/Cairo',
    'Africa/Johannesburg'
]

def get_all_timezones() -> list:
    """
    Get all supported timezones.
    
    Returns:
        List of timezone strings (IANA format).
    """
    return TIMEZONES.copy()
