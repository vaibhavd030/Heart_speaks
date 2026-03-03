

**Improvements Required**


# **2\. Overall Scorecard**

| Dimension | Rating | Notes |
| :---- | :---- | :---- |
| Project Structure & Packaging | **GOOD** | Clean src layout, pyproject.toml, Makefile, uv |
| Configuration Management | **GOOD** | pydantic-settings with .env, typed fields |
| RAG Pipeline Architecture | **NEEDS WORK** | LangGraph is solid choice but reranking disabled, no hybrid search |
| Ingestion Pipeline | **NEEDS WORK** | Basic chunking, no deduplication, no idempotency checks |
| Retrieval Quality | **CRITICAL** | Reranking removed, no BM25 hybrid, no query expansion |
| LLM Integration | **GOOD** | Structured outputs via Pydantic, conversation history |
| Evaluation & Metrics | **CRITICAL** | Only 5 questions, 2 metrics, no retrieval eval, no CI integration |
| Testing | **CRITICAL** | Single smoke test only, no unit tests, no mocks |
| Security & Guardrails | **NEEDS WORK** | Prompt injection check exists but uses expensive LLM call |
| Observability & Logging | **NEEDS WORK** | Loguru present but no structured logging, no LangSmith integration |
| Scalability & Deployment | **CRITICAL** | No Docker, no CI/CD, no async, module-level LLM init |
| Code Quality & Type Safety | **NEEDS WORK** | Missing Google-style docstrings on most functions, bare Exception catches |

# **3\. What Is Done Well**

## **3.1 Project Structure and Tooling**

* Clean src/ layout with proper Python packaging (src/heart\_speaks/) preventing import confusion

* pyproject.toml as single source of truth for dependencies, linting, and tooling configuration

* uv for dependency management, which is the modern best practice for Python projects

* Makefile with sensible targets: dev, lint, format, typecheck, test, smoke, ingest, eval, run, clean

* Ruff \+ Black \+ mypy configured with strict mode, demonstrating code quality awareness

## **3.2 Configuration Management (config.py)**

* pydantic-settings BaseSettings with typed fields, defaults, and .env integration is the right pattern

* RAG parameters (chunk\_size, chunk\_overlap, top\_k, rerank\_top\_k) are externalised rather than hardcoded

* extra='ignore' prevents crashes from unrelated env vars

## **3.3 Structured LLM Outputs (models.py)**

* Pydantic BaseModel for Citation and LLMResponse ensures type-safe, validated responses from GPT-4o

* with\_structured\_output(LLMResponse) in graph.py is the correct modern LangChain pattern, avoiding fragile output parsers

* Citation model captures source, page, and quote, enabling verifiable answers

## **3.4 LangGraph Orchestration (graph.py)**

* Using LangGraph StateGraph over plain LCEL chains is a strong architectural choice for multi-step workflows

* Clean separation: prompt injection check \-\> retrieval \-\> generation, with conditional routing

* GraphState TypedDict provides type safety for the workflow state

* Conversation history is properly threaded through the graph state messages

## **3.5 System Prompt Design**

* The system prompt instructs the LLM to preserve the original tone and voice of spiritual texts rather than over-summarising

* Explicit hallucination guardrail: 'If the answer is not in the context, gently say that you cannot find the answer'

* Citation requirement is built into the prompt, not left as optional

# **4\. File-by-File Critical Analysis**

## **4.1 retriever.py \- The Biggest Gap**

This is the most critical file in the entire project and it contains only 9 lines. The comment explicitly states 'Reranking removed for compatibility', which means the two-stage retrieval pipeline described in the README and EXREADME is not actually implemented.

**Current state:** The retriever simply returns top-k results from ChromaDB's cosine similarity search. There is no reranking, no hybrid search (BM25 \+ dense), no query expansion, and no Maximal Marginal Relevance (MMR) for diversity.

