"""
Clean, importable policy-retrieval function.

This replaces the print-only version in search_policy.py at the project
root (that file is left in place for manual/CLI debugging, but the app
and pipeline import from here).
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "data" / "chroma_db")
COLLECTION_NAME = "store_policies"

# A distance above this means the closest chunk still isn't a good match
# for the question - used to trigger the "no relevant policy found" fallback.
MAX_RELEVANT_DISTANCE = 1.1

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(name=COLLECTION_NAME)
    return _collection


def search_policy(query: str, k: int = 3):
    """
    Return the top-k relevant policy chunks for `query` as a list of dicts:
        {"text": ..., "source": ..., "distance": ...}
    Returns [] if the collection is empty or nothing relevant is found.
    """
    if not query or not query.strip():
        return []

    model = _get_model()
    collection = _get_collection()

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks = []
    for text, meta, distance in zip(documents, metadatas, distances):
        chunks.append(
            {
                "text": text,
                "source": meta.get("source", "unknown"),
                "distance": distance,
            }
        )
    return chunks


def has_relevant_policy(chunks) -> bool:
    """True if at least one retrieved chunk is close enough to trust."""
    return any(c["distance"] <= MAX_RELEVANT_DISTANCE for c in chunks)
