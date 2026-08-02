from models.base_client import BaseLLMClient, ExpenseSchema
from models.gemini_client import GeminiLLMClient
from models.openai_client import OpenAILLMClient
from models.claude_client import ClaudeLLMClient
from models.groq_client import GroqLLMClient


def get_llm_client(model_name: str) -> BaseLLMClient:
    """
    Factory function to return the correct LLM client.
    """

    model_name_lower = model_name.lower()

    if "gemini" in model_name_lower:
        return GeminiLLMClient(model_name)

    elif "gpt" in model_name_lower or "openai" in model_name_lower:
        return OpenAILLMClient(model_name)

    elif "claude" in model_name_lower or "anthropic" in model_name_lower:
        return ClaudeLLMClient(model_name)

    elif "llama" in model_name_lower or "groq" in model_name_lower:
        return GroqLLMClient(model_name)

    else:
        raise ValueError(f"Unknown model name: {model_name}")