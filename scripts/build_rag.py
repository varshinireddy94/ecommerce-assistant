from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# Configuration
# --------------------------------------------------

POLICY_DIR = Path("policies")
CHROMA_DIR = "data/chroma_db"

CHUNK_SIZE = 150
CHUNK_OVERLAP = 30


# --------------------------------------------------
# Load policy documents
# --------------------------------------------------

def load_documents():

    documents = []

    for file_path in sorted(POLICY_DIR.rglob("*.txt")):

        # Ignore the old policy files directly inside policies/
        if file_path.parent == POLICY_DIR:
            continue

        text = file_path.read_text(
            encoding="utf-8"
        ).strip()

        documents.append({
            "text": text,
            "source": str(
                file_path.relative_to(POLICY_DIR)
            )
        })

    return documents


# --------------------------------------------------
# Split documents into chunks
# --------------------------------------------------

def create_chunks(documents):

    chunks = []

    for document in documents:

        words = document["text"].split()

        start = 0

        while start < len(words):

            end = start + CHUNK_SIZE

            chunk_words = words[start:end]

            chunk_text = " ".join(chunk_words)

            chunks.append({
                "text": chunk_text,
                "source": document["source"]
            })

            # Move forward while keeping overlap
            start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


# --------------------------------------------------
# Main
# --------------------------------------------------

print("=" * 60)
print("BUILDING POLICY RAG")
print("=" * 60)


print("\nLoading policy documents...")

documents = load_documents()

print(f"Documents loaded: {len(documents)}")


print("\nCreating chunks...")

chunks = create_chunks(documents)

print(f"Chunks created: {len(chunks)}")


# --------------------------------------------------
# Load embedding model
# --------------------------------------------------

print("\nLoading embedding model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded.")


# --------------------------------------------------
# Create ChromaDB
# --------------------------------------------------

print("\nCreating ChromaDB...")

client = chromadb.PersistentClient(
    path=CHROMA_DIR
)


# Delete existing collection if present
try:
    client.delete_collection(
        name="store_policies"
    )
except Exception:
    pass


collection = client.create_collection(
    name="store_policies",
    metadata={
        "description": "ShopSphere e-commerce policies"
    }
)


# --------------------------------------------------
# Generate embeddings
# --------------------------------------------------

print("\nGenerating embeddings...")

texts = [
    chunk["text"]
    for chunk in chunks
]

embeddings = model.encode(
    texts,
    show_progress_bar=True
).tolist()


# --------------------------------------------------
# Store in ChromaDB
# --------------------------------------------------

print("\nStoring vectors in ChromaDB...")

collection.add(
    ids=[
        f"policy_{i}"
        for i in range(len(chunks))
    ],
    documents=texts,
    embeddings=embeddings,
    metadatas=[
        {
            "source": chunk["source"]
        }
        for chunk in chunks
    ]
)


print("\n" + "=" * 60)
print("RAG DATABASE CREATED SUCCESSFULLY")
print("=" * 60)

print(f"Documents : {len(documents)}")
print(f"Chunks    : {len(chunks)}")
print(f"Vectors   : {len(embeddings)}")
print(f"Location  : {CHROMA_DIR}")