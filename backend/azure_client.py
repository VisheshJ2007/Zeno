import os
import logging
from openai import AzureOpenAI

logger = logging.getLogger("zeno")

client = None

def init_azure_client():
    """Initialize Azure OpenAI client using .env settings."""
    global client
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")

    if not endpoint or not key:
        logger.warning("⚠  Azure OpenAI credentials not found in .env")
        return None

    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=api_version
        )
        logger.info("✅ Azure OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.exception("❌ Failed to initialize Azure OpenAI client: %s", e)
        return None


def get_client():
    """Return the initialized Azure client."""
    return client