"""
All LLM calls go through this module. The model used is Llama 3.3 70B
served by Groq.

The LLM is used for exactly four things (per the project spec):
  1. Picking a tool + extracting parameters for ORDER_PRODUCT / HYBRID queries
     (via native function-calling - the LLM never writes SQL).
  2. Answering POLICY questions from retrieved policy chunks only.
  3. Combining SQL results + policy chunks into one answer for HYBRID queries.
  4. Small talk replies.

Every function here can raise LLMError - callers (pipeline.py) are expected
to catch it and fall back to a friendly error message instead of crashing.
"""

import json
import os

from groq import Groq

MODEL_NAME = "openai/gpt-oss-120b"

_client = None


class LLMError(Exception):
    """Raised whenever the Groq API call fails or returns something unusable."""


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise LLMError(
                "GROQ_API_KEY is not set. Add it to your environment or a .env file."
            )
        _client = Groq(api_key=api_key)
    return _client


def _chat(messages, tools=None, tool_choice=None, temperature=0.2):
    client = _get_client()
    try:
        kwargs = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message
    except Exception as exc:  # network errors, rate limits, bad responses, etc.
        raise LLMError(f"LLM request failed: {exc}") from exc


# --------------------------------------------------------------------------
# 1. Tool + parameter selection (ORDER_PRODUCT / SQL side of HYBRID)
# --------------------------------------------------------------------------
def select_tool_and_params(user_query: str, tool_schemas: list):
    """
    Ask the LLM to pick exactly one predefined tool and its parameters
    for the given query. Returns (tool_name, params_dict) or (None, None)
    if the model couldn't confidently pick one (e.g. missing order ID).
    """
    system_prompt = (
        "You are a routing layer for an e-commerce support system. "
        "Given a customer message, call exactly ONE of the provided tools "
        "with the correct parameters extracted from the message. "
        "Only extract an ID if it is explicitly present in the message - "
        "never invent or guess an order_id, product_id, or customer_id. "
        "If no tool clearly applies, or a required ID is missing, do not "
        "call any tool."
    )

    message = _chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        tools=tool_schemas,
        tool_choice="auto",
    )

    tool_calls = getattr(message, "tool_calls", None)
    if not tool_calls:
        return None, None

    call = tool_calls[0]
    tool_name = call.function.name
    try:
        params = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        return None, None

    return tool_name, params


# --------------------------------------------------------------------------
# 2. Policy-only answer generation
# --------------------------------------------------------------------------
def generate_policy_answer(user_query: str, policy_chunks: list):
    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in policy_chunks
    )

    system_prompt = (
        "You are ShopSphere's customer support assistant. Answer the "
        "customer's question using ONLY the policy context provided below. "
        "If the context does not contain enough information to answer "
        "confidently, say so plainly and suggest the customer contact "
        "human support - do not guess or make up policy details.\n\n"
        f"POLICY CONTEXT:\n{context}"
    )

    message = _chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
    )
    return message.content


# --------------------------------------------------------------------------
# 3. Hybrid answer generation (SQL data + policy context)
# --------------------------------------------------------------------------
def generate_hybrid_answer(user_query: str, sql_data: dict, policy_chunks: list):
    context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in policy_chunks
    )

    system_prompt = (
        "You are ShopSphere's customer support assistant. You have two "
        "kinds of information to work with:\n\n"
        f"ORDER/PRODUCT DATA (from our database):\n{json.dumps(sql_data, indent=2)}\n\n"
        f"POLICY CONTEXT (from our policy documents):\n{context}\n\n"
        "Combine both to answer the customer's question. Apply the policy "
        "rules to the specific order/product data given. If the data shows "
        "an error (e.g. order not found) or the policy context doesn't "
        "cover this case, say so plainly instead of guessing."
    )

    message = _chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
    )
    return message.content


def generate_data_answer(user_query: str, sql_data: dict):
    """Pure SQL-data answer (ORDER_PRODUCT route) - reuses the hybrid
    generator with no policy context so wording/tone stay consistent."""
    return generate_hybrid_answer(user_query, sql_data, [])


# --------------------------------------------------------------------------
# 4. Small talk
# --------------------------------------------------------------------------
def generate_smalltalk_reply(user_query: str):
    system_prompt = (
        "You are ShopSphere's friendly customer support assistant. Reply "
        "briefly and warmly to this small-talk message, and remind the "
        "customer you can help with order status, product info, returns, "
        "refunds, shipping and other store policies."
    )
    message = _chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]
    )
    return message.content
