from abc import abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel

from .base import BaseModelProvider

class ChatCompletionProvider(BaseModelProvider):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        pass
