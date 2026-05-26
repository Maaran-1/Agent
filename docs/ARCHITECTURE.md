# Autonomous Browser Agent Architecture

## Goal

Build a fully autonomous browser AI agent platform that can plan, execute, observe, remember, recover, and stream progress while controlling real browser sessions through Playwright, browser-use, and local Ollama models.

## System Boundaries

- `backend`: FastAPI application, HTTP API, WebSocket streaming, dependency injection, auth boundary, request validation.
- `frontend`: Operator dashboard for task creation, live browser state, workflow status, logs, memory inspection, and run history.
- `agents`: Planner, executor, critic, reflection loop, task state machine, model routing, autonomous loop.
- `browser`: Playwright runtime, browser-use adapter, session lifecycle, context isolation, crash recovery, screenshots, DOM extraction.
- `memory`: Short-term run memory, long-term SQLite memory, embeddings-ready interfaces, retrieval policies, memory pruning.
- `workflows`: Workflow definitions, orchestration engine, step graph, retries, pause/resume, compensation hooks.
- `tools`: Agent-callable tools for browser actions, OCR, filesystem-safe utilities, network fetches, and structured data transforms.
- `configs`: Environment settings, model profiles, browser runtime settings, logging settings.
- `logs`: Runtime logs, traces, screenshots, captured artifacts.
- `tests`: Unit, integration, browser runtime, workflow, and API tests.
- `scripts`: Setup, health checks, database migrations, model checks, and local development helpers.
- `docs`: Architecture, operating model, API contracts, workflow authoring, and reliability notes.

## Runtime Flow

1. Client submits a task through FastAPI.
2. Backend creates a run record in SQLite and opens a WebSocket event stream.
3. Planner decomposes the task into structured objectives and executable steps.
4. Executor requests browser actions through the browser runtime.
5. Browser runtime applies actions in isolated Playwright contexts.
6. Observer captures page state, screenshots, DOM summaries, console errors, network hints, and OCR when needed.
7. Reflection loop compares observed state with expected state and decides whether to continue, retry, re-plan, or fail gracefully.
8. Memory system stores important run facts and retrieves relevant prior context for future steps.
9. Workflow engine persists progress, emits events, and handles retries, timeouts, and cancellation.
10. Dashboard receives live events over WebSockets.

## Agent Subsystems

### Planner

Responsibilities:

- Convert user goals into a structured task plan.
- Identify required tools, browser targets, success criteria, and risk level.
- Produce small executable steps rather than broad instructions.
- Re-plan when observations contradict the current plan.

Core inputs:

- User task
- Retrieved memory
- Current browser state
- Workflow status
- Tool registry

Core outputs:

- Step plan
- Expected observations
- Retry policy
- Stop condition

### Executor

Responsibilities:

- Execute one step at a time.
- Call browser, OCR, memory, and workflow tools through typed interfaces.
- Enforce timeouts, max retries, and cancellation checks.
- Return structured action results to the reflection loop.

### Reflection Loop

Responsibilities:

- Compare actual observations with the planned expected state.
- Detect loops, browser drift, missing elements, captchas, login walls, crashes, and stale pages.
- Decide between continue, retry, re-plan, ask operator, or fail.
- Store useful lessons in long-term memory.

## Browser Runtime

Use Playwright as the primary browser control layer and browser-use as a higher-level browser agent adapter.

Responsibilities:

- Launch and close browser instances.
- Create isolated contexts per run.
- Manage pages, tabs, downloads, permissions, cookies, and viewport profiles.
- Capture screenshots and DOM snapshots.
- Recover from browser crashes by restarting the context and restoring known state when possible.
- Provide stable typed actions: navigate, click, type, select, wait, extract, screenshot, evaluate, download.

## Memory System

### Short-Term Memory

Per-run memory used by planner and executor:

- Current objective
- Completed steps
- Page observations
- Tool outputs
- Retry history
- Active hypotheses

### Long-Term Memory

