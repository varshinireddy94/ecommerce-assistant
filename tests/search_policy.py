import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_DIR = "data/chroma_db"


print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(
    path=CHROMA_DIR
)

collection = client.get_collection(
    name="store_policies"
)


def search_policy(query, k=3):

    query_embedding = model.encode(
        [query]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k
    )

    print("\n" + "=" * 70)
    print("QUERY:")
    print(query)
    print("=" * 70)

    for i, document in enumerate(
        results["documents"][0]
    ):

        source = results["metadatas"][0][i]["source"]

        distance = results["distances"][0][i]

        print(f"\nRESULT {i + 1}")
        print(f"Source   : {source}")
        print(f"Distance : {distance:.4f}")
        print("-" * 70)
        print(document)


if __name__ == "__main__":

    queries = [
        "My laptop arrived damaged. Can I return it?",
        "How long do I have to return a product?",
        "My order is late. What should I do?",
        "My refund was approved but I haven't received the money.",
        "Can I cancel my order after it has been shipped?"
    ]

    for query in queries:
        search_policy(query)