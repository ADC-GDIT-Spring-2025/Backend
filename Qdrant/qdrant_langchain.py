import os
import joblib
import random
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

# Constants
COLLECTION_NAME = "my_documents"
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "data_for_qdrant", "docslist.pkl")
QDRANT_DB = os.path.join(os.path.dirname(__file__), "qdrant_db")

# Prompts
prompt = ChatPromptTemplate.from_template(
    "Answer question based only on the context below.\n\n{context}\n\nQuestion: {input}"
)

document_prompt = PromptTemplate.from_template(
    "From: {sender}\nTo: {recipient}\nDate: {date}\nSubject: {subject}\nEntities: {entities}\n\n{page_content}"
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

def query_qdrant(query_text: str) -> str:
    # Load documents and initialize qdrant client only when called
    docs_path = os.path.join(os.path.dirname(__file__), "data_for_qdrant", "docslist.pkl")
    docslist = joblib.load(docs_path)

    embedding_model = HuggingFaceEmbeddings(
        model_name="intfloat/e5-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    qdrant = Qdrant.from_existing_collection(
        embedding_model,
        path=QDRANT_DB,
        collection_name=COLLECTION_NAME,
    )

    retriever = qdrant.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10, "lambda_mult": 0.2}
    )

    # Dynamically import LLM and API key here
    from Qdrant.initialize_groq import init_groq, api_keys
    _, llm = init_groq(model_name="llama-3.3-70b-versatile")
    llm.groq_api_key = random.choice(api_keys)

    optimized_query = llm.invoke(detailed_prompt.format(query=query_text)).content.strip()

    chain = create_retrieval_chain(
        retriever,
        create_stuff_documents_chain(llm, prompt=prompt, document_prompt=document_prompt)
    )

    result = chain.invoke({"input": optimized_query})
    return result.get("answer", "No answer generated.")
