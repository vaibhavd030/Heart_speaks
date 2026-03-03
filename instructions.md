# Hub Health — AI Project Instructions

> **Goal:** Get a working POC up fast. A chatbot that reads podcast transcripts (JSON) and answers questions with precise citations.

---

## 1. Project Overview

| Field | Value |
|-------|-------|
| Project Name | Heart Speaks |
| Description | RAG chatbot that could answer questions from thousands of spiritual messages with citations to guide the seekers or aspirants|
| Users | Local user |
| Data | Transcript files in JSON format |

---

## 2. Tech Stack

| Component | Choice |
|-----------|--------|
| Interface | Streamlit, plain and simple with no side bars|
| LLM | GPT-4o (primary), o3-mini (fallback) |
| Orchestrator | LangChain (LCEL) |
| Vector DB | ChromaDB (local, persistent) |
| Embeddings | `text-embedding-3-large` (OpenAI) |



## 3. Environment & Installation

### 3.1 Package Manager: `uv` (mandatory)

All installation **must** go through `uv`. Never use `pip install` directly.

```bash
# Install uv (once, globally)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3.2 pyproject.toml

Create `pyproject.toml` first — this is the single source of truth for dependencies.

```toml
[project]
name = "hub-health"
version = "0.1.0"
description = "RAG chatbot over podcast transcripts"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.35.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-community>=0.3.0",
    "langchain-chroma>=0.1.4",
    "langchain-text-splitters>=0.3.0",
    "chromadb>=0.5.0",
    "openai>=1.40.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "loguru>=0.7.0",
    "python-dotenv>=1.0.0",
    "langsmith>=0.1.100",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "mypy>=1.11.0",
    "ruff>=0.6.0",
    "black>=24.8.0",
]

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = ["E501"]

[tool.mypy]
strict = true
python_version = "3.11"
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
log_cli = true
log_cli_level = "INFO"
log_file = "tests/logs/pytest.log"
log_file_level = "DEBUG"
```

### 3.3 Makefile

```makefile
.PHONY: install dev lint format typecheck test smoke clean

install:
	uv sync

dev:
	uv sync --extra dev

lint:
	uv run ruff check src/ tests/

format:
	uv run black src/ tests/

typecheck:
	uv run mypy src/

test:
	mkdir -p tests/logs
	PYTHONPATH=src uv run pytest tests/unit/ -v --tb=short

smoke:
	mkdir -p tests/logs
	PYTHONPATH=src uv run pytest tests/smoke/ -v --tb=short

ci: lint typecheck test

run:
	PYTHONPATH=src uv run streamlit run src/hub_health/app.py

clean:
	rm -rf .venv __pycache__ .mypy_cache .ruff_cache .pytest_cache
```

**Quick start:**
```bash
make dev    # install all deps including dev tools
make run    # launch the Streamlit app
```

---

## 4. Configuration

`.env.example`: look for .env file
```
OPENAI_API_KEY=sk-

```

---

## 5. Code Standards (Mandatory)

All code must comply with these rules. The CI sequence (`make ci`) enforces them.

### 5.1 Formatting & Linting
- **Black** — auto-formatter, line length 88, no config debates
- **Ruff** — fast linter, covers PEP8, imports, logic errors
- Run `make format` then `make lint` before committing

### 5.2 Type Safety
- Every function must have full type annotations (args + return type)
- **Mypy strict mode** — `make typecheck` must exit 0
- No `Any` unless unavoidable and explicitly annotated

### 5.3 Docstrings
- All public modules, classes, and functions: **Google-style docstrings**


### 5.4 Data Modelling

| Data Origin | Tool |
|-------------|------|
| Internal state / hot-path objects | `@dataclass(slots=True)` |
| External I/O (JSON transcripts, API) | `Pydantic V2 BaseModel` |
| LLM structured outputs | `Pydantic V2 BaseModel` |


### 5.5 Error Handling & Logging

- Use **Loguru** for all logging
- **Never use bare `except:`** — always catch specific exceptions
- Log with `logger.exception()` for unhandled errors (captures full stack trace)
- `LOG_LEVEL` env var controls verbosity (`DEBUG` in dev, `INFO` in prod)

```python
from loguru import logger

try:
    result = await client.embed(text)
except openai.RateLimitError as e:
    logger.warning("Rate limit hit, retrying: {}", e)
    raise
except openai.OpenAIError as e:
    logger.exception("Unexpected OpenAI error")
    raise
