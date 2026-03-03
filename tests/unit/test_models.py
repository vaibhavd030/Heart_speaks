from pydantic import ValidationError
import pytest

from heart_speaks.models import Citation, LLMResponse


def test_citation_model_valid():
    """Test valid instantiation of Citation model."""
    citation = Citation(source="doc.pdf", page=1, quote="test quote")
    assert citation.source == "doc.pdf"
    assert citation.page == 1
    assert citation.quote == "test quote"

def test_citation_model_invalid():
    """Test invalid instantiation of Citation model."""
    with pytest.raises(ValidationError):
        Citation(source="doc.pdf", page="one", quote="test quote")

def test_llm_response_model_valid():
    """Test valid instantiation of LLMResponse model."""
    citation = Citation(source="doc.pdf", page=1, quote="test quote")
    response = LLMResponse(answer="test answer", citations=[citation])
    assert response.answer == "test answer"
    assert len(response.citations) == 1
    assert response.citations[0].source == "doc.pdf"
