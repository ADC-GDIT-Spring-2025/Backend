from flask import Flask, request, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Distance,
    VectorParams,
    HnswConfig
)
import numpy as np
import json

app = Flask(__name__)

qdrant = QdrantClient("localhost", port=6333)

COLLECTION_NAME = "my_vectors"

if qdrant.collection_exists("my_vectors"):
    qdrant.delete_collection("my_vectors")

qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),  
    hnsw_config={"m": 16, "ef_construct": 100, "full_scan_threshold": 10000}
)

@app.route("/insert_embeddings", methods=["POST"])
def insert_embeddings():
    """
    Loading vectors and metadata, the insert them into Qdrant.
    Utilizing: 
    - embeddings.npy shape (n,768)
    - metadata.json: list of n dicts with relevant fields ('text, 'sender', etc.)
    - embeddings.npy : shape (n, 768)
    """
    try:
        embeddings = np.load("embeddings.npy")
        with open("metadata.json", "r") as f:
            payloads = json.load(f)
        num_vectors, dim = embeddings.shape
        if len(payloads) != num_vectors:
            return jsonify({"error": "Mismatch between embeddings and metadata lengths"}), 400

        points = [
            PointStruct(
                id=i,
                vector=embeddings[i].tolist(),
                payload=payloads[i]
            )
            for i in range(num_vectors)
        ]

        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        return jsonify({"message": f"Inserted {num_vectors} vectors with payloads into Qdrant."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search/<int:vector_id>", methods=["GET"])
def search_by_id(vector_id):
    """
    Retrieve a vector by ID and run similarity search with it.
    Returns top-5 hits and their payloads.
    """
    try:
        result = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[vector_id],
            with_vectors=True
        )

        # Check if the result is empty or doesn't contain the expected data
        if not result or len(result) == 0:
            return jsonify({"error": f"Vector with id {vector_id} not found."}), 404

        # Log the raw result to inspect it
        print(f"Retrieved result for vector {vector_id}: {result}")

        # Access the vector from the result (adjust based on the actual structure of the Record)
        query_vector = result[0].vector  # Assuming the vector is inside the 'vector' attribute

        # Check if the vector is None or not in the correct format
        if query_vector is None or not isinstance(query_vector, list):
            return jsonify({"error": f"Vector with id {vector_id} is not in a valid format."}), 400

        # Log the vector format
        print(f"Query vector for search: {query_vector}")

        # Perform the search using the query_vector
        hits = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector, # Use the fetched vector here
            limit=5,
            with_payload=True
        )

        results = [
            {"id": hit.id, "score": hit.score, "payload": hit.payload}
            for hit in hits
        ]
        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/search_vector", methods=["POST"])
def search_by_vector():
    """
    Accepts a vector in the request body, performs similarity search, and returns payloads.
    """
    try:
        query_vector = request.json.get("vector")
        if not query_vector or not isinstance(query_vector, list):
            return jsonify({"error": "Missing or invalid vector"}), 400

        hits = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=5,
            with_payload=True
        )

        results = [
            {"id": hit.id, "score": hit.score, "payload": hit.payload}
            for hit in hits
        ]
        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get_vector/<int:vector_id>", methods=["GET"])
def get_vector(vector_id):
    """Fetch a single vector and its payload."""
    try:
        result = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[vector_id],
            with_vectors=True,
            with_payload=True
        )
        if not result:
            return jsonify({"error": "Vector not found"}), 404

        return jsonify({
            "id": result[0].id,
            "vector": result[0].vector,
            "payload": result[0].payload
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/list_vectors", methods=["GET"])
def list_vectors():
    """Scroll and list payloads of the first 100 vectors (no vectors returned)."""
    try:
        scroll_result = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            with_payload=True,
            with_vectors=False
        )

        vectors = [
            {"id": point.id, "payload": point.payload}
            for point in scroll_result[0]
        ]
        return jsonify({"vectors": vectors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    app.run(debug=True)