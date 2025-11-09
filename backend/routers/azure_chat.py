"""Azure OpenAI proxy router

This router exposes a small POST endpoint that accepts a user message,
forwards it to Azure OpenAI Chat Completions API (deployment specified in
env), and returns the model's text reply. This keeps the API key secret
on the server side.
"""
import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/azure", tags=["Azure OpenAI"])


class ChatRequest(BaseModel):
    user: Optional[str] = None
    message: str
    # optional: override deployment name
    deployment: Optional[str] = None


@router.post("/chat", status_code=status.HTTP_200_OK)
async def azure_chat(req: ChatRequest):
    """Proxy the user's message to Azure OpenAI and return the reply.

    Requires environment variables in backend/.env or environment:
      AZURE_OPENAI_ENDPOINT (e.g. https://your-resource.openai.azure.com)
      AZURE_OPENAI_API_KEY
      AZURE_OPENAI_DEPLOYMENT (deployment name to use by default)
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = req.deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not endpoint or not api_key or not deployment:
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured on server")

    # Determine API version (allow override via env)
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

    # Build request to chat completions endpoint
    url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful study assistant named Zeno. Keep answers concise and friendly."},
            {"role": "user", "content": req.message}
        ],
        # keep response short for UI responsiveness
        "max_tokens": 512,
        "temperature": 0.2
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            logger.error("Azure OpenAI error: %s %s", r.status_code, r.text)
            raise HTTPException(status_code=502, detail=f"Azure OpenAI error: {r.status_code}")

        data = r.json()
        # expected shape: choices[0].message.content
        text = None
        try:
            text = data.get('choices', [])[0].get('message', {}).get('content')
        except Exception:
            text = None

        if not text:
            # fallback: try other keys
            text = data.get('choices', [])[0].get('text') if data.get('choices') else None

        return {"success": True, "response": text or ''}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to call Azure OpenAI: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", status_code=status.HTTP_200_OK)
async def azure_health():
    """Return whether Azure OpenAI config appears present on the server.

    This endpoint deliberately does NOT return secret values. It only
    indicates which required variables are missing so you can debug.
    """
    required = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"]
    missing = [k for k in required if not os.getenv(k)]
    return {"configured": len(missing) == 0, "missing": missing}
