import requests

# CONFIGURATION
API_URL = "https://api.llms.afterhoursdev.com/completions"
API_KEY = "a509790793f9864cbe4b3fdb1aab0c44169ae5c780dab12a96ad7824f7d5a78f"
SESSION_TOKEN = ""

MODEL_NAME = "meta-llama3.3-70b"
SYSTEM_PROMPT = "You are a helpful assistant"
TEMPERATURE = 0.5
TOP_P = 0.9
MAX_GEN_LEN = 512


# STEP 1: Enron Schema → Prompt Template
def make_prompt_enron(user_question: str) -> str:
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


# STEP 2: Call the LLaMA model
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
    print("\n[DEBUG] Full API Response:", data)

    return data.get("generation", "").strip()

# STEP 3: Run the full pipeline
def main():
    user_question = input("Enter your natural language question: ")
    prompt = make_prompt_enron(user_question)
    cypher_query = query_llama(prompt)

    print("\nGenerated Cypher Query:")
    print(cypher_query)


if __name__ == "__main__":
    main()
