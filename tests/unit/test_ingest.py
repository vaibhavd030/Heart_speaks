from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from heart_speaks.ingest import ingest_data, parse_whisper_filename


def test_parse_whisper_filename() -> None:
    """Test extraction of date and author from structured filenames."""
    # Valid format
    date, author = parse_whisper_filename(
        "Friday_February_1_1991_7_16_AM_Babuji Maharaj.pdf"
    )
    assert date == "1991-02-01"
    assert author == "Babuji Maharaj"

    # Invalid or short name
    date, author = parse_whisper_filename("unknown_file.pdf")
    assert date == "Unknown"
    assert author == "Spiritual Guide"


@patch("heart_speaks.repository.upsert_message")
@patch("heart_speaks.ingest.get_vector_store")
@patch("heart_speaks.ingest.glob")
@patch("heart_speaks.ingest.PyPDFLoader")
def test_ingest_data(
    mock_loader: MagicMock,
    mock_glob: MagicMock,
    mock_get_store: MagicMock,
    mock_upsert: MagicMock,
) -> None:
    """Test the ingestion pipeline's core loops."""
    # Mock finding files
    mock_glob.glob.return_value = ["fake_dir/fake1.pdf"]

    # Mock reading documents
    mock_doc = Document(
        page_content="some spiritual text", metadata={"source": "fake_dir/fake1.pdf"}
    )

    mock_loader_instance = MagicMock()
    mock_loader_instance.load.return_value = [mock_doc]
    mock_loader.return_value = mock_loader_instance

    # Mock vector store persistence
    mock_store = MagicMock()
    mock_get_store.return_value = mock_store

    # Run
    with patch("os.path.exists", return_value=True):
        ingest_data("fake_dir")

    # Validation
    mock_loader.assert_called_once_with("fake_dir/fake1.pdf")
    mock_store.add_documents.assert_called_once()


@patch("heart_speaks.repository.upsert_message")
@patch("heart_speaks.ingest.get_vector_store")
@patch("heart_speaks.ingest.glob")
@patch("heart_speaks.ingest.PyPDFLoader")
def test_ingest_data_exception_handling(
    mock_loader: MagicMock,
    mock_glob: MagicMock,
    mock_get_store: MagicMock,
    mock_upsert: MagicMock,
) -> None:
    """Test that ingestion continues if one document fails to load."""
    mock_glob.glob.return_value = ["fake_dir/good.pdf", "fake_dir/bad.pdf"]

    def side_effect(path: str) -> MagicMock:
        if "bad" in path:
            raise ValueError("Corrupted PDF")
        mock_instance = MagicMock()
        mock_instance.load.return_value = [
            Document(page_content="good text", metadata={"source": path})
        ]
        return mock_instance

    mock_loader.side_effect = side_effect

    mock_store = MagicMock()
    mock_get_store.return_value = mock_store

    with patch("os.path.exists", return_value=True):
        ingest_data("fake_dir")

    # Called twice
    assert mock_loader.call_count == 2
    # Only good text added
    mock_store.add_documents.assert_called_once()
