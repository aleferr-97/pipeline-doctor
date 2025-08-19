from typing import Optional

class LLM:
    """Interfaccia minimale per pluggare backend diversi (Ollama/Vertex)."""
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

class NoopLLM(LLM):
    """Fallback locale: nessun provider -> restituisce il prompt (debug-friendly)."""
    def generate(self, prompt: str, system: Optional[str] = None) -> str:
        header = "LLM non configurato: risposta deterministica.\n"
        if system:
            header += f"[system]: {system}\n"
        return header + prompt