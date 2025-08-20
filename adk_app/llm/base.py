from typing import Optional

class LLM:
    """Interface for backends (Ollama/Vertex)."""
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

class NoopLLM(LLM):
    """Local Fallback"""
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        header = "LLM non configurato: risposta deterministica.\n"
        if system:
            header += f"[system]: {system}\n"
        return header + prompt