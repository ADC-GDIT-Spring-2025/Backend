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
COLLECTION_NAME = "enron_emails"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_PATH = "qdrant_db"

embedding_model = HuggingFaceEmbeddings(
    model_name="intfloat/e5-base-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

docslist = joblib.load("docslist.pkl")

qdrant = Qdrant.from_documents(
    docslist,
    embedding_model,
    path=QDRANT_PATH,
    collection_name=COLLECTION_NAME,
)

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

document_chain = create_stuff_documents_chain(
    llm=None,  # set dynamically per request
    prompt=prompt,
    document_prompt=document_prompt
)

retrieval_chain = create_retrieval_chain(retriever, document_chain)

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

    # Bind LLM into the chain
    chain = create_retrieval_chain(
        retriever,
        create_stuff_documents_chain(llm, prompt=prompt, document_prompt=document_prompt)
    )

    result = chain.invoke({"input": query_text})
    return jsonify({"answer": result.get("answer", "No answer generated.")})


if __name__ == "__main__":
    app.run(debug=True)