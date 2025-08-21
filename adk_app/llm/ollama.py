import os
import requests
from typing import Optional
from adk_app.llm.base import LLM


class OllamaLLM(LLM):
    """
    Adapter for Ollama local LLM server.
    Requires Ollama running locally, e.g.:
        ollama run llama3:8b
    """

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        temperature: Optional[float] = None,
        num_predict: Optional[int] = None,
        num_ctx: Optional[int] = None,
        top_p: Optional[float] = None,
        repeat_penalty: Optional[float] = None,
    ):
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3:8b")
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.temperature = float(temperature or os.getenv("OLLAMA_TEMPERATURE", 0.2))
        self.num_predict = int(num_predict or os.getenv("OLLAMA_NUM_PREDICT", 256))
        self.num_ctx = int(num_ctx or os.getenv("OLLAMA_NUM_CTX", 4096))
        self.top_p = float(top_p or os.getenv("OLLAMA_TOP_P", 0.9))
        self.repeat_penalty = float(repeat_penalty or os.getenv("OLLAMA_REPEAT_PENALTY", 1.1))

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "prompt": f"{system or ''}\n\n{prompt}",
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                "num_ctx": self.num_ctx,
                "top_p": self.top_p,
                "repeat_penalty": self.repeat_penalty,
            },
        }
        url = f"{self.host}/api/generate"
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()