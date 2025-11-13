"""Azure OpenAI proxy router

This router exposes a small POST endpoint that accepts a user message,
forwards it to Azure OpenAI Chat Completions API (deployment specified in
env), and returns the model's text reply. This keeps the API key secret
on the server side.
"""
import os
import base64
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile
from openai import AzureOpenAI, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/azure", tags=["Azure OpenAI"])


@router.post("/chat", status_code=status.HTTP_200_OK)
async def azure_chat(
    message: str = Form(""),
    deployment: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Proxy a user's message to Azure OpenAI and return the reply.

    Requires environment variables in backend/.env or environment:
      AZURE_OPENAI_ENDPOINT (e.g. https://your-resource.openai.azure.com)
      AZURE_OPENAI_API_KEY (or AZURE_OPENAI_KEY)
      AZURE_OPENAI_CHAT_DEPLOYMENT (deployment name for chat models)
    """
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
    except Exception:
        logger.exception("Azure OpenAI client failed to initialize. Check environment variables.")
        raise HTTPException(status_code=500, detail="Azure OpenAI not configured on server")

    # Use the deployment name from the request or fall back to the env variable.
    chat_deployment = deployment or os.getenv("AZURE_CHAT_DEPLOYMENT")
    if not chat_deployment:
        raise HTTPException(status_code=500, detail="Azure chat deployment name not configured on server.")

    # --- Build the message payload ---
    messages = [
        {"role": "system", "content": "You are a helpful study assistant named Zeno. Keep answers concise and friendly."}
    ]
    user_content = []

    # Add the text part of the message
    if message:
        user_content.append({"type": "text", "text": message})

    # Add the image part of the message, if a file was uploaded
    if file:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are supported.")

        # Read file, encode to base64, and format for API
        file_bytes = await file.read()
        base64_image = base64.b64encode(file_bytes).decode('utf-8')
        image_url = f"data:{file.content_type};base64,{base64_image}"
        user_content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })

    if not user_content:
        return {"success": True, "response": "Please provide a message or a file."}

    messages.append({"role": "user", "content": user_content})

    try:
        completion = client.chat.completions.create(
            model=chat_deployment,
            messages=messages,
            max_tokens=512,
            temperature=0.2,
            timeout=30.0,
        )
        response_text = completion.choices[0].message.content
        return {"success": True, "response": response_text or ''}

    except APIConnectionError as e:
        logger.error("Azure OpenAI API connection error: %s", e.__cause__)
        raise HTTPException(status_code=502, detail="Cannot connect to Azure OpenAI service.")
    except RateLimitError as e:
        logger.warning("Azure OpenAI rate limit exceeded: %s", e)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    except Exception as e:
        logger.exception("Failed to call Azure OpenAI: %s", e)
        if "Resource not found" in str(e):
            raise HTTPException(status_code=404, detail=f"Deployment '{chat_deployment}' not found.")
        raise HTTPException(status_code=500, detail="An unexpected error occurred with the AI service.")


@router.get("/health", status_code=status.HTTP_200_OK)
async def azure_health():
    """Return whether Azure OpenAI config appears present on the server.

    This endpoint deliberately does NOT return secret values. It only
    indicates which required variables are missing so you can debug.
    """
    has_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    required = {
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_API_KEY": has_api_key,
        "AZURE_CHAT_DEPLOYMENT": os.getenv("AZURE_CHAT_DEPLOYMENT")
    }
    missing = [k for k, v in required.items() if not v]
    return {"configured": len(missing) == 0, "missing": missing}