**Impact:** For a spiritual text corpus where many passages discuss overlapping themes (meditation, peace, karma), pure dense retrieval will return near-duplicate chunks. Without reranking, the top-8 chunks sent to GPT-4o may be repetitive rather than comprehensive, directly degrading answer quality and citation diversity.

The config.py still has top\_k=25 and rerank\_top\_k=8 parameters defined, suggesting the original design intended a retrieve-25-then-rerank-to-8 pattern using FlashRank (which is in the dependencies). This needs to be restored and enhanced.

## **4.2 ingest.py \- Functional but Fragile**

**No idempotency:** Running 'make ingest' twice will duplicate all chunks in ChromaDB. There is no deduplication logic, no content hashing, and no check for whether documents have already been ingested. In a production system with thousands of PDFs, this is a data integrity risk.

**No document ID strategy:** ChromaDB will auto-generate IDs. Without deterministic IDs (e.g., hash of source\_file \+ page \+ chunk\_index), there is no way to update or delete specific documents without wiping the entire collection.

**Basic chunking only:** RecursiveCharacterTextSplitter with chunk\_size=1000 and overlap=200 is a reasonable starting point but does not account for the structure of spiritual PDFs. Discourse transcripts often have natural section boundaries (new speaker, new topic, paragraph breaks) that a semantic or section-aware splitter would preserve.

**Metadata enrichment is minimal:** Only date extraction via regex and source\_file are added. Missing: document title, speaker/author name, discourse topic, language, and chapter/section information.

**No error handling per document:** If one PDF is corrupted or encrypted, the entire ingestion fails. There is no try/except per document with skip-and-log behaviour.

## **4.3 graph.py \- Good Structure, Several Issues**

**Module-level LLM instantiation:** Line 24 creates a ChatOpenAI instance at import time. This means the OpenAI API key must be available when the module is first imported, which breaks testability (cannot mock the LLM without monkeypatching the module). It also means every import of graph.py creates an HTTP client, which is wasteful in testing and CI environments.