```

### 5.6 Async & Resource Management

- All I/O (HTTP, file reads, DB) must use `async with` / `with`
- Reuse `httpx.AsyncClient` — never instantiate inside a loop
- Use generators (`yield`) for processing large transcript files

### 5.7 AI Development Gotchas

- **Langchain refactors**: Ensure text splitters are imported from their modern packages (e.g., `from langchain_text_splitters import RecursiveCharacterTextSplitter` rather than `langchain.text_splitters`).
- **Typing imports**: Be diligent with adding `from typing import Any` and `from typing import List` when types are utilized, AI often forgets these.
- **PYTHONPATH**: When running entry points (like `pytest`, `streamlit run`, or custom scripts inside the `src` folder), ensure they run with `PYTHONPATH=src` to correctly resolve absolute imports against the `src/` layout (e.g., `from hub_health.config import settings`).

---

## 6. Logging Setup

Two log streams:

**Runtime logs** → `logs/app.log`
```python
logger.add("logs/app.log", level=os.getenv("LOG_LEVEL", "INFO"), rotation="10 MB")
```

**Test logs** → `tests/logs/pytest.log` (configured via `pyproject.toml`)

Both directories are gitignored. Create them at runtime if missing.

---

## 7. Testing Requirements

### 7.1 Unit Tests (`tests/unit/`)

Write tests for all business logic in `src/`. Tests must be importable with no Streamlit or framework side-effects.

| File | What to test |
|------|-------------|
| `test_ingest.py` | JSON parsing, chunking logic, metadata extraction |
| `test_retriever.py` | ChromaDB query returns correct shape, metadata present |
| `test_chain.py` | RAG chain returns answer + source citations, handles empty retrieval |

Each test file must:
- Use `pytest` fixtures (no repeated setup code)
- Mock OpenAI/LangSmith calls (no real API calls in unit tests)
- Log pass/fail counts to `tests/logs/`

### 7.2 Smoke Test (`tests/smoke/test_smoke.py`)

End-to-end check that all components connect. Run after `make dev` to verify setup:

```
1. Load a sample transcript JSON → ingest into ChromaDB
2. Query "What did the host say about X?" → retrieve chunks
3. Pass chunks to LLM → get answer with citations
4. Assert answer is non-empty and contains at least one source
5. Assert LangSmith trace was created (if tracing enabled)
```

Run with: `make smoke`

### 7.3 Test Log Format

Every test run must produce `tests/logs/pytest.log` with:
- Timestamp of run
- Total passed / failed / skipped
- Full tracebacks on failures
- Any LLM eval metrics (answer relevancy, faithfulness) if collected


---

## 8. Do evaluation and checks evaluation logs for 5 questions and answers pairs to validate

---

## 9. README.md (Final Deliverable after evaluation)

At project completion, the README must include:

1. Project description
2. Architecture choices with justification
3. Architecture diagram (Mermaid)
4. Full folder structure with file descriptions
5. Installation and run instructions (`make dev`, `make run`)
6. Test summary (what's covered, how to run)
7. Example usage with expected output (sample Q&A with citations)

---

## 10. Best Practices for RAG Chatbots

When building and maintaining RAG chatbots, adhere to the following best practices learned from this project:

- **Conversational Memory**: Always use a history-aware retriever that takes previous chat turns into account, reframing the user's latest message into a standalone query before performing vector search.
- **Citation Formatting**: Present citations clearly in the UI. Format them as an easy-to-read list (e.g., italicized titles with links) rather than bracketed numbers, allowing users to quickly verify the information.
- **Seamless User Experience**: The application should be ready for immediate use. Hide complex data ingestion steps from the main UI (e.g., remove unnecessary sidebars) and load the persistent vector database automatically.
- **Structured Output Reliability**: Utilize LangChain's `with_structured_output` powered by Pydantic models to guarantee that answers and nested citation objects follow the exact schema requested, avoiding hallucinated citation formats.
- **Two-Stage Retrieval (Reranking)**: Rely on a scalable base retriever combined with a compressor/reranker (e.g. Flashrank) to trim large chunk pools down to highly relevant subsets, reducing API token costs while maintaining context quality.
- **Evaluation Protocols**: Implement and run evaluation scripts (e.g., testing 5 standard Q&A pairs) to consistently measure answer relevancy and faithfulness after making pipeline changes.
- **Modular Architecture**: Strictly separate data ingestion, the retrieval interface, the LLM generation chain, and the Streamlit UI to maintain an easily testable and scalable codebase.
