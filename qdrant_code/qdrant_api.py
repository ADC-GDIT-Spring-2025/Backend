from flask import Flask, request, jsonify
from flask_cors import CORS
from qdrant_code.qdrant_langchain import query_qdrant

app = Flask(__name__)
CORS(app)

@app.route("/qdrant", methods=["POST"])
def handle_qdrant_query():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()

    if not prompt:
        print("Missing Prompt")
        return jsonify({"error": "Missing prompt"}), 400

    try:
        answer, filenames = query_qdrant(prompt)
        print("RESULTS FROM QDRANT:")
        print(answer, filenames)
        return jsonify({"answer": answer, "filenames": filenames})
    except Exception as e:
        print(f"error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5003, debug=True)