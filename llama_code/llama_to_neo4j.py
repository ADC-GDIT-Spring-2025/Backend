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

Limit the response from neo4j to 10 nodes for cases where the query returns the email body itself so as to not overload the reponse.
"""

message_thread = []

# ========== Prompt Template ==========
def get_filter_template(filters: dict = None) -> str:
    """Generate filter instructions for the prompt template."""
    if not filters:
        return ""
        
    filter_instructions = "YOU MUST INCORPORATE THE FOLLOWING FILTERS IN YOUR QUERY:\n"

    if filters.get('from'):
        filter_instructions += f"THE EMAIL MUST BE SENT BY A PERSON WITH EMAIL CONTAINING '{filters['from']}'\n"
    if filters.get('to'):
        filter_instructions += f"THE EMAIL MUST BE RECEIVED BY A PERSON WITH EMAIL CONTAINING '{filters['to']}'\n"
    if filters.get('cc'):
        filter_instructions += f"THE EMAIL MUST BE CC'D TO A PERSON WITH EMAIL CONTAINING '{filters['cc']}'\n"
    if filters.get('bcc'):
        filter_instructions += f"THE EMAIL MUST BE BCC'D TO A PERSON WITH EMAIL CONTAINING '{filters['bcc']}'\n"
    if filters.get('dateFrom'):
        filter_instructions += f"THE EMAIL DATE MUST BE ON OR AFTER {filters['dateFrom']}\n"
    if filters.get('dateTo'):
        filter_instructions += f"THE EMAIL DATE MUST BE ON OR BEFORE {filters['dateTo']}\n"
    if filters.get('keywords'):
        filter_instructions += f"THE EMAIL SUBJECT OR BODY MUST CONTAIN THE KEYWORDS: '{filters['keywords']}'\n"
    if filters.get('hasAttachment') == 'yes':
        filter_instructions += "THE EMAIL MUST HAVE ATTACHMENTS\n"
    elif filters.get('hasAttachment') == 'no':
        filter_instructions += "THE EMAIL MUST NOT HAVE ATTACHMENTS\n"
        
    return filter_instructions

def apply_template(user_question: str, filters: dict = None) -> str:
    filter_instructions = get_filter_template(filters)

    return f"""{TEMPLATE_INTRO}

Using the context of previous user messages, TRANSLATE the user's question into a CYPHER QUERY using the schema above. 
If the question does not need specific information from the dataset to be answered, then respond ONLY with "return ''" to return no data.

If you need to perform multiple match statements, COMBINE them into one query.
Do NOT include explanations or formatting — return ONLY the Cypher query. 
Your response should start with "MATCH" and be a VALID Cypher query.
Only provide ONE Cypher query, do NOT provide multiple queries or options.
{filter_instructions}

User question: "{user_question}"

Cypher query:
"""

def apply_error_template(user_question: str, cypher_query: str, error_msg: str = "", filters: dict = None) -> str:
    if error_msg != "":
        error_msg = "Error message: " + error_msg

    filter_instructions = get_filter_template(filters)

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
5. Must include ALL the filter requirements listed below:
{filter_instructions}

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
def query_neo4j(prompt: str, filters: dict = None) -> str:
    message_thread.append({
        'role': 'user',
        'message': prompt
    })
    full_prompt = apply_template(prompt, filters)
    cypher_query = query_llama(full_prompt)
    results = None

    max_tries = 3
    tries = 0
    while tries < max_tries:
        # print(f"\nAttempt {tries + 1}: {cypher_query}")

        if cypher_query.startswith("return"):
            return ''  # return no data

        if not cypher_query.lower().startswith("match"):
            print("⚠️ Cypher query does not start with 'match' — trying again.")
            full_prompt = apply_error_template(prompt, cypher_query, filters=filters)
            cypher_query = query_llama(full_prompt)
            tries += 1
            continue
        print("\nQuerying Neo4j...")
        results = run_cypher_query(cypher_query)
        if results is None or str(results).startswith("Neo4j query error"):
            print("⚠️ Neo4j query error or invalid query — trying again.")
            full_prompt = apply_error_template(prompt, cypher_query, results, filters)
            cypher_query = query_llama(full_prompt)
            tries += 1
        else:
            break

    if results is None or str(results).startswith("Neo4j query error"):
        print("⚠️ Failed to get valid results from Neo4j after multiple attempts.")
        print("Final attempt Cypher query: ", cypher_query)
        return ""
    
    print("\n Final prompt used to generate Cypher Query:\n", full_prompt)
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
