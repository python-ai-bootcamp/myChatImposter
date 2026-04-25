from abc import ABC, abstractmethod
from typing import Callable, Awaitable

from .base import BaseModelProvider


class AudioTranscriptionProvider(BaseModelProvider, ABC):
    """Abstract base class for audio transcription providers.
    
    Unlike LLMProvider, this does NOT inherit from LLMProvider because
    Soniox is a pure transcription API and not a standard ChatCompletion model.
    """

    def __init__(self, config):
        super().__init__(config)
        self._token_tracker = None

    def set_token_tracker(self, tracker_func: Callable[..., Awaitable[None]]):
        """Inject an async token tracking callback.
        
        Args:
            tracker_func: An async callable accepting input_tokens, output_tokens,
                          and cached_input_tokens keyword arguments.
        """
        self._token_tracker = tracker_func

    @abstractmethod
    async def transcribe_audio(self, file_path: str, mime_type: str) -> str:
        """Transcribe an audio file and return the transcript text.
        
        Args:
            file_path: Path to the audio file on disk.
            mime_type: MIME type of the audio file.
            
        Returns:
            The transcribed text string.
        """
        ...

    async def initialize(self):
        """No-op at this level; concrete subclass overrides."""
        pass
