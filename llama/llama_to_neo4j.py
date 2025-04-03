import requests
import os
from neo4j import GraphDatabase

# ========== Config ==========

#Neo4j Config
NEO4J_URL = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "cheerios4150"

# Llama Config
API_URL = "https://api.llms.afterhoursdev.com/completions"
API_KEY = os.environ.get("LLAMA_API_KEY")
SESSION_TOKEN = ""

MODEL_NAME = "meta-llama3.3-70b"
SYSTEM_PROMPT = "You are a helpful assistant"
TEMPERATURE = 0.5
TOP_P = 0.9
MAX_GEN_LEN = 512

# ========== Prompt Template ==========
# note: the email formatting is not consistent. we need to either exclude that part of the template or figure out a more flexible option
def apply_template(user_question: str) -> str:
    return f"""
You are a Cypher query expert working with a Neo4j graph database.

Graph schema:

Nodes:
(:Person {{id: string, email: string}}) — use the email property, not name, emails are formatted as firstname.lastname@enron.com
(:Email {{thread_id: string, subject: string, body: string}})

Relationships:
(:Person)-[:SENT]->(:Email)
(:Person)<-[:RECEIVED]-(:Email)
(:Person)<-[:RECEIVED_CC]-(:Email)
(:Person)<-[:RECEIVED_BCC]-(:Email)
(:Email)-[:REPLY]->(:Email)
(:Email)-[:FORWARD]->(:Email)

Translate the user's question into a Cypher query using the schema above.
Do NOT include explanations or formatting — only return the Cypher query.

User question: "{user_question}"

Cypher query:
"""

# ========== Calling the Llama model ==========

def query_llama(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    if SESSION_TOKEN:  # Optional
        headers["SESSION-TOKEN"] = SESSION_TOKEN

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "temperature": TEMPERATURE,
        "topP": TOP_P,
        "maxGenLen": MAX_GEN_LEN
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()

    data = response.json()

    return data.get("generation", "").strip()

# ========== Neo4j Query Runner ==========

def run_cypher_query(query: str):
    driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        try:
            result = session.run(query)
            data = result.data()
            return data
        except Exception as e:
            print("Neo4j query error:", e)
            return None
        finally:
            driver.close()

# ========== Main Program ==========

def process_prompt(prompt: str):
    full_prompt = apply_template(prompt)
    cypher_query = query_llama(full_prompt)

    print("\nGenerated Cypher Query:\n", cypher_query)

    if not cypher_query.lower().startswith("match"):
        print("⚠️ Query might not be valid — skipping Neo4j run.")
        return

    print("\nQuerying Neo4j...")
    results = run_cypher_query(cypher_query)

    print("\nResults:")
    if results:
        for row in results:
            print(row)
    else:
        print("No results or error occurred.")

    return results


if __name__ == "__main__":
    prompt = input("Enter your question: ")
    process_prompt(prompt)
