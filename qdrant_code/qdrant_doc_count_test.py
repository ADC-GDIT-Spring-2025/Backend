from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings

# Load the embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="intfloat/e5-base-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

# Load the existing Qdrant collection
qdrant = Qdrant.from_existing_collection(
    embedding=embedding_model,
    path="qdrant_db",
    collection_name="enron_emails",
)

# Access the internal QdrantClient instance directly
client = qdrant.client

# Count points in the collection
response = client.count(collection_name="enron_emails")
print(" Docs in Qdrant:", response.count)
