import pytest
from unittest.mock import patch, MagicMock
from typing import List

from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document

from heart_speaks.retriever import get_reranking_retriever, FlashRankRetriever

class FakeRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        return []

@patch('heart_speaks.retriever.get_vector_store')
@patch('langchain_community.document_compressors.flashrank_rerank.Ranker')
@patch('heart_speaks.retriever.FlashrankRerank')
def test_get_reranking_retriever(mock_flashrank, mock_ranker, mock_get_store):
    """Test that the reranking retriever pipeline is built correctly."""
    mock_store = MagicMock()
    fake_retriever = FakeRetriever()
    mock_store.as_retriever.return_value = fake_retriever
    mock_get_store.return_value = mock_store
    
    retriever = get_reranking_retriever()
    
    # Assert base retriever was requested with correct kwargs from Chroma
    mock_store.as_retriever.assert_called_once()
    
    # Assert Flashrank compressor was instantiated
    mock_flashrank.assert_called_once()
    
    from langchain.retrievers.multi_query import MultiQueryRetriever
    
    # Assert custom FlashRankRetriever was instantiated correctly
    assert isinstance(retriever, FlashRankRetriever)
    
    # Since we mocked get() to return nothing/fail, it falls back to dense MultiQueryRetriever
    assert isinstance(retriever.base_retriever, MultiQueryRetriever)
    assert retriever.base_retriever.retriever == fake_retriever
    
    assert retriever.compressor == mock_flashrank.return_value
