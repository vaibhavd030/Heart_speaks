import os
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from heart_speaks.ingest import extract_datetime_from_filename, ingest_data


def test_extract_datetime_from_filename():
    """Test extraction of date from filenames."""
    assert extract_datetime_from_filename("Discourse_2023-05-12.pdf") == "2023-05-12"
    assert extract_datetime_from_filename("2020-01-01_talk.pdf") == "2020-01-01"
    assert extract_datetime_from_filename("unknown_file.pdf") == "Unknown"

@patch('heart_speaks.ingest.get_vector_store')
@patch('heart_speaks.ingest.glob')
@patch('heart_speaks.ingest.PyPDFLoader')
def test_ingest_data(mock_loader, mock_glob, mock_get_store):
    """Test the ingestion pipeline's core loops."""
    # Mock finding files
    mock_glob.glob.return_value = ["fake_dir/fake1.pdf"]
    
    # Mock reading documents
    mock_doc = Document(page_content="some spiritual text", metadata={"source": "fake_dir/fake1.pdf"})
    
    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_loader.return_value = mock_loader_instance
    
    # Mock vector store persistence
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    
    # Run
    with patch('os.path.exists', return_value=True):
        ingest_data("fake_dir")
        
    # Validation
    mock_loader.assert_called_once_with("fake_dir/fake1.pdf")
    mock_store.add_documents.assert_called_once()

@patch('heart_speaks.ingest.get_vector_store')
@patch('heart_speaks.ingest.glob')
@patch('heart_speaks.ingest.PyPDFLoader')
def test_ingest_data_exception_handling(mock_loader, mock_glob, mock_get_store):
    """Test that ingestion continues if one document fails to load."""
    mock_glob.glob.return_value = ["fake_dir/good.pdf", "fake_dir/bad.pdf"]
    
    def side_effect(path):
        if "bad" in path:
            raise ValueError("Corrupted PDF")
        mock_instance = MagicMock()
        mock_instance.load.return_value = [Document(page_content="good text", metadata={"source": path})]
        return mock_instance
        
    mock_loader.side_effect = side_effect
    
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store
    
    with patch('os.path.exists', return_value=True):
        ingest_data("fake_dir")
        
    # Called twice
    assert mock_loader.call_count == 2
    # Only good text added
    mock_store.add_documents.assert_called_once()
