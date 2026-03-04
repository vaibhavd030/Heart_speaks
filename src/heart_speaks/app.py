import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger
from openai import OpenAIError
from pydantic import ValidationError

from heart_speaks.graph import app as rag_app


def main() -> None:
    """Main entry point for the Streamlit application.
    
    Initializes the UI, handles user chat input, invokes the RAG graph,
    and displays the generated answer with citations.
    """
    st.set_page_config(page_title="Heart Speaks RAG", initial_sidebar_state="collapsed")

    # Hide the sidebar completely via CSS
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("Heart Speaks - Spiritual Insights")
    st.caption("Ask questions about the spiritual messages in the knowledge base.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if isinstance(msg, HumanMessage):
            with st.chat_message("user"):
                st.write(msg.content)
        elif isinstance(msg, AIMessage):
            with st.chat_message("assistant"):
                st.write(msg.content)
                
    if user_input := st.chat_input("Ask a question..."):
        with st.chat_message("user"):
            st.write(user_input)
            
        st.session_state.messages.append(HumanMessage(content=user_input))
        
        with st.chat_message("assistant"):
            try:
                import asyncio
                from typing import Any, AsyncGenerator

                async def run_chat() -> dict[str, Any]:
                    inputs = {"messages": st.session_state.messages}
                    final_resp_dict: dict[str, Any] = {}
                    
                    with st.status("Analyzing...", expanded=True) as status_ui:
                        text_ui = st.empty()
                        try:
                            async for event in rag_app.astream_events(inputs, version="v2"):
                                kind = event["event"]
                                name = event.get("name")
                                
                                if kind == "on_chain_start" and name == "check_prompt_injection":
                                    status_ui.write("✅ Checking prompt safety...")
                                elif kind == "on_chain_start" and name == "retrieve":
                                    status_ui.write("🔍 Searching spiritual teachings...")
                                elif kind == "on_chain_start" and name == "generate":
                                    status_ui.write("✨ Distilling wisdom...")
                                    
                                elif kind == "on_parser_stream":
                                    chunk = event["data"]["chunk"]
                                    if isinstance(chunk, dict) and "answer" in chunk:
                                        text_ui.markdown(chunk["answer"])
                                        
                                elif kind == "on_chain_end" and name == "generate":
                                    final_outputs: Any = event["data"].get("output", {})
                                    if isinstance(final_outputs, dict):
                                        final_resp_dict = final_outputs.get("final_response", {})
                        except Exception:
                            logger.exception("Stream error")
                            
                        status_ui.update(label="Response ready", state="complete", expanded=False)
                        
                    return final_resp_dict

                final_resp = asyncio.run(run_chat())
                
                answer = final_resp.get("answer", "I could not generate an answer.")
                citations = final_resp.get("citations", [])
                
                import time
                from typing import Generator
                def stream_data(text: str) -> Generator[str, None, None]:
                    for word in text.split(" "):
                        yield word + " "
                        time.sleep(0.04)

                st.write_stream(stream_data(answer))
                
                if citations:
                    st.markdown("<br><p style='font-size: 0.85em; color: #888888; margin-bottom: 5px;'><strong>Sources:</strong></p>", unsafe_allow_html=True)
                    for c in citations:
                        st.markdown(f"<p style='font-size: 0.8em; color: #888888; margin-top: 0px; margin-bottom: 2px;'>- <i>{c['source']}, Page {c['page']}</i>: \"{c['quote']}\"</p>", unsafe_allow_html=True)
                        
                st.session_state.messages.append(AIMessage(content=answer))
            except (OpenAIError, ValidationError, ValueError, RuntimeError) as e:
                logger.exception("Error during app execution.")
                st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
