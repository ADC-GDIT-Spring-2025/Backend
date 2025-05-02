import os
import joblib
import random
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from qdrant_code.initialize_groq import init_groq, api_keys

# --- Constants ---
COLLECTION_NAME = "enron_emails"
QDRANT_DB = os.path.join(os.path.dirname(__file__), "qdrant_db")

# --- Prompt for final LLM answer ---
chat_prompt = ChatPromptTemplate.from_template(
    "\n\n{context}\n\nQuestion: {input}"
)

# --- Prompt for formatting retrieved documents ---
document_prompt = PromptTemplate.from_template(
    "From: {sender}\nTo: {recipient}\nDate: {date}\nSubject: {subject}\nEntities: {entities}\n\n{page_content}"
)

# --- Prompt for rewriting user query into a search-optimized one ---
detailed_prompt = PromptTemplate.from_template(
    """You are a Qdrant vector database query expert. 
The vector schema includes a passage (1 sentence with 1 before and after for context) 
and metadata fields: date, location, person, action, finance, legal, event, product, organization.
Rewrite the user's question to optimize it for semantic vector search using this structure. 
Emphasize key concepts and align with relevant metadata when possible. 
Only return the improved query WITHOUT any explanation.

User question: "{query}"
Qdrant query:"""
)

def query_qdrant(query_text: str) -> str:
    """Handles the full Qdrant + LLM pipeline from query -> rewrite -> retrieval -> answer generation."""

    # Initialize embedding model
    embedding_model = HuggingFaceEmbeddings(
        model_name="intfloat/e5-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # Load existing Qdrant vector store
    qdrant = Qdrant.from_existing_collection(
        embedding_model,
        path=QDRANT_DB,
        collection_name=COLLECTION_NAME,
    )

    try:
        # Initialize the retriever with MMR search
        retriever = qdrant.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "lambda_mult": 0.2}
        )

        # Dynamically load LLM and randomly assign an API key
        _, llm = init_groq(model_name="llama-3.3-70b-versatile")
        llm.groq_api_key = random.choice(api_keys)

        # Step 1: Rewrite the user's query to improve semantic retrieval
        optimized_query = llm.invoke(detailed_prompt.format(query=query_text)).content.strip()

        # Step 2: Retrieve relevant documents using optimized query
        retrieved_docs = retriever.invoke(optimized_query)

        filenames = [doc.metadata.get('filename', 'No filename found') for doc in retrieved_docs]

        # Step 3: Format retrieved documents into a single context string
        formatted_context = "\n\n".join([
            document_prompt.format(**doc.metadata, page_content=doc.page_content)
            for doc in retrieved_docs
        ])

        # Step 4: Construct the final prompt using context and original user query
        final_prompt = chat_prompt.format(context=formatted_context, input=query_text)

        # Step 5: Generate answer using LLM
        response = llm.invoke(final_prompt)
        return response.content.strip()

    finally:
        # Ensure Qdrant client closes after use
        qdrant.client.close()











