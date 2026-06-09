"""Clase base para todos los agentes."""
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from config.settings import (
    get_ai_provider, ANTHROPIC_API_KEY, GROQ_API_KEY,
    OLLAMA_HOST, AI_MODELS
)


class BaseAgent(ABC):
    """Agente base con soporte para múltiples proveedores de IA."""

    name: str = "base"
    description: str = ""

    def __init__(self):
        self.provider = get_ai_provider()
        self._client = None
        self._setup_client()

    def _setup_client(self):
        if self.provider == "anthropic" and ANTHROPIC_API_KEY:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                self.provider = "rules"

        elif self.provider == "groq" and GROQ_API_KEY:
            try:
                import requests
                self._client = {"type": "groq", "key": GROQ_API_KEY}
            except Exception:
                self.provider = "rules"

        elif self.provider == "ollama":
            self._client = {"type": "ollama", "host": OLLAMA_HOST}

    def ask_ai(self, system_prompt: str, user_message: str,
               max_tokens: int = 1000) -> str:
        """Envía consulta al proveedor de IA activo."""
        if self.provider == "rules" or not self._client:
            return self._rules_fallback(user_message)

        try:
            if self.provider == "anthropic":
                response = self._client.messages.create(
                    model=AI_MODELS["anthropic"],
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                )
                return response.content[0].text

            elif self.provider == "groq":
                import requests
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._client['key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": AI_MODELS["groq"],
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.3
                    },
                    timeout=30
                )
                return r.json()["choices"][0]["message"]["content"]

            elif self.provider == "ollama":
                import requests
                r = requests.post(
                    f"{self._client['host']}/api/chat",
                    json={
                        "model": AI_MODELS["ollama"],
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "stream": False,
                    },
                    timeout=60
                )
                return r.json()["message"]["content"]

        except Exception as e:
            return f"[Error IA: {e}] {self._rules_fallback(user_message)}"

        return self._rules_fallback(user_message)

    def _rules_fallback(self, context: str) -> str:
        """Respuesta de fallback sin IA (solo reglas)."""
        return "Análisis basado en reglas técnicas (sin IA configurada)"

    def get_lessons_context(self) -> str:
        """Carga lecciones aprendidas para incluir en prompts."""
        try:
            from memory.database import get_lessons
            lessons = get_lessons(agent=self.name, limit=10)
            if not lessons:
                return ""
            lines = [f"- {l['lesson']} (validado {l['times_validated']}x)" for l in lessons]
            return "LECCIONES APRENDIDAS PREVIAMENTE:\n" + "\n".join(lines)
        except Exception:
            return ""

    @abstractmethod
    def run(self) -> Dict:
        """Ejecuta el análisis del agente y retorna resultados."""
        pass

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{self.name.upper()}] {message}")