SQLite-backed storage for:

- Successful task patterns
- Domain-specific notes
- User preferences
- Tool performance records
- Workflow outcomes

Initial storage can be plain relational SQLite. Keep interfaces embeddings-ready so vector search can be added later without rewriting agent logic.

## Workflow Engine

Responsibilities:

- Represent work as durable runs and steps.
- Support retries, backoff, pause, resume, cancel, and timeout.
- Emit structured lifecycle events.
- Track artifacts such as screenshots, logs, extracted data, and final reports.

Core states:

- `queued`
- `planning`
- `running`
- `waiting`
- `retrying`
- `completed`
- `failed`
- `cancelled`

## FastAPI Backend

Initial API shape:

- `POST /runs`: create a browser agent run.
- `GET /runs/{run_id}`: inspect run status.
- `POST /runs/{run_id}/cancel`: request cancellation.
- `GET /runs/{run_id}/artifacts`: list generated artifacts.
- `WS /runs/{run_id}/events`: stream run events.
- `GET /health`: runtime health check.

## WebSocket Events

Events should be structured and versioned:

- `run.created`
- `run.planning`
- `step.started`
- `browser.action`
- `browser.observation`
- `reflection.decision`
- `memory.write`
- `step.completed`
- `step.failed`
- `run.completed`
- `run.failed`

## Ollama Integration

Use Ollama for local model inference with profile-based routing:

- `gemma4`: general planning, reflection, summaries.
- `qwen2.5-coder`: code-aware tasks, structured transformations, debugging.

The model client should expose one async interface:

- `complete(prompt, model_profile, schema=None)`
- `stream(prompt, model_profile, schema=None)`

This keeps the agent independent from a specific model backend.

## Database Structure

Initial SQLite tables:

- `runs`: run metadata, task, status, timestamps, model profile.
- `steps`: planned and executed steps, status, attempts, timing.
- `events`: append-only run event log.
- `artifacts`: screenshots, downloaded files, extracted data, reports.
- `memories`: long-term memory records with type, source, confidence, timestamps.
- `tool_calls`: tool call inputs, outputs, errors, duration.

## Reliability

Use explicit reliability policies:

- Retries use bounded exponential backoff.
- Browser actions have per-action timeout and run-level timeout.
- Every tool returns structured success or failure.
- Browser crash recovery restarts only the affected run context.
- Reflection loop detects repeated failed actions and triggers re-planning.
- Logs are structured and correlated with `run_id`, `step_id`, and `tool_call_id`.

## Testing Strategy

- Unit tests for planner contracts, memory repositories, retry policies, and workflow state transitions.
- Integration tests for FastAPI routes and WebSocket events.
- Browser tests against local static pages for click, type, extract, and recovery flows.
- Model client tests with stubbed Ollama responses.
- End-to-end smoke test for a short autonomous browser run.

## Implementation Phases

### Phase 1: Core Architecture

- Settings model
- Logging setup
- Event schema
- Database models
- Workflow state model
- Tool interface contracts

### Phase 2: Browser Controller

- Playwright manager
- Browser session lifecycle
- Typed browser actions
- Screenshots and DOM snapshots
- Crash recovery basics

### Phase 3: Agent Loop

- Planner interface
- Executor loop
- Reflection decisions
- Stop conditions
- Event streaming hooks

### Phase 4: Memory System

- SQLite repositories
- Short-term memory object
- Long-term memory CRUD
- Retrieval policies

### Phase 5: Workflow Engine

- Durable run orchestration
- Step execution
- Retries and cancellation
- Artifact tracking

### Phase 6: FastAPI Backend

- App factory
- REST endpoints
- WebSocket endpoint
- Background run management

### Phase 7: Dashboard

- Run creation
- Live event feed
- Browser screenshot panel
- Status timeline
- Artifact viewer

### Phase 8: Autonomous Workflows

- Reusable workflow definitions
- Scheduled or triggered runs
- Operator approval checkpoints
- Production hardening
