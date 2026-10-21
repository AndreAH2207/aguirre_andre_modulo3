import os

from agents import AsyncOpenAI, OpenAIChatCompletionsModel, set_tracing_disabled
from openai import OpenAI


def build_model():
    provider = os.getenv("MODEL_PROVIDER", "openai")
    model_name = os.getenv("MODEL_NAME", "gpt-5-mini")
    if provider == "openai":
        return model_name
    if provider == "openai_compatible":
        # Traces are sent to OpenAI by default; without an OpenAI key they only produce errors.
        set_tracing_disabled(True)
        base_url = os.environ["PROVIDER_BASE_URL"]
        api_key = os.environ["PROVIDER_API_KEY"]
        client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        return OpenAIChatCompletionsModel(model=model_name, openai_client=client)
    raise ValueError(f"MODEL_PROVIDER no soportado: {provider}")


def build_embedding_client() -> OpenAI:
    """Client for embeddings (RAG), using the same provider as the agent."""
    if os.getenv("MODEL_PROVIDER", "openai") == "openai_compatible":
        return OpenAI(base_url=os.environ["PROVIDER_BASE_URL"], api_key=os.environ["PROVIDER_API_KEY"])
    return OpenAI()
