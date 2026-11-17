from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.2
    ) -> str:
        """Generates a text completion."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Generates structured JSON output."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text chunks."""
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single text chunk."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass
