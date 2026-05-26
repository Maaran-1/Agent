from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from backend.app import create_app
from configs.settings import Settings


def make_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        app_name="Test Browser Agent",
        environment="test",
        sqlite_path=tmp_path / "api.sqlite3",
        logs_dir=tmp_path / "logs",
    )
    return TestClient(create_app(settings))


def test_health_endpoint(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_name": "Test Browser Agent",
        "environment": "test",
    }


def test_dashboard_static_files_are_served(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/dashboard/")

    assert response.status_code == 200
    assert "Browser Agent" in response.text


def test_cors_preflight_allows_dashboard_requests(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.options(
            "/runs",
            headers={
                "Origin": "null",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_create_and_get_run(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post(
            "/runs",
            json={
                "task": "Open billing dashboard",
                "model_profile": "gemma4",
                "auto_start": False,
            },
        )
        run_id = created.json()["id"]
        fetched = client.get(f"/runs/{run_id}")

    assert created.status_code == 201
    assert created.json()["status"] == "queued"
    assert fetched.status_code == 200
    assert fetched.json()["task"] == "Open billing dashboard"


def test_cancel_run(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/runs", json={"task": "Cancelable task", "auto_start": False})
        run_id = created.json()["id"]
        cancelled = client.post(
            f"/runs/{run_id}/cancel",
            json={"reason": "Operator stopped the run."},
        )
        events = client.get(f"/runs/{run_id}/events")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert any(event["type"] == "run.cancelled" for event in events.json())


def test_missing_run_returns_404(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_run_events_and_artifacts_start_empty(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/runs", json={"task": "Inspect page", "auto_start": False})
        run_id = created.json()["id"]
        events = client.get(f"/runs/{run_id}/events")
        artifacts = client.get(f"/runs/{run_id}/artifacts")
        steps = client.get(f"/runs/{run_id}/steps")

    assert events.status_code == 200
    assert any(event["type"] == "run.created" for event in events.json())
    assert artifacts.status_code == 200
    assert artifacts.json() == []
    assert steps.status_code == 200
    assert steps.json() == []


def test_websocket_event_stub_connects(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/runs", json={"task": "Stream events", "auto_start": False})
        run_id = created.json()["id"]
        with client.websocket_connect(f"/runs/{run_id}/events/ws") as websocket:
            message = websocket.receive_json()

    assert message["type"] == "connection.ready"
    assert message["run_id"] == run_id


def test_create_run_auto_starts_workflow(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        created = client.post("/runs", json={"task": "Autonomous echo task"})
        run_id = created.json()["id"]
        fetched = client.get(f"/runs/{run_id}")
        for _ in range(10):
            if fetched.json()["status"] == "completed":
                break
            sleep(0.05)
            fetched = client.get(f"/runs/{run_id}")
        steps = client.get(f"/runs/{run_id}/steps")
        events = client.get(f"/runs/{run_id}/events")

    assert created.status_code == 201
    assert fetched.json()["status"] == "completed"
    assert len(steps.json()) == 1
    event_types = [event["type"] for event in events.json()]
    assert "browser.action" in event_types
    assert "browser.observation" in event_types
    assert "run.completed" in event_types
