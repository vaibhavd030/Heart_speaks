import json
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from heart_speaks.graph import app as rag_app

app = FastAPI(
    title="Heart Speaks API",
    description="API for the Heart Speaks Spiritual RAG Chatbot",
    version="0.2.0",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory session store
sessions: dict[str, Any] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_user_session"
    search_filter: dict[str, Any] | None = None


class SourceModel(BaseModel):
    author: str
    date: str
    citation: str
    preview: str
    full_text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceModel]


class ProgressRequest(BaseModel):
    source_file: str
    messages_read: int


class BookmarkRequest(BaseModel):
    source_file: str
    notes: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint for answering spiritual queries.
    Maintains conversation history via session_id.
    Supports optional metadata filtering.
    """
    # Retrieve or initialize session history
    session_history = sessions.get(
        request.session_id,
        [
            AIMessage(
                content="Dear Soul,\n\nI am here to guide you through the whispers of the brighter world. How may I be of service to your heart today?"
            )
        ],
    )

    # Append new user message
    user_msg = HumanMessage(content=request.message)
    session_history.append(user_msg)

    inputs = {"messages": session_history, "metadata_filter": request.search_filter}

    result = rag_app.invoke(inputs)  # type: ignore
    final_resp = result.get("final_response", {})

    answer = final_resp.get("answer", "No answer generated.")
    sources = final_resp.get("sources", [])

    # Append the AI's response to history so subsequent turns have context
    session_history.append(AIMessage(content=answer))

    # Save back to store
    sessions[request.session_id] = session_history

    return ChatResponse(answer=answer, sources=sources)


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest) -> StreamingResponse:
    """
    Streaming Chat endpoint for answering spiritual queries.
    Uses Server-Sent Events (SSE) to stream text chunks and finally sources.
    """
    session_history = sessions.get(
        request.session_id,
        [
            AIMessage(
                content="Dear Soul,\n\nI am here to guide you through the whispers of the brighter world. How may I be of service to your heart today?"
            )
        ],
    )

    user_msg = HumanMessage(content=request.message)
    session_history.append(user_msg)

    inputs = {"messages": session_history, "metadata_filter": request.search_filter}

    from typing import AsyncGenerator
    async def event_stream() -> AsyncGenerator[str, None]:
        final_answer = ""
        final_sources = []

        try:
            async for event in rag_app.astream_events(inputs, version="v2"):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    tags = event.get("tags", [])
                    # Only stream chunks from the final generation call
                    if "final_generation" in tags:
                        chunk_content = event["data"]["chunk"].content
                        if chunk_content:
                            final_answer += chunk_content
                            yield f"data: {json.dumps({'type': 'content', 'text': chunk_content})}\n\n"

                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    # Collect the final rich sources assembled by the graph
                    final_resp = event["data"]["output"].get("final_response", {})
                    final_sources = final_resp.get("sources", [])
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'sources', 'sources': final_sources})}\n\n"

        session_history.append(AIMessage(content=final_answer))
        sessions[request.session_id] = session_history

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/stats")
def get_dashboard_stats() -> dict[str, Any]:
    """Returns EDA statistics for the dashboard."""
    from heart_speaks.repository import get_stats

    return get_stats()


@app.get("/messages")
def get_message_list(query: str = "", page: int = 1, limit: int = 50) -> dict[str, Any]:
    """Returns a paginated list of messages from the repository."""
    from heart_speaks.repository import search_messages

    return search_messages(query, page, limit)


@app.get("/reader/messages")
def get_reader_messages() -> list[dict[str, Any]]:
    """Returns all messages ordered by date for the reader sequence."""
    from heart_speaks.repository import get_reader_sequence

    return get_reader_sequence()


@app.get("/reader/progress")
def get_reader_progress() -> dict[str, Any]:
    """Returns the user's reading progress."""
    from heart_speaks.repository import get_progress

    progress = get_progress("default_user")
    return progress or {
        "user_id": "default_user",
        "last_read_source_file": None,
        "messages_read": 0,
    }


@app.post("/reader/progress")
def update_reader_progress(request: ProgressRequest) -> dict[str, str]:
    """Updates the user's reading progress."""
    from heart_speaks.repository import update_progress

    update_progress("default_user", request.source_file, request.messages_read)
    return {"status": "success"}


@app.get("/reader/bookmarks")
def get_reader_bookmarks() -> list[dict[str, Any]]:
    """Returns all bookmarks ordered by message date."""
    from heart_speaks.repository import get_bookmarks

    return get_bookmarks()


@app.post("/reader/bookmarks")
def save_reader_bookmark(request: BookmarkRequest) -> dict[str, str]:
    """Saves or updates a bookmark with notes."""
    from heart_speaks.repository import upsert_bookmark

    upsert_bookmark(request.source_file, request.notes)
    return {"status": "success"}


@app.delete("/reader/bookmarks/{source_file}")
def remove_reader_bookmark(source_file: str) -> dict[str, str]:
    """Removes a bookmark."""
    from heart_speaks.repository import delete_bookmark

    delete_bookmark(source_file)
    return {"status": "success"}
