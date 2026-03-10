import os
from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from heart_speaks.config import settings
from heart_speaks.retriever import get_reranking_retriever

# Enable LLM response caching to save time and API costs
if settings.enable_llm_cache:
    os.makedirs(settings.cache_dir, exist_ok=True)
    set_llm_cache(
        SQLiteCache(database_path=os.path.join(settings.cache_dir, "llm_cache.db"))
    )


from typing import Any


class GraphState(TypedDict):
    """Represents the state of our graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: list[str]
    docs: list[dict[str, Any]]  # source metadata for citation tracking
    is_safe: bool
    final_response: dict[str, Any]
    intent: str
    metadata_filter: dict[str, Any] | None  # optional metadata filters


class IntentClassification(BaseModel):
    intent: str = Field(
        description="The intent of the user's question. Must be one of: SEEKING_WISDOM, FACTUAL_REFERENCE, EMOTIONAL_SUPPORT, EXPLORATION, GREETING"
    )


def classify_intent(state: GraphState) -> dict[str, str]:
    """Classifies the user's message intent."""
    logger.info("Classifying intent...")
    latest_message = state["messages"][-1].content
    from pydantic import SecretStr

    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key=SecretStr(settings.openai_api_key), temperature=0
    )
    structured_llm = llm.with_structured_output(IntentClassification)
    try:
        res = structured_llm.invoke(
            f"Classify the intent of the following spiritual question. If it is a greeting or small talk, classify as GREETING:\n\n{latest_message}"
        )
        if isinstance(res, IntentClassification) and res.intent in [
            "SEEKING_WISDOM",
            "FACTUAL_REFERENCE",
            "EMOTIONAL_SUPPORT",
            "EXPLORATION",
            "GREETING",
        ]:
            intent = res.intent
        else:
            intent = "SEEKING_WISDOM"
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        intent = "SEEKING_WISDOM"

    logger.info(f"Classified intent: {intent}")
    return {"intent": intent}


def route_intent(state: GraphState) -> str:
    """Routes greetings directly to generation, skipping retrieval."""
    if state.get("intent") == "GREETING":
        return "generate"
    return "retrieve"


def check_prompt_injection(state: GraphState) -> dict[str, bool]:
    """Analyzes the latest user message for potential prompt injections or malicious intent using OpenAI Moderation API.

    Args:
        state (GraphState): The current state of the workflow containing conversation history.

    Returns:
        dict: Updated state with 'is_safe' boolean.
    """
    logger.info("Checking for prompt injections via Moderation API...")
    latest_message = state["messages"][-1].content

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        # Using the standard moderations endpoint which is free and very fast
        msg_str = str(latest_message)
        response = client.moderations.create(input=msg_str)
        is_safe = not response.results[0].flagged
    except Exception as e:
        logger.warning(f"Moderation API check failed, assuming safe to proceed: {e}")
        is_safe = True

    return {"is_safe": is_safe}


def route_safety(state: GraphState) -> str:
    """Routes to classification if safe, else ends the graph."""
    if state.get("is_safe", True):
        return "classify_intent"
    logger.warning("Prompt injection detected. Halting.")
    return "unsafe_response"


def unsafe_response(state: GraphState) -> dict[str, dict[str, Any]]:
    """Returns a canned response for malicious input."""
    return {
        "final_response": {
            "answer": "I cannot fulfill this request as it violates safety guidelines.",
            "citations": [],
        }
    }


def retrieve(state: GraphState) -> dict[str, list[str] | list[dict[str, Any]]]:
    """Retrieves relevant spiritual chunks from the vector store."""
    logger.info("Retrieving context...")
    latest_message = state["messages"][-1].content
    metadata_filter = state.get("metadata_filter")

    retriever = get_reranking_retriever(search_filter=metadata_filter)
    docs = retriever.invoke(str(latest_message))

    formatted_context = []
    doc_metadata = []
    for d in docs:
        content = d.page_content
        source = d.metadata.get("source_file", "Unknown PDF")
        date = d.metadata.get("date", "Unknown Date")
        page = d.metadata.get("page", 0)

        author = d.metadata.get("personality", "")
        if not author or author == "Unknown":
            from heart_speaks.repository import get_message_by_source

            repo = get_message_by_source(source)
            author = repo.get("author", "Unknown") if repo else "Unknown"

        # Extract precise date and time from filename (e.g., Friday_February_1_1991_12_00_AM_Babuji Maharaj.pdf)
        formatted_date_time = date
        try:
            name_parts = source.split("/")[-1].replace(".pdf", "").split("_")
            if len(name_parts) >= 7:
                month, day, year, hour, minute, ampm = name_parts[1], name_parts[2], name_parts[3], name_parts[4], name_parts[5], name_parts[6].lower()
                time_str = f"{hour}{ampm}" if minute == "00" else f"{hour}:{minute}{ampm}"
                formatted_date_time = f"{month} {day}, {year} {time_str}"
        except Exception:
            pass

        formatted_context.append(
            f"Content: {content}\nSource: {source}\nAuthor: {author}\nDate: {formatted_date_time}\n---"
        )
        doc_metadata.append({"source": source, "page": page, "content": content})

    return {"context": formatted_context, "docs": doc_metadata}


