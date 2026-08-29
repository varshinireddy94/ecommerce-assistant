"""
ShopSphere Support Assistant - Streamlit UI.

Run with:  streamlit run app.py

Flow:  Streamlit -> Router -> SQL / RAG / Hybrid / Small talk -> Llama 3.3-70B -> Response
"""

import streamlit as st

from backend.src.pipeline import handle_query

st.set_page_config(page_title="ShopSphere Support Assistant", page_icon="🛍️")

st.title("🛍️ ShopSphere Support Assistant")
st.caption(
    "Ask about an order, a product, or a store policy (returns, refunds, "
    "shipping, warranty, cancellations). For order questions, include the "
    "order ID."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("Sources used"):
                for source in msg["sources"]:
                    st.markdown(f"- `{source['source']}` (distance: {source['distance']:.3f})")
        if msg["role"] == "assistant" and msg.get("route"):
            st.caption(f"Route: {msg['route']}")

# Chat input
user_input = st.chat_input("How can I help you today?")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = handle_query(user_input)
        st.markdown(result["answer"])
        if result["sources"]:
            with st.expander("Sources used"):
                for source in result["sources"]:
                    st.markdown(f"- `{source['source']}` (distance: {source['distance']:.3f})")
        st.caption(f"Route: {result['route']}")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
            "route": result["route"],
        }
    )

with st.sidebar:
    st.header("About")
    st.write(
        "This assistant answers order/product questions from our database, "
        "answers policy questions from our knowledge base, and combines "
        "both for questions like *'Can I return the product from order "
        "X?'*."
    )
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()
