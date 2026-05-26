# Autonomous Browser Agent

Production-grade autonomous browser AI agent platform using FastAPI, Playwright, browser-use, Ollama, SQLite, WebSockets, and an async workflow architecture.

## Development Order

1. Core architecture
2. Browser controller
3. Agent loop
4. Memory system
5. Workflow engine
6. FastAPI backend
7. Dashboard/frontend
8. Autonomous workflows

## Phase 1 Core

The first implementation checkpoint defines the stable contracts that later phases build on:

- runtime settings
- structured logging
- event schema
- workflow states
- database records
- memory models
- agent plan and reflection contracts
- typed tool interface

## Phase 2 Browser Controller

The browser controller checkpoint adds:

- Playwright session lifecycle
- isolated browser contexts per run
- typed browser actions
- browser observations
- screenshot path management
- structured retryable failures
- browser controller contract tests

## Phase 3 Agent Loop

The agent loop checkpoint adds:

- deterministic planner
- run context and short-term memory initialization
- tool registry
- executor loop
- retry-aware reflection decisions
- lifecycle event recording
- tests for complete, retry, and failure paths

## Phase 4 Memory System

The memory checkpoint adds:

- async database engine and session helpers
- SQLite table initialization helper
- long-term memory repository
- run summary persistence helper
- type/source/confidence filtering
- basic text retrieval policy
- tests for create, filter, search, and delete behavior

## Phase 5 Workflow Engine

The workflow checkpoint adds:

- durable run and step repositories
- workflow service for lifecycle transitions
- retry/backoff policy
- cancellation checks
- event persistence
- artifact tracking
- tests for run, step, retry, event, and artifact behavior

## Phase 6 FastAPI Backend

The backend checkpoint adds:

- FastAPI app factory
- startup database initialization
- health endpoint
- run creation, lookup, and cancellation endpoints
- run steps, events, and artifacts endpoints
- initial WebSocket event stream stub
- API contract tests with temporary SQLite storage

## Phase 7 Dashboard

The frontend checkpoint adds a static operator dashboard:

- create a run
- view run status
- refresh events and artifacts
- cancel a run
- connect to the WebSocket event stream stub
- talk to the FastAPI backend from a local file or static server

Open the dashboard after the backend is running:

```powershell
uvicorn backend.app:app --reload
```

Then open:

```text
http://127.0.0.1:8000/dashboard/
```

## Phase 8 Autonomous Workflows

The autonomous workflow checkpoint adds:

- background execution for API-created runs
- deterministic planner execution without Ollama dependency
- durable workflow steps created from planned steps
- tool execution through the registry
- persisted action, observation, reflection, and completion events
- dashboard-created runs start automatically by default

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
```

Run the focused contract tests:

```powershell
pytest
```

Install local models:

```powershell
ollama pull gemma4
ollama pull qwen2.5-coder
```

Git initialization, once Git is available:

```powershell
git init
git branch -M main
git add .
git commit -m "initialize autonomous browser agent project"
```
