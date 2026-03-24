from abc import ABC, abstractmethod

from .base import LLMProvider


class ImageTranscriptionProvider(LLMProvider, ABC):
    """Abstract provider for image transcription.
    Inherits abstract get_llm() -> BaseChatModel from LLMProvider.
    """
    @abstractmethod
    async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str:
        ...
