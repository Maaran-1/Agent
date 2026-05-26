from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ModelProfile:
    name: str
    model: str
    temperature: float = 0.2
    timeout_seconds: float = 60.0


class OllamaClient:
    """Small async client for Ollama's local generate API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def generate(
        self,
        prompt: str,
        profile: ModelProfile,
        format_: str | None = "json",
    ) -> str:
        payload: dict[str, Any] = {
            "model": profile.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": profile.temperature},
        }
        if format_:
            payload["format"] = format_

        async with httpx.AsyncClient(timeout=profile.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

        generated = data.get("response")
        if not isinstance(generated, str):
            raise ValueError("Ollama response did not include a text response.")
        return generated


def planner_profile(model: str) -> ModelProfile:
    return ModelProfile(name="planner", model=model, temperature=0.15)

