"""
WhitelistPolicy - Handles whitelist matching logic for bot reply feature.

Extracts the nested loop logic from ChatbotInstance._handle_bot_reply
into a clean, testable, reusable policy class.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class WhitelistMatch:
    """Result of a whitelist check."""
    is_allowed: bool
    matched_identifier: Optional[str] = None
    matched_whitelist_entry: Optional[str] = None


class WhitelistPolicy:
    """
    Encapsulates whitelist matching logic.
    
    Checks if any identifier from a list matches any entry in a whitelist.
    Matching is done via substring containment (whitelist_entry in identifier).
    """
    
    @staticmethod
    def check(
        identifiers: List[str],
        whitelist: Optional[List[str]]
    ) -> WhitelistMatch:
        """
        Check if any identifier matches any whitelist entry.
        
        Args:
            identifiers: List of identifiers to check (e.g., sender ID, phone, display name)
            whitelist: List of allowed patterns. If None or empty, returns not allowed.
            
        Returns:
            WhitelistMatch with is_allowed=True and matching details if found,
            otherwise is_allowed=False.
        """
        if not whitelist:
            return WhitelistMatch(is_allowed=False)
        
        for whitelist_entry in whitelist:
            if not whitelist_entry:
                continue
            for identifier in identifiers:
                if identifier and whitelist_entry in identifier:
                    return WhitelistMatch(
                        is_allowed=True,
                        matched_identifier=identifier,
                        matched_whitelist_entry=whitelist_entry
                    )
        
        return WhitelistMatch(is_allowed=False)
