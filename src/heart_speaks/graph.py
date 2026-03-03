from collections.abc import Sequence
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger
from openai import OpenAI

from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
import os

from heart_speaks.config import settings
from heart_speaks.models import LLMResponse
from heart_speaks.retriever import get_reranking_retriever

# Enable LLM response caching to save time and API costs
if settings.enable_llm_cache:
    os.makedirs(settings.cache_dir, exist_ok=True)
    set_llm_cache(SQLiteCache(database_path=os.path.join(settings.cache_dir, "llm_cache.db")))


class GraphState(TypedDict):
    """Represents the state of our graph."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: list[str]
    docs: list[dict] # source metadata for citation tracking
    is_safe: bool
    final_response: dict
    metadata_filter: dict | None # optional metadata filters

def check_prompt_injection(state: GraphState):
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
        response = client.moderations.create(input=latest_message)
        is_safe = not response.results[0].flagged
    except Exception as e:
        logger.warning(f"Moderation API check failed, assuming safe to proceed: {e}")
        is_safe = True
        
    return {"is_safe": is_safe}

def route_safety(state: GraphState):
    """Routes to retrieval if safe, else ends the graph."""
    if state.get("is_safe", True):
        return "retrieve"
    logger.warning("Prompt injection detected. Halting.")
    return "unsafe_response"

def unsafe_response(state: GraphState):
    """Returns a canned response for malicious input."""
    return {"final_response": {
        "answer": "I cannot fulfill this request as it violates safety guidelines.",
        "citations": []
    }}

def retrieve(state: GraphState):
    """Retrieves relevant spiritual chunks from the vector store."""
    logger.info("Retrieving context...")
    latest_message = state["messages"][-1].content
    metadata_filter = state.get("metadata_filter")
    
    retriever = get_reranking_retriever(search_filter=metadata_filter)
    docs = retriever.invoke(latest_message)
    
    formatted_context = []
    doc_metadata = []
    for d in docs:
        content = d.page_content
        source = d.metadata.get("source_file", "Unknown PDF")
        page = d.metadata.get("page", 0)
        formatted_context.append(f"[Source: {source}, Page: {page}]\n{content}")
        doc_metadata.append({"source": source, "page": page, "content": content})
        
    return {"context": formatted_context, "docs": doc_metadata}

def generate(state: GraphState):
    """Generates the grounded response using structured outputs."""
    logger.info("Generating response...")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)
    
    # We use the previous messages as conversation history
    history = state["messages"][:-1]
    latest_message = state["messages"][-1].content
    context = "\n\n---\n\n".join(state["context"])
    
    system_prompt = (
        "You are 'Heart Speaks', sharing the pure essence of spiritual messages. "
        "Answer the seeker's question by preserving the exact tone, essence, and original voice of the provided context. "
        "Do not heavily edit, translate, or over-summarize the messages; instead, read from the chunks and share the wisdom "
        "as if reciting the original teachings directly, making sure it relates to the question asked. "
        "Do not hallucinate. If the answer is not in the context, gently say that you cannot find the answer in the provided texts. "
        "You MUST provide citations from the context to back up your guidance, referencing the Source file and Page number. "
        "\n\nContext:\n{context}"
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{history}"),
        ("human", "{question}"),
    ])
    
    chain = prompt | llm.with_structured_output(LLMResponse)
    
    response = chain.invoke({
        "context": context,
        "history": history,
        "question": latest_message
    })
    
    # Return serializable dict form for the final response
    return {"final_response": response.model_dump()}

# Build the Graph
workflow = StateGraph(GraphState)

workflow.add_node("check_prompt_injection", check_prompt_injection)
workflow.add_node("unsafe_response", unsafe_response)
workflow.add_node("retrieve", retrieve)
workflow.add_node("generate", generate)

workflow.add_edge(START, "check_prompt_injection")
workflow.add_conditional_edges("check_prompt_injection", route_safety)
workflow.add_edge("unsafe_response", END)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()
