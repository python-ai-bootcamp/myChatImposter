from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseLlmProvider(ABC):
    """
    Abstract base class for all LLM providers.
    It defines the interface that all LLM providers must implement.
    """
    def __init__(self, config: Dict, user_id: str):
        self.config = config
        self.user_id = user_id
        super().__init__()

    @abstractmethod
    def get_llm(self) -> Any:
        """
        Returns an instance of the LLM client (e.g., from LangChain).
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system prompt for the LLM.
        """
        pass
