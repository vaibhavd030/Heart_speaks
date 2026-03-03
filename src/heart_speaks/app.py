import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from heart_speaks.graph import app as rag_app


from openai import OpenAIError
from pydantic import ValidationError

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
                import time
                def stream_data(text):
                    for word in text.split(" "):
                        yield word + " "
                        time.sleep(0.04)

                inputs = {"messages": st.session_state.messages}
                
                # Stream the state updates to provide UI feedback
                final_state = None
                with st.status("Analyzing...", expanded=True) as status:
                    for output in rag_app.stream(inputs):
                        for node_name, state_update in output.items():
                            if node_name == "check_prompt_injection":
                                st.write("✅ Checking prompt safety...")
                            elif node_name == "retrieve":
                                st.write("🔍 Searching spiritual teachings...")
                            elif node_name == "generate":
                                st.write("✨ Distilling wisdom...")
                            elif node_name == "unsafe_response":
                                st.write("⚠️ Safety boundary triggered.")
                            final_state = state_update
                    status.update(label="Response ready", state="complete", expanded=False)
                
                final_resp = final_state.get("final_response", {}) if final_state else {}
                answer = final_resp.get("answer", "I could not generate an answer.")
                citations = final_resp.get("citations", [])
                
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
