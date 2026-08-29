"""
Semantic intent router.

Classifies a user message into one of:
    POLICY        - pure policy / rules question ("what is the return policy?")
    ORDER_PRODUCT - needs order/customer/product data from SQL
    HYBRID        - needs BOTH SQL data and policy knowledge
    SMALL_TALK    - greetings / chit-chat
    UNCLEAR       - confidence too low to route safely -> ask for clarification

Approach: embed a small set of labeled example utterances per class with
all-MiniLM-L6-v2, then classify a new query by its cosine similarity to
those examples (k-nearest-neighbor style, not a trained classifier - this
keeps the router fast, dependency-free, and easy to extend by just adding
more examples below).
"""

from sentence_transformers import SentenceTransformer, util

CONFIDENCE_THRESHOLD = 0.42  # below this -> UNCLEAR
TOP_K_NEIGHBORS = 3  # average the top-k nearest example scores per class

EXAMPLES = {
    "POLICY": [
        "What is your return policy?",
        "How long do I have to return an item?",
        "Can I get a refund?",
        "What is the warranty on electronics?",
        "How does the refund process work?",
        "Can I cancel my order?",
        "What happens if my order is late?",
        "Do you offer free shipping?",
        "What is your exchange policy?",
        "How many days for a refund to reach my account?",
        "What payment methods do you support for refunds?",
        "Is there a warranty on appliances?",
        "What's the policy on damaged items?",
        "Can I return furniture after opening the box?",
        "What's your policy for beauty products returns?",
    ],
    "ORDER_PRODUCT": [
        "Where is my order?",
        "What is the status of order 12345?",
        "Show me products under 1000 rupees.",
        "What's in my order?",
        "How much did I pay for my order?",
        "When will my order be delivered?",
        "Show me electronics between 500 and 2000.",
        "What did I order last time?",
        "List all my orders.",
        "Who placed order abc123?",
        "What's the price of this product?",
        "Search for toys under 300.",
        "Give me the delivery details for my order.",
        "How many items are in order 98765?",
        "What products are in the furniture category?",
    ],
    "HYBRID": [
        "Can I return the product from my order?",
        "Is my order eligible for a refund?",
        "Can I cancel order 12345?",
        "My order arrived late, what can I do about it?",
        "Is the item in my order still under warranty?",
        "Can I exchange the product I ordered?",
        "My order is damaged, can I get a refund for it?",
        "Is this order past the return window?",
        "Can I return the electronics I bought in this order?",
        "What is the refund process for my specific order?",
    ],
    "SMALL_TALK": [
        "Hello",
        "Hi there",
        "Good morning",
        "How are you?",
        "Thanks!",
        "Thank you for your help",
        "Bye",
        "Who are you?",
        "What can you help me with?",
        "Are you a real person?",
    ],
}

_model = None
_example_embeddings = None  # {label: tensor}


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_example_embeddings():
    global _example_embeddings
    if _example_embeddings is None:
        model = _get_model()
        _example_embeddings = {
            label: model.encode(utterances, convert_to_tensor=True)
            for label, utterances in EXAMPLES.items()
        }
    return _example_embeddings


def classify(query: str):
    """
    Returns (label, confidence) where label is one of
    POLICY / ORDER_PRODUCT / HYBRID / SMALL_TALK / UNCLEAR.
    """
    if not query or not query.strip():
        return "UNCLEAR", 0.0

    model = _get_model()
    example_embeddings = _get_example_embeddings()

    query_embedding = model.encode(query, convert_to_tensor=True)

    scores = {}
    for label, embeddings in example_embeddings.items():
        similarities = util.cos_sim(query_embedding, embeddings)[0]
        top_k = min(TOP_K_NEIGHBORS, len(similarities))
        top_scores = similarities.topk(top_k).values
        scores[label] = float(top_scores.mean())

    best_label = max(scores, key=scores.get)
    best_score = scores[best_label]

    if best_score < CONFIDENCE_THRESHOLD:
        return "UNCLEAR", best_score

    return best_label, best_score
