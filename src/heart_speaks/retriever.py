from functools import lru_cache
from typing import Any

from langchain.retrievers import EnsembleRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI
from loguru import logger

from heart_speaks.config import settings
from heart_speaks.ingest import get_vector_store


class FlashRankRetriever(BaseRetriever):
    """A custom retriever that uses a base retriever and FlashRank for reranking."""
    base_retriever: BaseRetriever
    compressor: Any

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        docs = self.base_retriever.invoke(
            query, config={"callbacks": run_manager.get_child()}
        )
        compressed_docs = self.compressor.compress_documents(docs, query)
        
        compressed_docs = list(compressed_docs)
        
        # Diversity deduplication: remove near-duplicate chunks (cosine > 0.85)
        if len(compressed_docs) > 1:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        
            texts = [d.page_content for d in compressed_docs]
            tfidf = TfidfVectorizer().fit_transform(texts)
            sim_matrix = cosine_similarity(tfidf)
            keep = [0]
            for i in range(1, len(compressed_docs)):
                if all(sim_matrix[i][j] < 0.85 for j in keep):
                    keep.append(i)
            compressed_docs = [compressed_docs[i] for i in keep]
            
        return compressed_docs


@lru_cache(maxsize=1)
def get_cached_bm25() -> Any:
    """Caches ONLY the heavy BM25 index initialization."""
    logger.info("Initializing cached BM25 Retriever from Chroma...")
    # This vectorstore instance is only used once in the main thread to populate BM25
    init_vs = get_vector_store()
    
    try:
        data = init_vs.get()
        contents = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        
        if contents:
            docs_for_bm25 = [
                Document(page_content=c, metadata=m) 
                for c, m in zip(contents, metadatas, strict=False)
                if c is not None
            ]
            bm25_retriever = BM25Retriever.from_documents(docs_for_bm25)
            bm25_retriever.k = settings.top_k
            return bm25_retriever
    except Exception as e:
        logger.warning(f"Could not initialize BM25 Retriever, using dense only: {e}")
        
    return None


def get_reranking_retriever(search_filter: dict[str, Any] | None = None) -> FlashRankRetriever:
    """
    Returns a custom FlashRankRetriever.
    Composes retrieved singletons swiftly.
    Supports metadata filtering via search_filter dynamically.
    """
    bm25_retriever = get_cached_bm25()
    
    # Initialize Chroma client per-request to avoid Thread Deadlocks
    vectorstore = get_vector_store()
    
    # Initialize FlashRank per-request to avoid ONNX thread deadlocks
    import flashrank
    compressor = FlashrankRerank(top_n=settings.rerank_top_k, client=flashrank.Ranker())
    
    search_kwargs: dict[str, Any] = {"k": settings.top_k}
    if search_filter:
        search_kwargs["filter"] = search_filter
        
    from pydantic import SecretStr
    llm_for_mq = ChatOpenAI(
        temperature=0, 
        model="gpt-4o-mini",
        api_key=SecretStr(settings.openai_api_key)
    )
    dense_retriever = MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs),
        llm=llm_for_mq
    )
    
    if bm25_retriever:
        # Note: metadata_filter applies to dense retriever only as BM25 operates on prebuilt docs in memory.
        # This is expected behavior for local lexical caches.
        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, dense_retriever], weights=[0.4, 0.6]
        )
        base_retriever: BaseRetriever = ensemble_retriever
    else:
        base_retriever = dense_retriever
    
    return FlashRankRetriever(base_retriever=base_retriever, compressor=compressor)
