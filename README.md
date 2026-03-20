# JobSearch Local Resume Builder

This repo contains a small local web UI (static HTML) and a FastAPI backend that generates:
- an executive resume (`resume_md`)
- a LinkedIn profile draft (`linkedin_md`)

Gemini is used for the writing and evaluation steps.

## Setup

1. Create a Python virtual environment (already scaffolded as `.venv/` in this workspace).
2. Ensure you have `GEMINI_API_KEY` available in your environment.

An example is in `.env.example`. Do **not** commit your real key.

## Run

From the repo root:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Then open:
- `http://localhost:8000/`

## Usage

Paste a job description or provide a URL, choose the executive variant, then click `Generate`.

The UI calls `POST /api/generate` and displays the returned markdown.

