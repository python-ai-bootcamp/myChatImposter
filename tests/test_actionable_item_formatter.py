"""
Unit tests for LocaleLoader and ActionableItemFormatter locale integration.
"""

import pytest
from pathlib import Path
from locale_loader import LocaleLoader, LOCALES_BASE_DIR
from actionable_item_formatter import ActionableItemFormatter


class TestLocaleLoader:
    """Tests for the LocaleLoader class."""

    def setup_method(self):
        """Clear cache before each test."""
        LocaleLoader.clear_cache()

    def test_load_english_locale(self):
        """Test loading English locale strings."""
        strings = LocaleLoader.get("actionable_item", "en")
        
        assert strings is not None
        assert strings["header_icon"] == "📝"
        assert strings["group"] == "📂 *Group*"
        assert strings["goal"] == "📌 *Description*"

    def test_load_hebrew_locale(self):
        """Test loading Hebrew locale strings."""
        strings = LocaleLoader.get("actionable_item", "he")
        
        assert strings is not None
        assert strings["header_icon"] == "📝"
        assert strings["group"] == "📂 *קבוצה*"
        assert strings["goal"] == "📌 *תיאור*"

    def test_fallback_to_english_for_unsupported_language(self):
        """Test fallback to English when requested language is not available."""
        # Russian is not supported
        strings = LocaleLoader.get("actionable_item", "ru")
        
        # Should return English strings
        assert strings is not None
        assert strings["group"] == "📂 *Group*"
        assert strings["goal"] == "📌 *Description*"

    def test_fallback_to_english_for_nonexistent_language(self):
        """Test fallback to English for a completely made-up language code."""
        strings = LocaleLoader.get("actionable_item", "xyz")
        
        # Should return English strings
        assert strings is not None
        assert strings["group"] == "📂 *Group*"

    def test_caching_works(self):
        """Test that locales are cached after first load."""
        # First load
        strings1 = LocaleLoader.get("actionable_item", "en")
        
        # Second load should return same object (from cache)
        strings2 = LocaleLoader.get("actionable_item", "en")
        
        assert strings1 is strings2

    def test_get_available_languages(self):
        """Test listing available languages for a domain."""
        languages = LocaleLoader.get_available_languages("actionable_item")
        
        assert "en" in languages
        assert "he" in languages

    def test_missing_domain_returns_empty_list(self):
        """Test that a non-existent domain returns an empty language list."""
        languages = LocaleLoader.get_available_languages("nonexistent_domain")
        
        assert languages == []


class TestActionableItemFormatterLocale:
    """Tests for ActionableItemFormatter locale integration."""

    def setup_method(self):
        """Clear locale cache before each test."""
        LocaleLoader.clear_cache()

    def test_format_card_english(self):
        """Test formatting a card in English."""
        item = {
            "task_title": "Complete Report",
            "group_display_name": "Work Team",
            "task_description": "Finish the quarterly report",
            "text_deadline": "by Friday",
            "timestamp_deadline": "2026-01-31 17:00:00"
        }
        
        card = ActionableItemFormatter.format_card(item, "en")
        
        assert "📝 *Complete Report*" in card
        assert "📂 *Group*: Work Team" in card
        assert "📌 *Description*: Finish the quarterly report" in card
        assert "⏰ *Due (from text)*: by Friday" in card

    def test_format_card_hebrew(self):
        """Test formatting a card in Hebrew."""
        item = {
            "task_title": "השלמת דוח",
            "group_display_name": "צוות עבודה",
            "task_description": "סיים את הדוח הרבעוני"
        }
        
        card = ActionableItemFormatter.format_card(item, "he")
        
        assert "📝 *השלמת דוח*" in card
        assert "📂 *קבוצה*: צוות עבודה" in card
        assert "📌 *תיאור*: סיים את הדוח הרבעוני" in card

    def test_format_card_unsupported_language_falls_back_to_english(self):
        """Test that unsupported languages fall back to English formatting."""
        item = {
            "task_title": "Задача",
            "group_display_name": "Команда",
            "task_description": "Описание задачи"
        }
        
        # Request Russian (not supported)
        card = ActionableItemFormatter.format_card(item, "ru")
        
        # Should use English labels
        assert "📂 *Group*: Команда" in card
        assert "📌 *Description*: Описание задачи" in card

    def test_format_card_default_language_is_english(self):
        """Test that default language is English when not specified."""
        item = {
            "task_title": "Test Task",
            "task_description": "Test description"
        }
        
        card = ActionableItemFormatter.format_card(item)
        
        assert "📌 *Description*: Test description" in card
