import os
import random
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from initialize_groq import init_groq, api_keys

# --- Constants ---
COLLECTION_NAME = "enron_emails"
QDRANT_DB = os.path.join(os.path.dirname(__file__), "qdrant_db")

# --- Prompts ---
chat_prompt = ChatPromptTemplate.from_template(
    "\n\n{context}\n\nQuestion: {input}"
)

document_prompt = PromptTemplate.from_template(
    "From: {sender}\nTo: {recipient}\nDate: {date}\nSubject: {subject}\nEntities: {entities}\n\n{page_content}"
)

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

# --- CLI Prompt ---
def main():
    query_text = input("🔍 Query: ").strip()
    if not query_text:
        print("⚠️ No query entered.")
        return

    # --- Embedding Model ---
    embedding_model = HuggingFaceEmbeddings(
        model_name="intfloat/e5-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # --- Load Vector Store ---
    qdrant = Qdrant.from_existing_collection(
        embedding=embedding_model,
        path=QDRANT_DB,
        collection_name=COLLECTION_NAME,
    )

    try:
        # --- LLM ---
        _, llm = init_groq(model_name="llama-3.3-70b-versatile")
        llm.groq_api_key = random.choice(api_keys)

        # --- Optimize Query ---
        optimized_query = llm.invoke(detailed_prompt.format(query=query_text)).content.strip()
        print("🔁 Optimized Query:", optimized_query)

        # --- Retrieval ---
        retriever = qdrant.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "lambda_mult": 0.2}
        )

        retrieved_docs = retriever.invoke(optimized_query)

        if not retrieved_docs:
            print("⚠️ No documents returned.")
            return

        # --- Format Context ---
        formatted_context = "\n\n".join([
            document_prompt.format(**doc.metadata, page_content=doc.page_content)
            for doc in retrieved_docs
        ])

        # --- Final Prompt to LLM ---
        final_prompt = chat_prompt.format(context=formatted_context, input=query_text)
        print("=" * 60)
        print("🧠 Asking LLM...\n")

        response = llm.invoke(final_prompt)
        print(response.content.strip())

    finally:
        qdrant.client.close()

if __name__ == "__main__":
    main()
