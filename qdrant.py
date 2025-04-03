from flask import Flask, request, jsonify
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Distance,
    VectorParams,
    HnswConfig
)
import numpy as np

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
    """Insert precomputed embeddings into Qdrant"""
    try:
        embeddings = np.load("embeddings (1).npy")
        num_vectors, dim = embeddings.shape

        points = [
            PointStruct(id=i, vector=embeddings[i].tolist())
            for i in range(num_vectors)
        ]

        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        return jsonify({"message": f"Inserted {num_vectors} embeddings into Qdrant"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/search/<int:vector_id>", methods=["GET"])
def search(vector_id):
    """Search for the closest vectors using HNSW"""

    try:
        # Fetch the vector corresponding to the given vector_id using 'retrieve'
        result = qdrant.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[vector_id],
            with_vectors = True
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
            query_vector=query_vector,  # Use the fetched vector here
            limit=5,
            with_vectors = True
        )

        formatted_hits = [{"id": hit.id, "score": hit.score} for hit in hits]

        return jsonify({"results": f"{formatted_hits}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500






    """
    data = request.json
    query_vector = data.get("vector")

    if query_vector is None:
        return jsonify({"error": "Missing query vector"}), 400

    search_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=5,
        with_payload=True,
        params={"hnsw_ef": 50}
    )

    return jsonify({"results": [hit.id for hit in search_results]})
    """

@app.route("/get_vector/<int:vector_id>", methods=["GET"])
def get_vector(vector_id):
    """Retrieve a vector by its ID"""
    try:
        result = qdrant.retrieve(collection_name=COLLECTION_NAME, ids=[vector_id])
        print(f"Retrieved result for ID {vector_id}: {result}")
        if not result:
            return jsonify({"error": "Vector not found"}), 404
        return jsonify({"vector": result[0].vector})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_all_vectors", methods=["GET"])
def get_all_vectors():
    """Retrieve all stored vectors"""
    try:
        vectors = qdrant.scroll(collection_name=COLLECTION_NAME, limit=100)
        return jsonify({"vectors": [{"id": v.id, "vector": v.vector} for v in vectors]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    try:
        result = client.retrieve(collection_name="your_collection", ids=[])
        if result:
            # Iterate over the list of results and access each id and vector
            vectors = [{'id': point.id, 'vector': point.vector} for point in result]
            return jsonify({"vectors": vectors})
        else:
            return jsonify({"error": "No vectors found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list_vectors", methods=["GET"])
def list_ids():
    """Get all vector IDs in the Qdrant collection."""
    try:
        # Perform the search or scroll with a limit
        search_results = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            with_vectors = True
        )
        
        # Assuming search_results contains 'matches' or similar field
        vectors = [record.vector for record in search_results[0]]  # Adjust based on the structure
        
        return jsonify({"vectors": vectors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    app.run(debug=True)

