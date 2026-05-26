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
