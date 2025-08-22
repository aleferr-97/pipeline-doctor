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
        response_format: Optional[str] = None
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.temperature = float(temperature)
        self.num_predict = int(num_predict)
        self.num_ctx = int(num_ctx)
        self.top_p = float(top_p)
        self.repeat_penalty = float(repeat_penalty)
        self.response_format = response_format

    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": self.response_format,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.num_predict,
                "num_ctx": self.num_ctx,
                "top_p": self.top_p,
                "repeat_penalty": self.repeat_penalty,
            },
        }
        if system:
            payload["system"] = system
        if self.response_format:
            payload["format"] = self.response_format
        url = f"{self.host}/api/generate"
        r = requests.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data.get("response", "").strip()