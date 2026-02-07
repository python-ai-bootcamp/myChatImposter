"""
Resource Service.
Provides static data like countries, languages, etc.
"""
import pycountry
from typing import List, Dict

class ResourceService:
    @staticmethod
    def get_countries() -> List[Dict[str, str]]:
        """
        Returns a list of countries with name and code.
        Sorted by name.
        """
        countries = []
        for country in pycountry.countries:
            countries.append({
                "name": country.name,
                "code": country.alpha_2,
                "flag": country.flag if hasattr(country, "flag") else "" 
            })
        
        # Sort by name
        return sorted(countries, key=lambda x: x["name"])

    @staticmethod
    def get_languages() -> List[Dict[str, str]]:
        """
        Returns a list of languages.
        """
        from resources import get_all_languages
        return get_all_languages()
