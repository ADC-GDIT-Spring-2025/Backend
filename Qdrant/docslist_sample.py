import joblib

docs = joblib.load("data_for_qdrant/docslist.pkl")

for i, doc in enumerate(docs[:5]):  # show the first 5 documents
    print(f"\n--- Document {i+1} ---")
    print(doc.page_content)
    print(doc.metadata)
