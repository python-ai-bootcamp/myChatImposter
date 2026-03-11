from openai import AsyncOpenAI
from .image_moderation import ImageModerationProvider, ModerationResult
from config_models import BaseModelProviderConfig

class OpenAiModerationProvider(ImageModerationProvider):
    def __init__(self, config: BaseModelProviderConfig):
        super().__init__(config)

    async def moderate_image(self, image_url: str) -> ModerationResult:
        api_key = self._resolve_api_key()
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.moderations.create(
            model=self.config.provider_config.model,
            input=[
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        )
        
        result = response.results[0]
        return ModerationResult(
            flagged=result.flagged,
            categories=result.categories.model_dump(),
            category_scores=result.category_scores.model_dump()
        )
