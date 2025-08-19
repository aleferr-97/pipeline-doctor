import requests
from typing import Optional
from adk_app.llm.base import LLM


class OllamaLLM(LLM):
    """
    Adapter for Ollama local LLM server.
    Requires Ollama running locally, e.g.:
        ollama run llama3:8b
    """

    def __init__(self, model: str = "llama3:8b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "prompt": f"{system or ''}\n\n{prompt}",
            "stream": False,
        }
        url = f"{self.host}/api/generate"
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()
