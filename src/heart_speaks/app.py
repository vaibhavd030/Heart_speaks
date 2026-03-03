import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from heart_speaks.graph import app as rag_app


def main():
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
        
        with st.chat_message("assistant"), st.spinner("Connecting with the teachings..."):
            try:
                # Invoke Graph
                inputs = {"messages": st.session_state.messages}
                result = rag_app.invoke(inputs)
                
                final_resp = result.get("final_response", {})
                answer = final_resp.get("answer", "I could not generate an answer.")
                citations = final_resp.get("citations", [])
                
                st.write(answer)
                if citations:
                    st.markdown("<br><p style='font-size: 0.85em; color: #888888; margin-bottom: 5px;'><strong>Sources:</strong></p>", unsafe_allow_html=True)
                    for c in citations:
                        st.markdown(f"<p style='font-size: 0.8em; color: #888888; margin-top: 0px; margin-bottom: 2px;'>- <i>{c['source']}, Page {c['page']}</i>: \"{c['quote']}\"</p>", unsafe_allow_html=True)
                        
                st.session_state.messages.append(AIMessage(content=answer))
            except Exception as e:
                logger.exception("Error during app execution.")
                st.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
