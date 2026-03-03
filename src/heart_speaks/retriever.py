from typing import List, Any
from loguru import logger

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank

from heart_speaks.config import settings
from heart_speaks.ingest import get_vector_store


class FlashRankRetriever(BaseRetriever):
    """A custom retriever that uses a base retriever and FlashRank for reranking."""
    base_retriever: BaseRetriever
    compressor: Any

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        docs = self.base_retriever.invoke(
            query, config={"callbacks": run_manager.get_child()}
        )
        compressed_docs = self.compressor.compress_documents(docs, query)
        return list(compressed_docs)


def get_reranking_retriever(search_filter: dict | None = None) -> FlashRankRetriever:
    """
    Returns a custom FlashRankRetriever.
    Retrieves top_k from vector store via Hybrid Search, reranks to rerank_top_k.
    Supports metadata filtering via search_filter.
    """
    from langchain.retrievers.multi_query import MultiQueryRetriever
    from langchain_openai import ChatOpenAI
    
    vectorstore = get_vector_store()
    
    search_kwargs = {"k": settings.top_k}
    if search_filter:
        search_kwargs["filter"] = search_filter
        
    llm_for_mq = ChatOpenAI(
        temperature=0, 
        model="gpt-4o-mini",
        api_key=settings.openai_api_key
    )
    dense_retriever = MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(search_kwargs=search_kwargs),
        llm=llm_for_mq
    )
    
    try:
        data = vectorstore.get()
        contents = data.get("documents", [])
        metadatas = data.get("metadatas", [])
        
        if contents:
            docs_for_bm25 = [
                Document(page_content=c, metadata=m) 
                for c, m in zip(contents, metadatas)
                if c is not None
            ]
            bm25_retriever = BM25Retriever.from_documents(docs_for_bm25)
            bm25_retriever.k = settings.top_k
            
            ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, dense_retriever], weights=[0.4, 0.6]
            )
            base_retriever = ensemble_retriever
        else:
            base_retriever = dense_retriever
            
    except Exception as e:
        logger.warning(f"Could not initialize BM25 Retriever, using dense only: {e}")
        base_retriever = dense_retriever
    
    compressor = FlashrankRerank(top_n=settings.rerank_top_k)
    return FlashRankRetriever(base_retriever=base_retriever, compressor=compressor)
