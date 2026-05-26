import httpx
import pytest

from agents.ollama import ModelProfile, OllamaClient, planner_profile


@pytest.mark.asyncio
async def test_ollama_client_posts_generate_request(monkeypatch) -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = request.read()
        return httpx.Response(200, json={"response": "{\"objective\":\"ok\"}"})

    transport = httpx.MockTransport(handler)
    original_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    client = OllamaClient("http://ollama.local")
    response = await client.generate(
        "plan this",
        ModelProfile(name="planner", model="gemma4", temperature=0.1),
    )

    assert response == "{\"objective\":\"ok\"}"
    assert captured["url"] == "http://ollama.local/api/generate"
    assert b'"model":"gemma4"' in captured["payload"]
    assert b'"format":"json"' in captured["payload"]


def test_planner_profile_uses_requested_model() -> None:
    profile = planner_profile("qwen2.5-coder")

    assert profile.name == "planner"
    assert profile.model == "qwen2.5-coder"

