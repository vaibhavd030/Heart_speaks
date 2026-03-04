# Heart Speaks - Spiritual RAG Chatbot

## 1. Project Description
Heart Speaks is a production-grade RAG (Retrieval-Augmented Generation) chatbot designed to read thousands of spiritual messages and discourse transcripts in PDF format and answer questions with precise, clickable citations. It features a bespoke React UI that intelligently extracts true author signatures and provides a peaceful reading experience.

## 2. Architecture & Features
- **Frontend**: A custom **Next.js** implementation boasting beautiful, spiritual aesthetics (Parchment backgrounds, Tailwind V4 CSS) and compact, expandable citation cards with PDF downloads and integrated Author extraction.
- **Backend**: A headless **FastAPI** REST API serving chat generation and static PDF files (mounted via `data/`).
- **Orchestration**: Built using **LangGraph**. Features an integrated prompt-injection validation guardrail (via OpenAI's Moderation API) and seamless conversational history routing.
- **Advanced Retrieval**:
  - **Hybrid Search**: Uses singletons for dense vector search (via ChromaDB) and sparse lexical search (BM25) to dramatically reduce latency.
  - **Query Expansion**: Uses `MultiQueryRetriever` to generate multiple semantic perspectives of the user's question before retrieving.
  - **Reranking**: Uses `FlashRank` (cross-encoder) to re-order the retrieved chunks for maximum precision. 
- **Embeddings/LLM**: `text-embedding-3-large` and `gpt-4o` from OpenAI.
- **Message Repository**: Utilizes a standalone **SQLite** database (`messages.db`) to map semantic chunks back to their full-text original source, ensuring citations expand to provide maximum context including date and parsed author signature.
- **Evaluation**: Enforces strict **Ragas** metric thresholds over a golden dataset.

## 3. Ragas Evaluation Metrics (Latest)
Our CI pipeline enforces strict thresholds over our golden datasets. The latest run achieved the following standard-setting metrics:
*   **Faithfulness**: `1.000` (Perfect grounding; zero hallucinations)
*   **Answer Relevancy**: `0.920` (Excellent structural synthesis)
*   **Context Recall**: `0.800` (Exceptional retrieval capture)
*   **Context Precision**: `0.766` (Highly accurate ranking)

## 4. Full Folder Structure

```
├── Makefile             # Automation wrapper
├── pyproject.toml       # Single-source of truth for dependencies (uv)
├── data/                # Source PDF files and SQLite DB (`messages.db`)
├── frontend/            # Next.js Application
│   ├── src/app/         # Next.js App Router
│   ├── src/components/  # React ChatInterface UI
│   └── public/          # SVGs, Fonts, Images
├── src/
│   └── heart_speaks/
│       ├── __init__.py
│       ├── api.py       # FastAPI headless server and PDF mount
│       ├── graph.py     # LangGraph Pipeline (Moderation + Retriever + Generation)
│       ├── config.py    # `pydantic-settings` to safely load .env parameters
│       ├── ingest.py    # Idempotent chunking, embedding, and Author abstraction logic
│       ├── models.py    # Pydantic data models for structured LLM response
│       ├── repository.py# SQLite Full-Text Storage
│       └── retriever.py # EnsembleRetriever + FlashRank + MultiQuery integration
└── tests/
    ├── eval/
    │   ├── run_eval.py    # Ragas strict threshold evaluation framework
    │   └── eval_dataset.json
    ├── unit/
    │   ├── test_ingest.py
    │   ├── test_models.py
    │   └── test_retriever.py 
    └── smoke/
        └── test_smoke.py  # End-to-end LangGraph integration tests
```

## 5. Installation & Run Instructions

**Prerequisites:** Assumes `uv` is installed globally (`curl -LsSf https://astral.sh/uv/install.sh | sh`), `npm` is installed, and `.env` file exists with the `OPENAI_API_KEY`.

### Local Development
```bash
# Install all Python backend dependencies
make install

# Idempotently ingest Data from your data/ folder to ChromaDB and SQLite
make ingest

# Run all strict unit and smoke tests
make test
make smoke

# Run Evaluation using Ragas to verify quality metrics
make eval

# Start the FastAPI Backend
make run-api

# In a new terminal, start the Next.js Frontend
cd frontend
npm install
npm run dev
```

## 6. Testing, Linting & CI
- **GitHub Actions**: Automated CI pipeline runs `ruff` linting, `black` formatting, `mypy` type-checking, and `pytest` on all PRs.
- **Ragas Evaluations**: `make eval` will fail CI blocks if your retrieval or language models dip below the strict quality bar defined in the script.
