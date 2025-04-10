from flask import Flask, request, jsonify
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import joblib
import random

app = Flask(__name__)
COLLECTION_NAME = "my_documents"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_PATH = "C:\DEV\Datasets\EnronEmailDataset\qdrant_db"

embedding_model = HuggingFaceEmbeddings(
    model_name="intfloat/e5-base-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

docslist = joblib.load("C:\DEV\Datasets\EnronEmailDataset\data\docslist.pkl")

# qdrant = Qdrant.from_documents(
#     docslist,
#     embedding_model,
#     path=QDRANT_PATH,
#     collection_name=COLLECTION_NAME,
# )
qdrant = Qdrant.from_existing_collection(embedding_model, path=QDRANT_PATH, collection_name=COLLECTION_NAME)
prompt = ChatPromptTemplate.from_template(
    "Answer question based only on the context below.\n\n{context}\n\nQuestion: {input}"
)

document_prompt = PromptTemplate.from_template(
    "From: {sender}\nTo: {recipient}\nDate: {date}\nSubject: {subject}\nEntities: {entities}\n\n{page_content}"
)

retriever = qdrant.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 10, "lambda_mult": 0.2}
)

detailed_prompt = PromptTemplate.from_template(
    """You are a Qdrant vector database query expert. 
The vector schema includes a passage (1 sentence with 1 before and after for context) 
and metadata fields: date, location, person, action, finance, legal, event, product, organization.
Rewrite the user’s question to optimize it for semantic vector search using this structure. 
Emphasize key concepts and align with relevant metadata when possible. 
Only return the improved query WITHOUT any explanation.

User question: "{query}"
Qdrant query:"""
)

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    query_text = data.get("query")

    if not query_text:
        return jsonify({"error": "Missing query field"}), 400

    # Dynamically import LLM and API key here
    from initialize_groq import init_groq, api_keys
    _, llm = init_groq(model_name="llama-3.3-70b-versatile")
    llm.groq_api_key = random.choice(api_keys)

    optimized_query = llm.invoke(detailed_prompt.format(query=query_text)).content.strip()

    chain = create_retrieval_chain(
        retriever,
        create_stuff_documents_chain(llm, prompt=prompt, document_prompt=document_prompt)
    )

    result = chain.invoke({"input": optimized_query})
    return jsonify({"answer": result.get("answer", "No answer generated.")})


if __name__ == "__main__":
    app.run()