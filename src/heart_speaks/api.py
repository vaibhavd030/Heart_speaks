import json
from typing import Any

from fastapi import FastAPI, Depends
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
    allow_origins=[
        "https://sage-frontend-34833003999.europe-west2.run.app",
        "https://sage-frontend-qxhmc5knkq-nw.a.run.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.staticfiles import StaticFiles
from heart_speaks.config import settings

from heart_speaks.auth import (
    ApproveRequest,
    LoginRequest,
    RegisterRequest,
    approve_or_reject_user,
    delete_user,
    ensure_admin_exists,
    get_current_user,
    list_all_users,
    list_pending_users,
    login_user,
    register_user,
    require_admin,
    suspend_user,
)
from heart_speaks.repository import (
    delete_bookmark,
    delete_chat_log,
    get_all_chat_logs,
    get_bookmarks,
    get_user_chat_logs,
    get_progress,
    get_reader_sequence,
    get_stats,
    save_chat_log,
    search_messages,
    update_progress,
    upsert_bookmark,
)

from heart_speaks.repository import init_db

@app.on_event("startup")
def startup_event():
    ensure_admin_exists()
    init_db()

# Mount real storage location for PDFs
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", settings.data_dir.replace("./", "")))
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")

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

# --- Public Auth Endpoints (no token required) ---

@app.post("/auth/register")
def register(req: RegisterRequest):
    return register_user(req)

@app.post("/auth/login")
def login(req: LoginRequest):
    return login_user(req)

# --- Admin Endpoints ---

@app.get("/admin/users/pending")
def get_pending_users(admin=Depends(require_admin)):
    return list_pending_users()

@app.post("/admin/users/approve")
def approve_user(req: ApproveRequest, admin=Depends(require_admin)):
    return approve_or_reject_user(req)

@app.get("/admin/users/all")
def get_all_registered_users(admin=Depends(require_admin)):
    return list_all_users()

@app.post("/admin/users/suspend")
def suspend_user_endpoint(user_id: str, admin=Depends(require_admin)):
    return suspend_user(user_id)

@app.delete("/admin/users/{user_id}")
def delete_user_endpoint(user_id: str, admin=Depends(require_admin)):
    return delete_user(user_id)

@app.get("/admin/logs")
def get_chat_history(limit: int = 100, offset: int = 0, admin=Depends(require_admin)):
    return get_all_chat_logs(limit, offset)


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, user=Depends(get_current_user)) -> ChatResponse:
    session_key = user["user_id"]
    session_history = sessions.get(
        session_key,
        [
            AIMessage(
                content="Dear Soul,\n\nI am here to guide you through the whispers of the brighter world. How may I be of service to your heart today?"
            )
        ],
    )

    user_msg = HumanMessage(content=request.message)
    session_history.append(user_msg)

    inputs = {"messages": session_history, "metadata_filter": request.search_filter}

    result = rag_app.invoke(inputs)  # type: ignore
    final_resp = result.get("final_response", {})

    answer = final_resp.get("answer", "No answer generated.")
    sources = final_resp.get("sources", [])

    session_history.append(AIMessage(content=answer))
    sessions[session_key] = session_history

    # Log interaction
    try:
        save_chat_log(
            user_id=user["user_id"],
            session_id=request.session_id,
            question=request.message,
            response=answer,
            metadata=json.dumps({"sources_count": len(sources)}),
            first_name=user.get("first_name", ""),
            last_name=user.get("last_name", ""),
            email=user.get("email", ""),
            abhyasi_id=user.get("abhyasi_id", ""),
        )
    except Exception as e:
        print(f"Failed to save chat log: {e}")

    return ChatResponse(answer=answer, sources=sources)


@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest, user=Depends(get_current_user)) -> StreamingResponse:
    session_key = user["user_id"]
    session_history = sessions.get(
        session_key,
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
                    if "final_generation" in tags:
                        chunk_content = event["data"]["chunk"].content
                        if chunk_content:
                            final_answer += chunk_content
                            yield f"data: {json.dumps({'type': 'content', 'text': chunk_content})}\n\n"

                elif kind == "on_chain_end" and event["name"] == "LangGraph":
                    final_resp = event["data"]["output"].get("final_response", {})
                    final_sources = final_resp.get("sources", [])
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'sources', 'sources': final_sources})}\n\n"

        session_history.append(AIMessage(content=final_answer))
        sessions[session_key] = session_history

        # Log interaction
        try:
            save_chat_log(
                user_id=user["user_id"],
                session_id=request.session_id,
                question=request.message,
                response=final_answer,
                metadata=json.dumps({"streamed": True, "sources_count": len(final_sources)}),
                first_name=user.get("first_name", ""),
                last_name=user.get("last_name", ""),
                email=user.get("email", ""),
                abhyasi_id=user.get("abhyasi_id", ""),
            )
        except Exception as e:
            print(f"Failed to save streamed chat log: {e}")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/chat/logs")
def get_user_logs(user=Depends(get_current_user)) -> list[dict[str, Any]]:
    """Returns chat logs for the authenticated user."""
    return get_user_chat_logs(user["user_id"])


@app.delete("/chat/logs/{log_id}")
def remove_chat_log(log_id: str, user=Depends(get_current_user)) -> dict[str, str]:
    """Allows a user to delete their own chat log."""
    from fastapi import HTTPException
    success = delete_chat_log(log_id, user_id=user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Log not found or not owned by user")
    return {"status": "success"}


@app.get("/stats")
def get_dashboard_stats(user=Depends(get_current_user)) -> dict[str, Any]:
    return get_stats()


@app.get("/messages")
def get_message_list(query: str = "", page: int = 1, limit: int = 50, user=Depends(get_current_user)) -> dict[str, Any]:
    return search_messages(query, page, limit)


@app.get("/reader/messages")
def get_reader_messages(user=Depends(get_current_user)) -> list[dict[str, Any]]:
    return get_reader_sequence()


@app.get("/reader/progress")
def get_reader_progress(user=Depends(get_current_user)) -> dict[str, Any]:
    progress = get_progress(user["user_id"])
    return progress or {
        "user_id": user["user_id"],
        "last_read_source_file": None,
        "messages_read": 0,
    }


@app.post("/reader/progress")
def update_reader_progress(request: ProgressRequest, user=Depends(get_current_user)) -> dict[str, str]:
    update_progress(user["user_id"], request.source_file, request.messages_read)
    return {"status": "success"}


@app.get("/reader/bookmarks")
def get_reader_bookmarks(user=Depends(get_current_user)) -> list[dict[str, Any]]:
    return get_bookmarks(user["user_id"])


@app.post("/reader/bookmarks")
def save_reader_bookmark(request: BookmarkRequest, user=Depends(get_current_user)) -> dict[str, str]:
    upsert_bookmark(user["user_id"], request.source_file, request.notes)
    return {"status": "success"}


@app.delete("/reader/bookmarks/{source_file:path}")
def remove_reader_bookmark(source_file: str, user=Depends(get_current_user)) -> dict[str, str]:
    delete_bookmark(user["user_id"], source_file)
    return {"status": "success"}


@app.delete("/admin/logs/{log_id}")
def admin_remove_chat_log(log_id: str, admin=Depends(require_admin)) -> dict[str, str]:
    """Allows an admin to delete any chat log."""
    from fastapi import HTTPException
    success = delete_chat_log(log_id)
    if not success:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"status": "success"}
