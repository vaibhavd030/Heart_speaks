# Heart Speaks - Spiritual RAG Chatbot

## 1. Project Description
Heart Speaks is a production-grade RAG (Retrieval-Augmented Generation) chatbot designed to read thousands of spiritual messages and discourse transcripts in PDF format and answer questions with precise, clickable citations. It features a bespoke React UI that intelligently extracts true author signatures and provides a peaceful reading experience.
## 2. Dataset Description & Statistics
The primary knowledge base consists of the **"All Whispers Messages"** dataset, a comprehensively curated collection of transcribed spiritual discourses and messages.
- **Total Messages:** 4,681 PDF transcripts.
- **Date Range:** Detailed records spanning from the early 1990s through recent years (e.g., 1991 - 2017).
- **Authorship:** Insights drawn directly from spiritual guides (e.g., Babuji Maharaj) as identified through filename metadata signatures.
- **Organization:** The raw repository is strictly chronologically partitioned (`/YYYY/Month/Message.pdf`) to enable deep Exploratory Data Analysis (EDA) on the frontend Dashboard.

## 3. Architecture & Features
- **Frontend**: A custom **Next.js** implementation boasting beautiful, spiritual aesthetics (Parchment backgrounds, Tailwind V4 CSS).
- **Backend**: A headless **FastAPI** REST API serving chat generation and static PDF files (mounted via `data/`).
- **Production Authentication**: Complete registration flow with **Admin Approval** via dashboard and Email notifications (Gmail SMTP).
- **Reader Sequence Filtering**: Intelligent backend filtering that dynamically checks disk for PDF existence to ensure a contiguous reading experience.
- **Orchestration**: Built using **LangGraph**. Features an integrated prompt-injection validation guardrail and seamless conversational history routing.
- **Advanced Retrieval**:
  - **Hybrid Search**: Uses singletons for dense vector search (via ChromaDB) and sparse lexical search (BM25) to dramatically reduce latency.
  - **Query Expansion**: Uses `MultiQueryRetriever` to generate multiple semantic perspectives.
  - **Reranking**: Uses `FlashRank` (cross-encoder) to re-order the retrieved chunks for maximum precision. 
- **Message Repository**: Utilizes a standalone **SQLite** database (`messages.db`) to map semantic chunks back to their full-text original source.

## 4. Architecture Diagram

```mermaid
graph TD
    %% Ingestion Flow
    A[Spiritual PDF Files] -->|PyPDF Loader + Content Hashing| B(Document Chunks)
    A -->|Extract Bottom Signature| M[Author Metadata]
    B -->|text-embedding-3-large| C[(ChromaDB)]
    B -->|Keyword Term Frequencies| K[(BM25 Index Singleton)]
    
    B -->|Full Text + Metadata| DB[(SQLite messages.db)]
    M --> DB
    
    %% Retrieval Flow
    D[User Request] --> E{Next.js Frontend}
    E -->|REST API /chat| F[FastAPI Server]
    F -->|GraphState Messages| G[LangGraph Agent]
    
    G --> H{Moderation Check Node}
    H -- Unsafe --> I[Refusal Message]
    H -- Safe --> J[MultiQuery + Hybrid Retrieval Node]
    
    J <-->|Dense Search| C
    J <-->|Sparse Search| K
    J -->|FlashRank Reranking| L[Re-ordered Context]
    
    L -->|Context + Conversational History| N[Generation Node]
    
    N -->|GPT-4o Structured Output| O[Citation Enrichment]
    O <-->|Fetch Full Text & True Author| DB
    O -->|Rich Citation Cards| E
```

## 5. Ragas Evaluation Metrics (Latest)
Our CI pipeline enforces strict thresholds over our golden datasets. The latest run achieved the following standard-setting metrics:
*   **Faithfulness**: `1.000` (Perfect grounding; zero hallucinations)
*   **Answer Relevancy**: `0.920` (Excellent structural synthesis)
*   **Context Recall**: `0.800` (Exceptional retrieval capture)
*   **Context Precision**: `0.766` (Highly accurate ranking)

## 6. Full Folder Structure

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

## 7. Installation & Run Instructions

**Prerequisites:** Assumes `uv` is installed globally (`curl -LsSf https://astral.sh/uv/install.sh | sh`), `npm` is installed, and `.env` file exists with the `OPENAI_API_KEY`.

### Local Development (Quickstart)
```bash
# 1. Install all backend dependencies
make install

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Idempotently ingest Data from your data/ folder to ChromaDB and SQLite
make ingest

# 4. Start the Application (Spins up FastAPI and Next.js concurrently)
make start
```
*The Frontend will be available at `http://localhost:3000` and the Backend API at `http://localhost:8000`.*

### Docker Deployment
You can easily spin up the entire architecture (FastAPI Backend + Next.js Frontend) using Docker Compose:
```bash
docker-compose up --build -d
```

## 8. User Registration & Features

### Registration & Access Workflow
SAGE implements a secure, admin-gated registration process to ensure the integrity of the spiritual archives.

1.  **Registration**: New seekers register via the **Login** page by providing their Name, Email, and **Abhyasi ID**.
2.  **Admin Review**: A notification is automatically dispatched to the administrator (`vaibhav030@gmail.com`).
3.  **Approval**: The administrator reviews pending requests in the **Archive Dashboard**. Once approved, the seeker's status is updated.
4.  **Login**: Seekers log in using their **Email** as the username and **Abhyasi ID** as the initial password.

---

### Core Applications

#### 1. SAGE Chat Interface
The heart of the application. Engage in deep, contextual conversations with the spiritual archive.
- **Hybrid Retrieval**: Combines semantic vector search with keyword-based BM25 search for precise citations.
- **Citation Cards**: Every response includes expandable citations. Click a citation to view the exact excerpt or download the original PDF.

#### 2. Reader Mode (`/reader`)
A dedicated space for focused study of the whispers.
- **Sequential Navigation**: Read through the archives chronologically using the "Next" and "Prev" buttons.
- **Dynamic Filtering**: The system automatically skips messages with missing source files, ensuring a seamless experience.
- **Persistence**: Your progress is saved automatically. Return to exactly where you left off in your next session.
- **Reflections**: Jot down personal notes and bookmarks. These are saved to your profile for future review.

#### 3. Saved Reflections (`/bookmarks`)
Your personal library of meaningful whispers.
- **Chronological Review**: All bookmarked messages are listed in the order they were originally delivered.
- **Personal Log**: View and manage the notes you've taken during study.
- **Direct Access**: Jump back into the PDF or remove reflections as your journey evolves.

#### 4. Archive Dashboard (`/dashboard`)
A powerful tool for exploratory data analysis and administrative management.
- **Statistical Insights**: Visualize the temporal distribution of whispers across decades.
- **Repository Search**: Perform full-text searches across the entire SQLite dataset to locate specific keywords or authors.
- **Admin Management**: (For Admins) Approve or reject new user registrations to grant access to the system.

## 9. Testing, Linting & CI
- **GitHub Actions**: Automated CI pipeline runs `ruff` linting, `black` formatting, `mypy` type-checking, and `pytest` on all PRs.
- **Ragas Evaluations**: `make eval` will fail CI blocks if your retrieval or language models dip below the strict quality bar defined in the script.
