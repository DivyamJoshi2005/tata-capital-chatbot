import os
import json
import asyncio
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Built-in lightweight .env loader fallback using standard library
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'").strip('"')
                    if k not in os.environ:
                        os.environ[k] = v

# --- Configuration Constants ---
DEFAULT_OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# We use deepseek-r1:1.5b for fast reasoning
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")


class OllamaChatMessage:
    def __init__(self, content: str):
        self.content = content


class OllamaChoice:
    def __init__(self, message: OllamaChatMessage):
        self.message = message


class OllamaChatResponse:
    def __init__(self, content: str):
        self.choices = [OllamaChoice(OllamaChatMessage(content))]


class OllamaChatCompletions:
    def __init__(self, base_url: str, default_model: str):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def _sync_post(self, url: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))

    async def create(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, str]] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> OllamaChatResponse:
        target_model = model or self.default_model
        endpoint = f"{self.base_url}/api/chat"

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        # Support JSON mode if requested
        if response_format and response_format.get("type") == "json_object":
            payload["format"] = "json"

        try:
            result = await asyncio.to_thread(self._sync_post, endpoint, payload)
            content = result.get("message", {}).get("content", "")
            return OllamaChatResponse(content)
        except urllib.error.URLError as e:
            error_msg = (
                f"Failed to connect to local Ollama at {self.base_url}. "
                f"Make sure Ollama is running (`ollama serve`) and model '{target_model}' is installed (`ollama pull {target_model}`). Error: {e}"
            )
            print(f"[Ollama Error] {error_msg}")
            raise ConnectionError(error_msg) from e
        except Exception as e:
            print(f"[Ollama Error] Chat completion failed: {e}")
            raise e

    async def create_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        import httpx
        target_model = model or self.default_model
        endpoint = f"{self.base_url}/api/chat"

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", endpoint, json=payload, timeout=None) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
        except Exception as e:
            print(f"[Ollama Stream Error]: {e}")
            yield " [Connection Error]"


class OllamaChat:
    def __init__(self, base_url: str, default_model: str):
        self.completions = OllamaChatCompletions(base_url, default_model)


class AsyncOllamaClient:
    """
    Lightweight OpenAI/Groq compatible client for local Ollama server.
    Requires no heavy external dependencies and provides full async support.
    """
    def __init__(self, base_url: str = DEFAULT_OLLAMA_BASE_URL, default_model: str = DEFAULT_OLLAMA_MODEL):
        self.base_url = base_url
        self.default_model = default_model
        self.chat = OllamaChat(base_url, default_model)


def is_ollama_available(base_url: str = DEFAULT_OLLAMA_BASE_URL) -> bool:
    """Checks if the local Ollama daemon is reachable."""
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/api/version", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def get_available_ollama_models(base_url: str = DEFAULT_OLLAMA_BASE_URL) -> List[str]:
    """Lists locally installed Ollama models."""
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m.get("name") for m in data.get("models", [])]
    except Exception:
        return []


def get_llm_client():
    """
    Factory that returns the local Ollama LLM client and model name, completely avoiding API usage.
    
    Returns:
        (client, model_name, provider_name)
    """
    model_name = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    print(f"🦙 Initializing Local Open Source LLM (Ollama) -> Model: '{model_name}' at '{base_url}'")
    client = AsyncOllamaClient(base_url=base_url, default_model=model_name)
    return client, model_name, "ollama"