def generate(state: GraphState) -> dict[str, dict[str, Any]]:
    """Generates the grounded response using structured outputs and enriches with SQLite full-text."""
    logger.info("Generating response...")

    # We allow streaming API configuration natively
    from pydantic import SecretStr

    llm = ChatOpenAI(
        model=settings.generation_model,
        temperature=0,
        streaming=True,
        api_key=SecretStr(settings.openai_api_key),
    )

    # We use the previous messages as conversation history
    history = state["messages"][:-1]
    latest_message = state["messages"][-1].content
    context = "\n\n---\n\n".join(state.get("context", []))
    intent = state.get("intent", "SEEKING_WISDOM")

    # --- Grounding block (shared by all non-GREETING intents) ---
    GROUNDING_RULES = (
        "You have access to sacred spiritual texts as context below. "
        "Base your response ONLY on this context. If the answer is not present, "
        "say so with kindness. "
        "When referencing a source, you MUST always end each teaching or paragraph with a citation "
        "in this exact format: (Author, Month Day, Year Time). For example: (Babuji, May 12, 2004 8am) "
        "or (Unknown, November 9, 2016 10:30am). Do not use the word 'Whispers' in the citation. "
        "Never show raw filenames or page numbers.\n\n"
    )

    # --- Persona prompts (these go AFTER the context, so they are the last thing the LLM reads) ---
    intent_prompts = {
        "SEEKING_WISDOM": (
            "You are 'Heart Speaks', sharing the pure essence of spiritual messages. "
            "Answer the seeker's question by preserving the exact tone, essence, and original voice of the provided context. "
            "Do not heavily edit, translate, or over-summarize the messages. "
            "Give each distinct theme or teaching its own paragraph with a bold subheading, "
            "and end each teaching with its elegant citation. Do not use numbered lists. "
            "Make sure the response directly relates to the question asked."
        ),
        "FACTUAL_REFERENCE": (
            "You are 'Heart Speaks', a knowledgeable scholar of spiritual teachings. "
            "Respond directly and precisely. Lead with the exact teaching and its citation. "
            "If the answer spans multiple sources, give each its own paragraph with a "
            "short bold subheading and citation. Do not use numbered lists."
        ),
        "EMOTIONAL_SUPPORT": (
            "You are 'Heart Speaks', a compassionate spiritual guide. "
            "Respond with deep compassion first, validating and acknowledging the seeker's feeling. "
            "Write as a warm letter from someone who truly cares. "
            "Gently introduce relevant teachings as comfort, not prescription. "
            "If drawing on multiple teachings, let each one form its own paragraph "
            "with a gentle bold subheading and a naturally woven citation at the end. "
            "Do not use numbered lists or bullet points. "
            "Never tell the seeker what to do. Invite them to sit with the wisdom."
        ),
        "EXPLORATION": (
            "You are 'Heart Speaks', a patient spiritual teacher. "
            "Provide a structured overview drawing from multiple teachings. "
            "Give each theme or teaching its own paragraph with a bold subheading, "
            "ending with its citation. Do not use numbered lists. "
            "Offer to go deeper into specific aspects if the seeker wishes."
        ),
        "GREETING": (
            "You are 'Heart Speaks', a gentle spiritual companion. "
            "The user has just greeted you or made small talk. "
            "Respond with a warm, brief greeting in character. "
            "Do not use headings, bullet points, or citations. Keep it conversational."
        ),
    }

    if intent == "GREETING":
        system_prompt = intent_prompts["GREETING"]
    else:
        persona_voice = intent_prompts.get(intent, intent_prompts["SEEKING_WISDOM"])
        system_prompt = GROUNDING_RULES + "Context:\n{context}\n\n" + persona_voice

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{history}"),
            ("human", "{question}"),
        ]
    )

    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "context": context,
                "history": history,
                "question": latest_message,
            },
            config={"tags": ["final_generation"]},
        )
        logger.info(f"Raw LLM Response: {response.content}")
        answer_text = response.content
    except Exception as e:
        logger.error(f"Error during LLM Generation: {str(e)}")
        # Provide a fallback error response
        answer_text = (
            "I apologize, but I encountered an error formulating your response."
        )

    # Enrich all retrieved docs to serve as citations for the UI
    from heart_speaks.repository import get_message_by_source

    unique_sources = {}
    for doc in state.get("docs", []):
        src = doc.get("source", "")
        if src and src not in unique_sources:
            unique_sources[src] = doc.get("content", "")

    rich_sources = []
    for src, preview_text in unique_sources.items():
        try:
            repo_data = get_message_by_source(src)
        except Exception as e:
            logger.warning(f"Repository lookup failed {e}")
            repo_data = None

        if repo_data:
            rich_sources.append(
                {
                    "author": repo_data.get("author", "Unknown"),
                    "date": str(repo_data.get("date", "Unknown")),
                    "citation": src,
                    "preview": repo_data.get("preview", preview_text),
                    "full_text": repo_data.get("full_text", preview_text),
                }
            )
        else:
            rich_sources.append(
                {
                    "author": "Unknown",
                    "date": "Unknown",
                    "citation": src,
                    "preview": preview_text,
                    "full_text": preview_text,
                }
            )

    # Re-pack the payload to match Next.js ChatInterface
    final_payload = {"answer": answer_text, "sources": rich_sources}

    # Return serializable dict form for the final response
    return {"final_response": final_payload}


# Build the Graph
workflow = StateGraph(GraphState)

workflow.add_node("check_prompt_injection", check_prompt_injection)
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("unsafe_response", unsafe_response)
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

workflow.add_edge(START, "check_prompt_injection")
workflow.add_conditional_edges("check_prompt_injection", route_safety)
workflow.add_edge("unsafe_response", END)
workflow.add_conditional_edges("classify_intent", route_intent)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
