import os
import joblib
import random
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from qdrant_code.initialize_groq import init_groq, api_keys
# Constants
COLLECTION_NAME = 'enron_emails'
QDRANT_DB = os.path.join(os.path.dirname(__file__), "qdrant_db")
# Prompts
prompt = ChatPromptTemplate.from_template(
    "Answer question based only on the context below.\n\n{context}\n\nQuestion: {input}"
)
document_prompt = PromptTemplate.from_template(
    "From: {sender}\nTo: {recipient}\nDate: {date}\nSubject: {subject}\nEntities: {entities}\nFilename: {filename}\n\n{page_content}"
)
detailed_prompt = PromptTemplate.from_template(
    """You are a Qdrant vector database query expert.
The vector schema includes a passage (1 sentence with 1 before and after for context)
and metadata fields: date, location, person, action, finance, legal, event, product, organization.
Rewrite the users question to optimize it for semantic vector search using this structure.
Emphasize key concepts and align with relevant metadata when possible.
Only return the improved query WITHOUT any explanation. Make sure to specify that you should use the retriever to answer the question based on the data on the similarity search results.
User question: "{query}"
Qdrant query:"""
)
_, llm = init_groq(model_name="llama-3.3-70b-versatile")
llm.groq_api_key = random.choice(api_keys)
documentChain = create_stuff_documents_chain(llm, prompt=prompt, document_prompt=document_prompt)
def query_qdrant(query_text: str) -> str:
    # Load documents and initialize qdrant client only when called
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
    try:
        retriever = qdrant.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "lambda_mult": 0.2}
        )
        chain = create_retrieval_chain(
            retriever,
            documentChain
        )
        result = chain.invoke({"input": query_text})
        filenames = [doc.metadata.get('filename', 'No filename found') for doc in result.get('context', [])]
        return result.get("answer", "No answer generated."), filenames
    finally:
        # manually close the underlying Qdrant client
        qdrant.client.close()