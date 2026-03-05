# Heart Speaks - Context Extraction & Retrieval Architecture

This document details exactly how the "Heart Speaks" assistant processes, chunks, retrieves, and organizes context from the source documents to feed into the language model.

## 1. Document Ingestion & Chunking
The system processes PDF files located in the configured `data_dir` (default `./data`).

**Parsing and Splitting:**
- **Text Splitter**: `RecursiveCharacterTextSplitter`
- **Chunk Size**: `1000` characters.
- **Chunk Overlap**: `200` characters.
- **Separators**: `["\n\n", "\n", " ", ""]` (Prioritizes splitting by double newlines, then single newlines, then spaces).
- **Embeddings Model**: `text-embedding-3-large` (OpenAI).
- **Vector Database**: ChromaDB.

**Metadata Extraction:**
Each ingested chunk includes the following metadata:
- `source_file`: The filename of the PDF.
- `date`: Extracted from the filename (expecting a `YYYY-MM-DD` pattern).
- `page`: The page number of the PDF where the chunk originated.

*(Additionally, full texts of the documents are saved into a SQLite repository to enable full-text clickable citations later).*

---

## 2. The Retrieval Pipeline
The application uses a highly optimized dual-retrieval and reranking pipeline (`FlashRankRetriever`) to find the most relevant context.

### Step 2a. Initial Retrieval (Top 25)
The system retrieves an initial wide net of the top **25 chunks** (`settings.top_k = 25`) using an `EnsembleRetriever` that combines two distinct methods:

1. **Keyword/Lexical Search (BM25) - 40% Weight**: 
   - A `BM25Retriever` initialized natively from the ChromaDB documents.
2. **Dense Semantic Search (Multi-Query) - 60% Weight**:
   - A `MultiQueryRetriever` powered by `gpt-4o-mini` (temperature = 0).
   - This LLM generates multiple nuanced variations of the user's question, which are all embedded and run against the vector store to ensure high recall, even if the user phrased their question ambiguously.

### Step 2b. Reranking and Compression (Top 8)
Once the `EnsembleRetriever` fetches the best combined subset of chunks (representing the top 25), it passes them to a cross-encoder reranker:
- **Reranker**: `FlashrankRerank` 
- **Final Context Size**: It compresses and reranks the documents down to the absolute **top 8 most relevant chunks** (`settings.rerank_top_k = 8`).

This ensures the LLM receives highly dense, accurate context without overwhelming its context window or diluting the instructions.

---

## 3. Assembling the Context for the LLM
Once the top 8 chunks are retrieved, the orchestration graph (`graph.py`) formats them into a single coherent string before injecting them into the prompt.

**Extraction loop for the final prompt:**
```python
formatted_context = []
for d in docs:
    content = d.page_content
    source = d.metadata.get("source_file", "Unknown PDF")
    date = d.metadata.get("date", "Unknown Date")
    page = d.metadata.get("page", 0)
    
    # Format for each chunk
    formatted_context.append(f"[Source File: {source}, Date: {date}]\n{content}")
```

**Final Concatenation:**
The 8 formatted chunks are joined together using a strict visual separator (`\n\n---\n\n`) to clearly demarcate the boundaries of different textual sources for the language model.

```python
context = "\n\n---\n\n".join(state.get("context", []))
```

This single `context` string is then directly substituted into the `{context}` variable in the grounding prompt instructing the LLM to formulate its answer based exclusively on these 8 ranked chunks.
