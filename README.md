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

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install
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
