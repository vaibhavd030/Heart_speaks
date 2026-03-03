from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from heart_speaks.graph import app as rag_app

app = FastAPI(
    title="Heart Speaks API",
    description="API for the Heart Speaks Spiritual RAG Chatbot",
    version="0.1.0"
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user_session"
    search_filter: dict | None = None

class CitationModel(BaseModel):
    source: str
    page: int
    quote: str

class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationModel]

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint for answering spiritual queries.
    Supports optional metadata filtering via search_filter (e.g. {"source_file": "my_pdf.pdf"}).
    """
    inputs = {
        "messages": [HumanMessage(content=request.message)],
        "metadata_filter": request.search_filter
    }
    result = rag_app.invoke(inputs)
    final_resp = result.get("final_response", {})
    
    return ChatResponse(
        answer=final_resp.get("answer", "No answer generated."),
        citations=final_resp.get("citations", [])
    )

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