**Prompt injection check uses GPT-4o-mini:** This adds latency (500-1500ms) and cost to every single user query. For a chatbot handling spiritual questions, a lightweight classifier (regex patterns \+ a small local model, or OpenAI's moderation API) would be faster and cheaper. The current approach also lacks caching: asking the same question twice runs the safety check twice.

**Retriever re-instantiated per query:** Line 64 calls get\_reranking\_retriever() inside the retrieve() function, which creates a new Chroma connection and OpenAI embeddings client on every invocation. This should be initialised once and reused.

**No error handling in nodes:** If the retrieval or generation step fails (API timeout, rate limit, empty context), the graph will crash. Each node should have try/except with structured error states.

**No streaming:** The generate() function uses invoke() which blocks until the full response is ready. For a chat interface, streaming tokens via astream would dramatically improve perceived latency.

## **4.4 app.py \- Clean but Missing Features**

**Citations not stored in session state:** Line 56 appends only the answer text to session\_state.messages, discarding the citations. On page refresh or chat continuation, the citation context is lost.

**Bare Exception catch:** Line 57 catches all exceptions including KeyboardInterrupt and SystemExit. This violates the project's own code standards from instructions.md.

**No input validation:** No max length check on user input, no empty string handling.

**No loading state feedback:** The spinner says 'Connecting with the teachings...' but gives no indication of which step (safety check, retrieval, generation) is currently running.

## **4.5 run\_eval.py \- The Evaluation Gap**

This is the second most critical gap after retriever.py. The evaluation framework has fundamental limitations:

1. Only 5 hardcoded questions, which is far too few for statistical significance. Production RAG evaluation needs 50-200+ diverse questions.

2. Only 2 metrics (faithfulness, answer\_relevancy). Missing critical retrieval metrics: context\_precision, context\_recall, context\_relevancy from RAGAS. Without these, you cannot diagnose whether poor answers come from bad retrieval or bad generation.

3. No retrieval-specific evaluation. The eval runs the full pipeline but does not separately measure whether the retriever found the right chunks. You need hit@k, MRR, and nDCG metrics.

4. Ground truths are generic and not validated against actual PDF content. If the PDFs do not contain these exact answers, the evaluation is measuring hallucination rather than retrieval accuracy.

5. No baseline comparison. Without benchmarking against different chunk sizes, top-k values, or embedding models, there is no evidence the current configuration is optimal.

6. Results are saved to CSV but not integrated into CI. There are no pass/fail thresholds that would block a deployment if quality regresses.

## **4.6 test\_smoke.py \- Insufficient Test Coverage**

The project has a single smoke test that verifies the graph compiles and returns a response. There are no unit tests whatsoever, despite the Makefile having a 'test' target pointing to tests/unit/ (which does not exist). The EXREADME references unit tests for test\_chain.py, test\_ingest.py, and test\_retriever.py, but these were never implemented.

Missing tests: chunking logic verification, metadata extraction, retriever configuration, prompt template rendering, citation parsing, error handling paths, prompt injection detection accuracy, and configuration validation.

# **5\. Retrieval & Reranking \- Deep Dive**

The retrieval pipeline is the heart of any RAG system. Currently Heart Speaks uses only dense cosine similarity via ChromaDB. For a spiritual text corpus, this is particularly problematic because spiritual concepts are highly semantically overlapping (e.g., 'peace', 'tranquility', 'serenity', 'calm' all embed near each other).

## **5.1 Recommended Architecture**

A production retrieval pipeline should implement the following stages:

| Stage | Component | Purpose | Implementation |
| :---- | :---- | :---- | :---- |
| 1 | Query Expansion | Generate multiple query variants | LLM rewrites user query into 2-3 semantic variants |
| 2 | Hybrid Search (BM25 \+ Dense) | Lexical \+ semantic coverage | BM25Retriever \+ ChromaDB, fused via Reciprocal Rank Fusion |
| 3 | Initial Retrieval (top-25) | Cast a wide net | ChromaDB.as\_retriever(search\_kwargs={'k': 25}) |
| 4 | Cross-Encoder Reranking | Precision reranking | FlashRank or cross-encoder/ms-marco-MiniLM-L-6-v2 to top-8 |
| 5 | MMR Diversity Filter | Remove near-duplicates | LangChain MMR or manual cosine dedup with threshold 0.85 |

## **5.2 Metrics to Track**

| Metric | What It Measures | Target |
| :---- | :---- | :---- |
| Hit@K (K=8) | Is the correct chunk in the top-8 retrieved? | \> 0.85 |
| MRR (Mean Reciprocal Rank) | How high is the correct chunk ranked? | \> 0.70 |
| nDCG@8 | Quality-weighted ranking across all 8 positions | \> 0.65 |
| Context Precision (RAGAS) | Are the retrieved chunks relevant to the question? | \> 0.80 |
| Context Recall (RAGAS) | Does the context cover the ground truth answer? | \> 0.75 |
| Faithfulness (RAGAS) | Are claims in the answer supported by context? | \> 0.85 |
| Answer Relevancy (RAGAS) | Is the answer relevant to the question? | \> 0.80 |
| Chunk Diversity Score | How many unique source documents in top-8? | \> 3 unique sources |

# **6\. Evaluation Framework \- Recommendations**

## **6.1 Building a Golden Dataset**

The current 5-question dataset must be expanded to 100+ questions. These should be generated through three methods:

1. Manual curation: Subject matter experts write 30-50 questions directly from the PDFs with exact page references as ground truth.

2. Synthetic generation: Use GPT-4o to read each PDF chunk and generate question-answer pairs with the chunk as the ground truth context. Filter for quality and diversity.

3. Adversarial testing: Include questions that should NOT be answerable from the corpus (e.g., 'What did Einstein say about meditation?') to test the hallucination guardrail.

## **6.2 Evaluation Layers**

The evaluation should be split into three distinct layers, each runnable independently:

**Layer 1 \- Retrieval Evaluation:** Tests only the retriever. For each question in the golden dataset, measure hit@k, MRR, and nDCG against the known ground-truth chunks. This isolates retrieval quality from generation quality.

**Layer 2 \- Generation Evaluation:** Given perfect retrieval (manually curated context), test the LLM's ability to synthesise answers. Measures faithfulness, answer relevancy, and citation accuracy.

**Layer 3 \- End-to-End Evaluation:** Full pipeline test combining retrieval and generation. Uses RAGAS context\_precision, context\_recall, faithfulness, and answer\_relevancy together.

## **6.3 CI Integration**

Evaluation results should have automated pass/fail thresholds integrated into CI. If any metric drops below the target, the deployment should be blocked. This prevents quality regressions when changing chunk sizes, embedding models, prompts, or retrieval parameters.

# **7\. Scalability & Deployment Gaps**

## **7.1 Containerisation**

There is no Dockerfile or docker-compose.yml. For deployment, the application needs a multi-stage Docker build: a build stage that installs dependencies with uv, and a runtime stage with only the necessary packages. ChromaDB persistence should be mounted as a volume.

## **7.2 Async Support**

All LLM and retrieval calls are synchronous. Streamlit's execution model somewhat mitigates this, but for any future API deployment (FastAPI), the entire pipeline should be async. LangGraph supports async natively via ainvoke().

## **7.3 ChromaDB Limitations**

ChromaDB running locally with file persistence is appropriate for a POC. For production with thousands of PDFs and concurrent users, consider: Qdrant or Weaviate for production vector storage with proper indexing and filtering, or a managed service like Pinecone or GCP Vertex AI Vector Search. ChromaDB's local mode does not support concurrent writes from multiple processes.

## **7.4 Cost Optimisation**

Currently every query makes 2 OpenAI API calls (safety check \+ generation) plus an embedding call. At scale, this costs approximately $0.03-0.08 per query. Optimisations include: replacing the GPT-4o-mini safety check with OpenAI's free moderation endpoint, caching embeddings for repeated queries, using GPT-4o-mini for simple questions and routing complex ones to GPT-4o, and implementing semantic caching for frequently asked spiritual questions.

# **8\. Prioritised Improvement Roadmap**

## **8.1 Phase 1 \- Critical Fixes (Week 1-2)**

| \# | Task | File(s) | Impact |
| :---- | :---- | :---- | :---- |
| 1 | Restore FlashRank reranking (retrieve 25, rerank to 8\) | retriever.py | Immediate retrieval quality improvement |
| 2 | Add idempotent ingestion with content hashing | ingest.py | Prevents data duplication on re-runs |
| 3 | Build golden evaluation dataset (50+ questions) | tests/eval/ | Foundation for all quality measurement |
| 4 | Add context\_precision, context\_recall to eval | run\_eval.py | Diagnose retrieval vs generation failures |
| 5 | Write unit tests for ingest, retriever, models | tests/unit/ | Test coverage and refactoring confidence |
| 6 | Fix bare Exception catches, add Google docstrings | all files | Code quality alignment with stated standards |

## **8.2 Phase 2 \- Production Hardening (Week 3-4)**

| \# | Task | File(s) | Impact |
| :---- | :---- | :---- | :---- |
| 7 | Add Dockerfile and docker-compose.yml | root | Reproducible deployment |
| 8 | Implement hybrid search (BM25 \+ dense via EnsembleRetriever) | retriever.py | Better lexical and semantic coverage |
| 9 | Replace GPT-4o-mini safety check with moderation API | graph.py | Reduced latency and cost per query |
| 10 | Add LangSmith tracing integration | graph.py, config.py | Full observability of RAG pipeline |
| 11 | Implement streaming responses in Streamlit | app.py, graph.py | Dramatically improved UX and perceived latency |
| 12 | Add GitHub Actions CI (lint, typecheck, test, eval) | .github/workflows/ | Automated quality gates |

## **8.3 Phase 3 \- Scale & Advanced Features (Week 5-8)**

| \# | Task | File(s) | Impact |
| :---- | :---- | :---- | :---- |
| 13 | Migrate to Qdrant or Pinecone for production vector DB | ingest.py, retriever.py | Concurrent access, better filtering, managed infra |
| 14 | Implement query expansion (multi-query retrieval) | graph.py, retriever.py | Better recall for ambiguous spiritual questions |
| 15 | Add semantic caching layer (GPTCache or Redis) | new cache.py | Cost reduction and latency improvement |
| 16 | Build FastAPI wrapper for API deployment | new api.py | Enables mobile, web, and integration clients |
| 17 | Implement parent-child chunking (small chunks for retrieval, full sections for context) | ingest.py | Better retrieval precision with full context for generation |
| 18 | Add metadata filtering (by date, speaker, topic) | retriever.py, app.py | User-controlled search refinement |

# **9\. Dependency Audit**

Several dependencies in pyproject.toml need attention:

* langchain-classic\>=0.0.1: This package appears unused in the codebase. If it was added during the LCEL-to-LangGraph migration, it should be removed to keep the dependency tree clean.

* trustcall\>=0.0.24: Not imported anywhere in the codebase. Remove unless there is a planned use.

* huggingface-hub\>=0.23.0: Not used in the current code. Was likely added for FlashRank model downloads but is not needed if FlashRank handles its own downloads.

* flashrank\>=0.2.8: Present in dependencies but the reranking that uses it has been removed from retriever.py. This should be restored, not removed.

* cryptography\>=41.0.0: Listed but only needed if PDFs are encrypted. Consider making this optional.

* Both ruff and black are configured: Ruff has its own formatter (ruff format) which can replace Black entirely, reducing one dev dependency.

# **10\. Architectural Debt from EXREADME**

The EXREADME.md reveals that Heart Speaks was adapted from a different project called 'Hub Health' (a Huberman podcast RAG chatbot). Several artifacts of this migration remain:

* EXREADME.md itself should be removed or merged into the main README

* The instructions.md references 'Hub Health' and JSON transcripts, but Heart Speaks uses PDFs. This creates documentation confusion.

* The original project had a more complete architecture: LCEL with ContextualCompressionRetriever \+ FlashrankRerank \+ create\_history\_aware\_retriever. The LangGraph migration lost the reranking capability.

* The original project had unit tests (test\_chain.py, test\_ingest.py, test\_retriever.py) which were not ported.

* The Makefile run target correctly points to heart\_speaks, but the original instructions.md still references hub\_health paths.

This technical debt creates confusion for contributors and suggests the project was migrated in a hurry. A clean-up pass to remove all Hub Health references and restore lost functionality would significantly improve the codebase.

# **11\. Conclusion**

Heart Speaks has a solid foundation: the choice of LangGraph for orchestration, pydantic-settings for configuration, structured outputs for citations, and uv for dependency management are all best-practice decisions that position the project well for growth.

The critical gaps are concentrated in three areas: retrieval quality (reranking disabled, no hybrid search), evaluation rigour (5 questions, 2 metrics, no retrieval-specific evaluation), and production readiness (no tests, no CI, no containerisation). These are all addressable with focused effort over 4-8 weeks.

The recommended approach is to follow the phased roadmap in Section 8, starting with the retrieval pipeline restoration and evaluation dataset construction in Phase 1\. These two changes alone will provide the measurement infrastructure needed to validate all subsequent improvements with data rather than intuition.

The project demonstrates clear architectural thinking and awareness of modern AI engineering patterns. With the improvements outlined in this document, Heart Speaks can evolve from a well-structured POC into a production-grade spiritual RAG system capable of serving thousands of seekers with accurate, cited answers.