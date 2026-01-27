"""
Locale Loader Module.

Provides a centralized way to load and cache locale strings from JSON files.
Supports automatic fallback to English when a requested locale is not available.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

# Base directory for locales (relative to this file's location)
LOCALES_BASE_DIR = Path(__file__).parent / "locales"
DEFAULT_LANGUAGE = "en"


class LocaleLoader:
    """
    Loads and caches locale strings from JSON files.
    
    Supports:
    - Multiple domains (e.g., 'actionable_item', 'error_messages')
    - Automatic fallback to English if requested language is unavailable
    - Caching to avoid repeated file I/O
    """
    
    _cache: Dict[str, Dict[str, dict]] = {}  # {domain: {language_code: strings}}
    
    @classmethod
    def get(cls, domain: str, language_code: str) -> dict:
        """
        Get locale strings for the specified domain and language.
        
        Args:
            domain: The locale domain (e.g., 'actionable_item')
            language_code: ISO 639-1 language code (e.g., 'en', 'he', 'ru')
            
        Returns:
            Dictionary of locale strings
            
        Falls back to English if the requested language is not available.
        Raises FileNotFoundError if even English locale is missing.
        """
        # Check cache first
        if domain in cls._cache and language_code in cls._cache[domain]:
            return cls._cache[domain][language_code]
        
        # Initialize domain cache if needed
        if domain not in cls._cache:
            cls._cache[domain] = {}
        
        # Try to load requested language
        locale_path = LOCALES_BASE_DIR / domain / f"{language_code}.json"
        
        if locale_path.exists():
            strings = cls._load_json(locale_path)
            cls._cache[domain][language_code] = strings
            return strings
        
        # Fallback to English
        logging.info(f"LOCALE: Language '{language_code}' not found for domain '{domain}'. Falling back to English.")
        
        if language_code == DEFAULT_LANGUAGE:
            # English was requested but not found - critical error
            raise FileNotFoundError(
                f"Default locale file not found: {locale_path}. "
                f"Please ensure '{DEFAULT_LANGUAGE}.json' exists in 'locales/{domain}/'."
            )
        
        # Load and cache English fallback
        return cls.get(domain, DEFAULT_LANGUAGE)
    
    @classmethod
    def _load_json(cls, path: Path) -> dict:
        """Load and parse a JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached locales. Useful for testing or hot-reloading."""
        cls._cache.clear()
    
    @classmethod
    def get_available_languages(cls, domain: str) -> list:
        """
        Get list of available language codes for a domain.
        
        Args:
            domain: The locale domain (e.g., 'actionable_item')
            
        Returns:
            List of available language codes (e.g., ['en', 'he'])
        """
        domain_path = LOCALES_BASE_DIR / domain
        if not domain_path.exists():
            return []
        
        return [
            f.stem for f in domain_path.glob("*.json")
        ]
