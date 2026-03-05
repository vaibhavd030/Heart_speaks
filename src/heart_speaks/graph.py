import os
from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_community.cache import SQLiteCache
from langchain_core.globals import set_llm_cache
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field

from heart_speaks.config import settings
from heart_speaks.models import LLMResponse
from heart_speaks.retriever import get_reranking_retriever

# Enable LLM response caching to save time and API costs
if settings.enable_llm_cache:
    os.makedirs(settings.cache_dir, exist_ok=True)
    set_llm_cache(SQLiteCache(database_path=os.path.join(settings.cache_dir, "llm_cache.db")))


from typing import Any

class GraphState(TypedDict):
    """Represents the state of our graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: list[str]
    docs: list[dict[str, Any]] # source metadata for citation tracking
    is_safe: bool
    final_response: dict[str, Any]
    intent: str
    metadata_filter: dict[str, Any] | None # optional metadata filters

class IntentClassification(BaseModel):
    intent: str = Field(description="The intent of the user's question. Must be one of: SEEKING_WISDOM, FACTUAL_REFERENCE, EMOTIONAL_SUPPORT, EXPLORATION, GREETING")

def classify_intent(state: GraphState) -> dict[str, str]:
    """Classifies the user's message intent."""
    logger.info("Classifying intent...")
    latest_message = state["messages"][-1].content
    from pydantic import SecretStr
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=SecretStr(settings.openai_api_key), temperature=0)
    structured_llm = llm.with_structured_output(IntentClassification)
    try:
        res = structured_llm.invoke(f"Classify the intent of the following spiritual question. If it is a greeting or small talk, classify as GREETING:\n\n{latest_message}")
        if isinstance(res, IntentClassification) and res.intent in ["SEEKING_WISDOM", "FACTUAL_REFERENCE", "EMOTIONAL_SUPPORT", "EXPLORATION", "GREETING"]:
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
    return {"final_response": {
        "answer": "I cannot fulfill this request as it violates safety guidelines.",
        "citations": []
    }}

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
        formatted_context.append(f"[Source File: {source}, Date: {date}]\n{content}")
        doc_metadata.append({"source": source, "page": page, "content": content})
        
    return {"context": formatted_context, "docs": doc_metadata}

def generate(state: GraphState) -> dict[str, dict[str, Any]]:
    """Generates the grounded response using structured outputs and enriches with SQLite full-text."""
    logger.info("Generating response...")
    
    # We allow streaming API configuration natively 
    from pydantic import SecretStr
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0, 
        streaming=True, 
        api_key=SecretStr(settings.openai_api_key)
    )
    
    # We use the previous messages as conversation history
    history = state["messages"][:-1]
    latest_message = state["messages"][-1].content
    context = "\n\n---\n\n".join(state.get("context", []))
    intent = state.get("intent", "SEEKING_WISDOM")
    
    intent_prompts = {
        "SEEKING_WISDOM": (
            "You are 'Heart Speaks', a gentle spiritual companion who has deeply absorbed the wisdom of these sacred messages. "
            "Structure your response thoughtfully: "
            "1. Start with a warm, conversational discussion of the topic. "
            "2. If the topic is complex, organize your response clearly using ONLY **Bold Subheadings** (e.g., **Understanding the Process**) to separate different insights or themes. DO NOT use numbered lists. If simple, weave wisdom naturally without headings. "
            "3. Weave your explanations, ending with organic, elegant citations (e.g., 'As expressed in Whispers...'). "
            "4. Conclude with a warm, gentle synthesis of the wisdom. "
            "Your tone should be warm, unhurried, and reverent. Invite the seeker to sit with the wisdom."
        ),
        "FACTUAL_REFERENCE": (
            "You are 'Heart Speaks', a knowledgeable scholar of spiritual teachings. "
            "Respond directly and precisely. Lead with the exact quote and citation to answer the requested fact. "
            "If your response is long, format it cleanly using **Bold Subheadings**. DO NOT use numbered lists."
        ),
        "EMOTIONAL_SUPPORT": (
            "You are 'Heart Speaks', a compassionate spiritual guide. "
            "Respond with deep compassion first, validating and acknowledging their current feeling. "
            "Gently introduce relevant teachings as a comfort, not a prescription. Avoid telling them what to do. "
            "Organize your thoughts clearly using ONLY **Bold Subheadings** (e.g., **Finding Comfort**) if the response has multiple parts. DO NOT use numbered lists."
        ),
        "EXPLORATION": (
            "You are 'Heart Speaks', a patient spiritual teacher. "
            "Provide a structured overview drawing from multiple teachings. Organize thoughts logically using **Bold Subheadings**. DO NOT use numbered lists. "
            "Offer to go deeper into specific aspects if they wish."
        ),
        "GREETING": (
            "You are 'Heart Speaks', a gentle spiritual companion. "
            "The user has just greeted you or made small talk. Respond with a warm, brief greeting in character "
            "(e.g., 'Pranam. How may I guide your heart today?' or simply 'Hello, dear soul.'). "
            "Do not use headings, bullet points, or any citations. Keep it conversational."
        )
    }
    
    base_prompt = intent_prompts.get(intent, intent_prompts["SEEKING_WISDOM"])
    
    if intent == "GREETING":
        system_prompt = base_prompt
    else:
        system_prompt = (
            f"{base_prompt}\n\n"
            "Do not hallucinate. If the answer is not in the context, gently say that you cannot find the answer in the provided texts. "
            "You MUST provide citations from the context to back up your guidance. "
            "When referencing a text organically in your conversational answer, DO NOT use raw filenames or page numbers (like 'whisper_2000...pdf' or 'Page: 0'). "
            "Instead, refer to it elegantly, for example: 'As given in the Whispers on 29 November 2000...' or '(Whispers, 29 Nov 2000)'. "
            "\n\nContext:\n{context}\n\n"
        )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{history}"),
        ("human", "{question}"),
    ])
    
    chain = prompt | llm
    
    try:
        response = chain.invoke(
            {
                "context": context,
                "history": history,
                "question": latest_message,
            },
            config={"tags": ["final_generation"]}
        )
        logger.info(f"Raw LLM Response: {response.content}")
        answer_text = response.content
    except Exception as e:
        logger.error(f"Error during LLM Generation: {str(e)}")
        # Provide a fallback error response
        answer_text = "I apologize, but I encountered an error formulating your response."

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
            rich_sources.append({
                "author": repo_data.get("author", "Unknown"),
                "date": str(repo_data.get("date", "Unknown")),
                "citation": src,
                "preview": repo_data.get("preview", preview_text),
                "full_text": repo_data.get("full_text", preview_text)
            })
        else:
             rich_sources.append({
                "author": "Unknown",
                "date": "Unknown",
                "citation": src,
                "preview": preview_text,
                "full_text": preview_text
            })
    
    # Re-pack the payload to match Next.js ChatInterface
    final_payload = {
        "answer": answer_text,
        "sources": rich_sources
    }
    
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
