"""
Settings management API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class OllamaSettings(BaseModel):
    """Ollama configuration settings"""
    host: str = Field(..., description="Ollama server URL (e.g., http://localhost:11434)")
    model: str = Field(..., description="Vision model to use (e.g., llava, qwen2-vl)")
    timeout: int = Field(..., description="Request timeout in seconds", ge=10, le=600)


class OllamaSettingsResponse(OllamaSettings):
    """Ollama settings with available models"""
    available_models: List[str] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    """Request to update settings"""
    ollama_host: Optional[str] = None
    ollama_model: Optional[str] = None
    ollama_timeout: Optional[int] = None


# List of popular vision models supported by Ollama
SUPPORTED_VISION_MODELS = [
    "llava",
    "llava:7b",
    "llava:13b",
    "llava:34b",
    "llava-phi3",
    "llava-llama3",
    "qwen2-vl",
    "qwen2-vl:2b",
    "qwen2-vl:7b",
    "minicpm-v",
    "minicpm-v:8b",
    "bakllava",
]


@router.get("/ollama", response_model=OllamaSettingsResponse)
async def get_ollama_settings():
    """
    Get current Ollama configuration settings
    """
    try:
        # Try to get available models from Ollama server
        available_models = []
        try:
            import ollama
            client = ollama.Client(host=settings.ollama_host)
            models_response = client.list()
            # Extract model names
            available_models = [model['name'] for model in models_response.get('models', [])]
            logger.info(f"Found {len(available_models)} models on Ollama server")
        except Exception as e:
            logger.warning(f"Could not fetch models from Ollama server: {e}")
            # Fallback to supported list
            available_models = SUPPORTED_VISION_MODELS

        return OllamaSettingsResponse(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout,
            available_models=available_models
        )
    except Exception as e:
        logger.error(f"Error getting Ollama settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ollama", response_model=OllamaSettings)
async def update_ollama_settings(request: SettingsUpdateRequest):
    """
    Update Ollama configuration settings

    Note: These changes are temporary and will be lost on server restart.
    To persist changes, update the .env file.
    """
    try:
        # Update settings in memory
        if request.ollama_host is not None:
            # Validate URL format
            if not request.ollama_host.startswith(('http://', 'https://')):
                raise HTTPException(
                    status_code=400,
                    detail="Ollama host must start with http:// or https://"
                )
            settings.ollama_host = request.ollama_host.rstrip('/')
            logger.info(f"Updated Ollama host to: {settings.ollama_host}")

        if request.ollama_model is not None:
            settings.ollama_model = request.ollama_model
            logger.info(f"Updated Ollama model to: {settings.ollama_model}")

        if request.ollama_timeout is not None:
            if request.ollama_timeout < 10 or request.ollama_timeout > 600:
                raise HTTPException(
                    status_code=400,
                    detail="Timeout must be between 10 and 600 seconds"
                )
            settings.ollama_timeout = request.ollama_timeout
            logger.info(f"Updated Ollama timeout to: {settings.ollama_timeout}")

        # Reinitialize the global LLaVA client with new settings
        from app.ai.llava_client import llava_client
        llava_client.host = settings.ollama_host
        llava_client.model = settings.ollama_model
        llava_client.timeout = settings.ollama_timeout
        logger.info("Reinitialized LLaVA client with new settings")

        return OllamaSettings(
            host=settings.ollama_host,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Ollama settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ollama/test")
async def test_ollama_connection():
    """
    Test connection to Ollama server and verify the configured model is available
    """
    try:
        import ollama

        # Test connection
        client = ollama.Client(host=settings.ollama_host)

        # List available models
        models_response = client.list()
        available_models = [model['name'] for model in models_response.get('models', [])]

        # Check if configured model is available
        model_available = any(
            settings.ollama_model in model or model.startswith(settings.ollama_model)
            for model in available_models
        )

        if not model_available:
            return {
                "success": False,
                "message": f"Model '{settings.ollama_model}' not found on server",
                "available_models": available_models,
                "suggestion": f"Install with: ollama pull {settings.ollama_model}"
            }

        # Try a simple chat request to verify the model works
        try:
            response = client.chat(
                model=settings.ollama_model,
                messages=[{'role': 'user', 'content': 'Hello'}],
                options={'num_predict': 10}
            )

            return {
                "success": True,
                "message": f"Successfully connected to Ollama server and verified model '{settings.ollama_model}'",
                "available_models": available_models,
                "server_version": models_response.get('version', 'unknown')
            }
        except Exception as model_error:
            return {
                "success": False,
                "message": f"Model '{settings.ollama_model}' exists but failed to respond: {str(model_error)}",
                "available_models": available_models
            }

    except Exception as e:
        logger.error(f"Error testing Ollama connection: {e}")
        return {
            "success": False,
            "message": f"Failed to connect to Ollama server at {settings.ollama_host}: {str(e)}",
            "suggestion": "Check that Ollama is running and the host URL is correct"
        }


@router.get("/models/vision")
async def list_vision_models():
    """
    List all supported vision models
    """
    return {
        "supported_models": SUPPORTED_VISION_MODELS,
        "current_model": settings.ollama_model,
        "recommendations": {
            "llava": "Best overall balance of speed and quality",
            "llava:13b": "Higher quality, slower inference",
            "qwen2-vl": "Excellent for detailed image analysis",
            "minicpm-v": "Fast and efficient for basic tasks",
            "llava-phi3": "Good balance with Microsoft Phi-3 base",
        }
    }
