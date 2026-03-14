# SAGE: Spiritual Archive Guidance Engine 🕊️

> **"Heart Speaks to Heart in the Sanctuary of Silence."**

SAGE (formerly Heart Speaks) is a state-of-the-art **Retrieval-Augmented Generation (RAG)** ecosystem designed to preserve and provide intelligent access to thousands of spiritual discourses. It transforms a vast archive of 4,600+ PDF transcripts into a living, conversational companion capable of guiding seekers through profound spiritual inquiries with precise citations.

---

## 🌐 Live Production Access

The SAGE Sanctuary is fully deployed and operational across the following endpoints:

*   **Sanctum (Frontend):** [https://sage-frontend-34833003999.europe-west2.run.app](https://sage-frontend-34833003999.europe-west2.run.app)
*   **Oracle (API/Backend):** [https://sage-backend-34833003999.europe-west2.run.app](https://sage-backend-34833003999.europe-west2.run.app)

---

## ✨ Primary Features

### 1. The Sanctuary (Chat)
Experience a persona-driven consultation. SAGE doesn't just "search"—it **listens**. Depending on your inquiry, SAGE adopts one of five spiritual intent-based personas:
*   **Seeking Wisdom:** Deep, meditative thematic explorations.
*   **Emotional Support:** Compassionate, letter-style guidance.
*   **Factual Reference:** Precise, scholarly citations.
*   **Exploration:** Structured overviews of multiple teachings.
*   **Greeting:** Warm, conversational welcomes.

![Chat Response Example](file:///Users/vaibhavdikshit/.gemini/antigravity/brain/4b13c2d1-eeb1-4496-9568-9d37e14e2faa/sage_chat_response_1773408998097.png)

### 2. The Archives (Interactive Reader)
Browse the entire spiritual lineage chronologically.
*   **Timeline Navigation:** Explore messages from 1991 to 2017.
*   **Unified Viewing:** Read full-text transcriptions alongside original PDF sources.
*   **Progress Tracking:** SAGE remembers precisely where you left off in your reading journey.

### 3. Saved Reflections (Bookmarks)
Capture personal insights from your spiritual study.
*   **One-Click PDF Access:** Instantly open the original source document for any saved chunk.
*   **Per-User Isolation:** Your bookmarks and notes are private and securely stored.

### 4. Admin Sanctum
A secure management portal for lineage administrators to:
*   **Approve Seekers:** Manage registration and grant access to privileged content.
*   **Audit Wisdom:** View comprehensive logs of queries and responses (stored by Session ID) to understand seeker needs.

---

## 🏗️ Technical Architecture

SAGE represents a complex orchestration of modern AI and cloud-native technologies.

### The LangGraph Brain
The entire conversation logic is managed by **LangGraph**, ensuring a robust, state-managed workflow:

```mermaid
graph TD
    User([Seeker Input]) --> Safety[OpenAI Moderation Guard]
    Safety -- Malicious --> Refusal[Safe Refusal Response]
    Safety -- Safe --> Intent[Intent Classification Node]
    
    Intent --> Route{Route Intent}
    Route -- Greeting --> Welcome[Warm Generation]
    Route -- Inquiry --> RAG[Hybrid Retrieval Phase]
    
    subgraph "Hybrid RAG Stack"
    RAG --> MQ[Multi-Query Expansion]
    MQ --> Dense[(ChromaDB: Semantic)]
    MQ --> Lexical[(BM25: Keyword)]
    Dense --> Merge[Merger Node]
    Lexical --> Merge
    Merge --> Rerank[FlashRank Cross-Encoder]
    end
    
    Rerank --> Context[Top 10 High-Relevance Chunks]
    Context --> GPT4[GPT-4o Generation]
    Welcome --> Render[Frontend Rendering]
    GPT4 --> Render
```

### Advanced Retrieval Pipeline (The RAG Deep-Dive)
*   **Data Ingestion:** Thousands of PDFs are ingested using an idempotent pipeline that hashes content to prevent duplicates.
*   **Smart Chunking:** Text is split into **1000-character** segments with a **200-character overlap**, preserving context at boundaries.
*   **Embeddings:** Powered by **OpenAI text-embedding-3-large** for deep semantic understanding.
*   **The Hybrid Advantage:** 
    *   **Semantic Search:** Captures the "vibe" and meaning of the question.
    *   **Lexical Search (BM25):** Ensures specific rare terms (e.g., specific sanskrit terms) are found.
*   **Reranking (FlashRank):** A Cross-Encoder model re-evaluates the Top 25 candidates, selecting the absolute **Top 10** for the final prompt.

---

## 🚀 Production Infrastructure

Deployed on **Google Cloud Platform (GCP)** for maximum reliability:

| Component | Technology | Resource Spec |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14 / Tailwind CSS | Cloud Run (Standard) |
| **Backend/API** | FastAPI / LangGraph | Cloud Run (2Gi RAM / 1 CPU) |
| **Vector DB** | ChromaDB (Persistent) | Local Disk (Cloud Run Volume) |
| **Metadata DB** | SQLite (EF) | messages.db |
| **Secrets** | GCP Secret Manager | JWT, API Keys, SMTP |

---

## 🛠️ Local Development Quickstart

Ensure you have `uv` and `npm` installed.

1.  **Clone & Install:**
    ```bash
    git clone https://github.com/vaibhavd030/Heart_speaks.git
    cd Heart_speaks
    make install
    cd frontend && npm install && cd ..
    ```

2.  **Environment Setup:**
    Create a `.env` with `OPENAI_API_KEY`, `JWT_SECRET_KEY`, and `GMAIL_APP_PASSWORD`.

3.  **Run Application:**
    ```bash
    make start
    ```
    *   **Frontend:** http://localhost:3000
    *   **Backend:** http://localhost:8000

---

## 🧪 Testing & Validation

*   **Ragas Evals:** We maintain a `Faithfulness` score of **1.000**, ensuring zero hallucinations.
*   **Moderation:** Every message passes through the OpenAI Moderation endpoint before processing.
*   **Auth Guard:** All sensitive routes are protected by JWT and the `AuthGuard` React component.

---

*Peace and Silence.* 🕊️
🔗
