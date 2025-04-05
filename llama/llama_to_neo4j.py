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


TEMPLATE_INTRO = """
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
"""

# ========== Prompt Template ==========
# note: the email formatting is not consistent. we need to either exclude that part of the template or figure out a more flexible option
def apply_template(user_question: str) -> str:
    return f"""{TEMPLATE_INTRO}

Translate the user's question into a Cypher query using the schema above. 
If the question does not need specific information from the dataset to be answered, then respond ONLY with "return ''" to return no data.

If you need to perform multiple match statements, combine them into one query.
Do NOT include explanations or formatting — only return the Cypher query. 
Your resposne should start with "match" and be a valid Cypher query.
Only provide ONE Cypher query, do not provide multiple queries or options.

User question: "{user_question}"

Cypher query:
"""

def apply_error_template(user_question: str, cypher_query: str, error_msg: str = "") -> str:
    if error_msg != "":
        error_msg = "Error message: " + error_msg


    return f"""{TEMPLATE_INTRO}

The previous attempt to generate a Cypher query for this question failed:
Question: "{user_question}"
Failed query: {cypher_query}
{error_msg}

Generate a new, corrected Cypher query that:
1. Must start with 'match'
2. Must be syntactically valid
3. Must use the schema exactly as shown above
4. Must answer the original question

Return ONLY the corrected Cypher query with no explanations or additional text.

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

def run_cypher_query(query: str) -> str:
    driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        try:
            result = session.run(query)
            data = result.data()
            return data
        except Exception as e:
            print("Neo4j query error:", e)
            return "Neo4j query error: " + str(e)
        finally:
            driver.close()

# ========== Main Program ==========

def query_neo4j(prompt: str) -> str:
    full_prompt = apply_template(prompt)
    cypher_query = query_llama(full_prompt)

    max_tries = 3
    tries = 0
    while tries < max_tries:
        print(f"\nAttempt {tries + 1}: {cypher_query}")

        if cypher_query.startswith("return"):
            return ''  # return no data

        if not cypher_query.startswith("match"):
            print("⚠️ Cypher query does not start with 'match' — trying again.")
            full_prompt = apply_error_template(prompt, cypher_query)
            cypher_query = query_llama(full_prompt)
            tries += 1
            continue
        print("\nQuerying Neo4j...")
        results = run_cypher_query(cypher_query)
        if results is None or str(results).startswith("Neo4j query error"):
            print("⚠️ Neo4j query error or invalid query — trying again.")
            full_prompt = apply_error_template(prompt, cypher_query, results)
            cypher_query = query_llama(full_prompt)
            tries += 1
        else:
            break


    if results is None or str(results).startswith("Neo4j query error"):
        print("⚠️ Failed to get valid results from Neo4j after multiple attempts.")
        return ""
    
    print(f"\nFinal Cypher Query used: {cypher_query}")
    print("\nCypher query results:") # the results from neo4j is a list of dicts, where each dict is a row of data
    if results:
        for row in results[:10]:
            print(row)
    else:
        print("No Neo4j results, or error occurred.")
        results = ""

    return results


if __name__ == "__main__":
    prompt = input("Enter your question: ")
    query_neo4j(prompt)
