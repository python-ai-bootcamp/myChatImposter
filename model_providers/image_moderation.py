from abc import abstractmethod
from pydantic import BaseModel
from typing import Dict

from .base import BaseModelProvider

class ModerationResult(BaseModel):
    """Normalized result from an image moderation API call."""
    flagged: bool
    categories: Dict[str, bool]
    category_scores: Dict[str, float]

class ImageModerationProvider(BaseModelProvider):
    @abstractmethod
    async def moderate_image(self, image_url: str) -> ModerationResult:
        pass
