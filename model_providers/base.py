from abc import ABC
from typing import Optional

from config_models import BaseModelProviderConfig

class BaseModelProvider(ABC):
    def __init__(self, config: BaseModelProviderConfig):
        self.config = config

    def _resolve_api_key(self) -> Optional[str]:
        """Shared utility: resolves the API key based on api_key_source."""
        settings = self.config.provider_config
        if settings.api_key_source == "explicit":
            if not settings.api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key provided.")
            return settings.api_key
        return None
