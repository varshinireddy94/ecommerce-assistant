"""
Main orchestration: user query -> router -> SQL / RAG / Hybrid / Small talk
-> Llama 3.3-70B -> final answer.

Every branch is wrapped so that a failure anywhere (bad/missing ID, no DB
rows, no relevant policy chunk, LLM/API failure) degrades to a clear,
honest fallback message instead of crashing or hallucinating - see
FALLBACKS below and section 7 of the project spec.
"""

from backend.src import llm, rag
from backend.src import router
from backend.src.tools import TOOL_REGISTRY, TOOL_SCHEMAS

CLARIFICATION_MESSAGE = (
    "I'm not totally sure what you're asking. Could you rephrase, or let "
    "me know if you're asking about an order, a product, or a store policy "
    "(returns, refunds, shipping, warranty, cancellations)? If it's about "
    "a specific order, please include the order ID."
)

NO_POLICY_MATCH_MESSAGE = (
    "I couldn't find a policy that covers this exact situation. Could you "
    "rephrase, or would you like me to connect you with human support?"
)

NEEDS_ID_MESSAGE = (
    "I'd need an order ID (or product/customer ID) to look that up - could "
    "you share it? It's usually a long code from your order confirmation."
)

LLM_FAILURE_MESSAGE = (
    "Something went wrong on my end while generating a response. Please "
    "try again in a moment."
)

TOOL_ERROR_MESSAGES = {
    "invalid_order_id": "That doesn't look like a valid order ID - could you double check it?",
    "invalid_product_id": "That doesn't look like a valid product ID - could you double check it?",
    "invalid_customer_id": "That doesn't look like a valid customer ID - could you double check it?",
    "invalid_category": "I didn't recognize that product category - could you rephrase it?",
    "invalid_price_range": "That price range doesn't look valid - could you give it again (e.g. 500 to 2000)?",
    "order_not_found": "I couldn't find an order with that ID. Could you double-check it?",
    "no_items_found": "I couldn't find any items for that order.",
    "product_not_found": "I couldn't find a product with that ID.",
    "no_products_found": "I couldn't find any products matching that search.",
    "customer_not_found_or_no_orders": "I couldn't find any orders for that customer ID.",
}


def _run_tool(user_query: str):
    """
    Resolve a query to a tool call and execute it.
    Returns (data_or_None, error_message_or_None).
    """
    try:
        tool_name, params = llm.select_tool_and_params(user_query, TOOL_SCHEMAS)
    except llm.LLMError:
        return None, LLM_FAILURE_MESSAGE

    if tool_name is None or tool_name not in TOOL_REGISTRY:
        return None, NEEDS_ID_MESSAGE

    try:
        result = TOOL_REGISTRY[tool_name](**params)
    except TypeError:
        # missing/extra params from the LLM's extraction
        return None, NEEDS_ID_MESSAGE
    except Exception:
        return None, LLM_FAILURE_MESSAGE

    if isinstance(result, dict) and "error" in result:
        return None, TOOL_ERROR_MESSAGES.get(result["error"], NEEDS_ID_MESSAGE)

    return result, None


def handle_query(user_query: str):
    """
    Returns a dict:
        {
            "answer": str,
            "route": str,
            "sources": [ {source, distance}, ... ]   # policy sources, if any
            "tool_used": str or None,
        }
    """
    if not user_query or not user_query.strip():
        return {"answer": CLARIFICATION_MESSAGE, "route": "UNCLEAR", "sources": [], "tool_used": None}

    route, confidence = router.classify(user_query)

    # ---------------- SMALL TALK ----------------
    if route == "SMALL_TALK":
        try:
            answer = llm.generate_smalltalk_reply(user_query)
        except llm.LLMError:
            answer = "Hi! I can help with order status, product info, returns, refunds and shipping."
        return {"answer": answer, "route": route, "sources": [], "tool_used": None}

    # ---------------- POLICY ----------------
    if route == "POLICY":
        chunks = rag.search_policy(user_query, k=3)
        if not chunks or not rag.has_relevant_policy(chunks):
            return {"answer": NO_POLICY_MATCH_MESSAGE, "route": route, "sources": [], "tool_used": None}
        try:
            answer = llm.generate_policy_answer(user_query, chunks)
        except llm.LLMError:
            return {"answer": LLM_FAILURE_MESSAGE, "route": route, "sources": [], "tool_used": None}
        return {
            "answer": answer,
            "route": route,
            "sources": [{"source": c["source"], "distance": c["distance"]} for c in chunks],
            "tool_used": None,
        }

    # ---------------- ORDER / PRODUCT (SQL only) ----------------
    if route == "ORDER_PRODUCT":
        data, error = _run_tool(user_query)
        if error:
            return {"answer": error, "route": route, "sources": [], "tool_used": None}
        try:
            answer = llm.generate_data_answer(user_query, data)
        except llm.LLMError:
            return {"answer": LLM_FAILURE_MESSAGE, "route": route, "sources": [], "tool_used": None}
        return {"answer": answer, "route": route, "sources": [], "tool_used": True}

    # ---------------- HYBRID (SQL + RAG) ----------------
    if route == "HYBRID":
        data, error = _run_tool(user_query)
        chunks = rag.search_policy(user_query, k=3)
        relevant_chunks = chunks if rag.has_relevant_policy(chunks) else []

        if error and not relevant_chunks:
            return {"answer": error, "route": route, "sources": [], "tool_used": None}

        try:
            answer = llm.generate_hybrid_answer(
                user_query,
                data if not error else {"error": error},
                relevant_chunks,
            )
        except llm.LLMError:
            return {"answer": LLM_FAILURE_MESSAGE, "route": route, "sources": [], "tool_used": None}

        return {
            "answer": answer,
            "route": route,
            "sources": [{"source": c["source"], "distance": c["distance"]} for c in relevant_chunks],
            "tool_used": True,
        }

    # ---------------- UNCLEAR ----------------
    return {"answer": CLARIFICATION_MESSAGE, "route": "UNCLEAR", "sources": [], "tool_used": None}
