
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Citation for a provided answer.
    
    Attributes:
        source (str): The name of the PDF source document
        page (int): The page number where the information was found
        quote (str): Exact quote from the text that supports the answer
    """
    source: str = Field(..., description="The name of the PDF source document")
    page: int = Field(..., description="The page number where the information was found")
    quote: str = Field(..., description="Exact quote from the text that supports the answer")

class LLMResponse(BaseModel):
    """Structured response from the LLM containing the answer and citations.
    
    Attributes:
        answer (str): The detailed answer to the user's question
        citations (list[Citation]): List of citations verifying the answer
    """
    answer: str = Field(..., description="The detailed answer to the user's question")
    citations: list[Citation] = Field(..., description="List of citations verifying the answer")
