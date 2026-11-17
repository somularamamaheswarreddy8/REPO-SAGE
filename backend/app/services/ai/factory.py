from app.core.config import settings
from app.services.ai.base import BaseLLMProvider, BaseEmbeddingProvider
from app.services.ai.mock import MockLLMProvider, MockEmbeddingProvider
from app.services.ai.providers import OpenAILLMProvider, OpenAIEmbeddingProvider, AnthropicLLMProvider


def get_llm_provider() -> BaseLLMProvider:
    provider = settings.DEFAULT_LLM_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicLLMProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.ANTHROPIC_MODEL)
    # Default fallback to mock provider
    return MockLLMProvider()


def get_embedding_provider() -> BaseEmbeddingProvider:
    provider = settings.DEFAULT_EMBEDDING_PROVIDER.lower()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_EMBEDDING_MODEL)
    # Default fallback to deterministic mock embedding
    return MockEmbeddingProvider()
