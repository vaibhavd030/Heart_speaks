from heart_speaks.config import settings
from heart_speaks.ingest import get_vector_store


def get_reranking_retriever():
    """Returns the base Chroma DB retriever. Reranking removed for compatibility."""
    vectorstore = get_vector_store()
    base_retriever = vectorstore.as_retriever(search_kwargs={"k": settings.rerank_top_k})
    return base_retriever
