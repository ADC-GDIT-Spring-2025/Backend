import requests
import os
from neo4j import GraphDatabase
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
(:Email {{thread: number, subject: string, body: string, filename: string, time: string}})

Relationships:
(:Person)-[:SENT]->(:Email)
(:Person)<-[:RECEIVED]-(:Email)
(:Person)<-[:RECEIVED_CC]-(:Email)
(:Person)<-[:RECEIVED_BCC]-(:Email)
(:Email)-[:REPLY]->(:Email)
(:Email)-[:FORWARD]->(:Email)

Limit the response from neo4j to 10 nodes for cases where the query returns the email body itself so as to not overload the response, unless the number of emails is specified in the prompt.
"""

message_thread = []

# ========== Prompt Template ==========
def get_filter_template(filters: dict = None) -> str:
    """Generate filter instructions for the prompt template."""
    logger.info(f"Generating filter template for filters: {filters}")
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
    logger.info(f"Applying template for user question: {user_question}")
    filter_instructions = get_filter_template(filters)

    return f"""{TEMPLATE_INTRO}

Using the context of previous user messages, TRANSLATE the user's question into a CYPHER QUERY using the schema above. 
If the question does not need specific information from the dataset to be answered, then respond ONLY with "return ''" to return no data.

If you need to perform multiple match statements, COMBINE them into one query.
Do NOT include explanations or formatting — return ONLY the Cypher query. 
The Cypher query must ensure the filename of any email node is included in the results.
Your response should start with "MATCH" and be a VALID Cypher query.
Only provide ONE Cypher query, do NOT provide multiple queries or options.
{filter_instructions}

User question: "{user_question}"

Cypher query:
"""

def apply_error_template(user_question: str, cypher_query: str, error_msg: str = "", filters: dict = None) -> str:
    logger.info(f"Applying error template for user question: {user_question}, failed query: {cypher_query}, error: {error_msg}")
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
5. MUST include the filename of each email node in the results.
6. Must include ALL the filter requirements listed below:
{filter_instructions}

Return ONLY the corrected Cypher query with no explanations or additional text.

Cypher query:
"""


# ========== Calling the Llama model ==========

def query_llama(prompt: str) -> str:
    # logger.info(f"Querying Llama model: {MODEL_NAME}")
    # logger.info(f"Llama prompt: {prompt}")
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

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        # logger.info(f"Llama API request successful (Status: {response.status_code})")
        data = response.json()
        generation = data.get("generation", "").strip()
        # logger.info(f"Llama generation received: {generation}")
        return generation
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling Llama API: {e}")
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred during Llama API call: {e}")
        return ""

# ========== Neo4j Query Runner ==========

def run_cypher_query(query: str) -> str:
    # logger.info("Running Cypher query against Neo4j")
    # logger.info(f"Executing query: {query}")
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # logger.info("Neo4j session opened.")
            result = session.run(query)
            data = result.data()
            summary = result.consume()
            return data
    except Exception as e:
        logger.error(f"Neo4j query failed for query '{query}'. Error: {e}")
        return f"Neo4j query error: {e}"
    finally:
        if driver:
            driver.close()

# ========== Main Program ==========
def query_neo4j(prompt: str, filters: dict = None) -> str:
    # logger.info(f"Starting query_neo4j process for prompt: '{prompt}' with filters: {filters}")
    message_thread.append({
        'role': 'user',
        'message': prompt
    })
    logger.info(f"Appended user message to thread. Current thread length: {len(message_thread)}")
    
    full_prompt = apply_template(prompt, filters)
    logger.info(f"Generated full prompt for Llama: {full_prompt}")
    cypher_query = query_llama(full_prompt)
    results = None

    max_tries = 3
    tries = 0
    while tries < max_tries:
        # logger.info(f"Neo4j query attempt {tries + 1}/{max_tries}")
        # logger.info(f"Attempt {tries + 1} - Query before filter application: {cypher_query}")

        if cypher_query.startswith("return"):
            logger.info("Query starts with 'return', likely an indication to skip Neo4j. Returning empty data.")
            return ''  # return no data

        if not cypher_query.lower().startswith("match"):
            # logger.warning(f"Attempt {tries + 1} - Cypher query does not start with 'match'. Query: '{cypher_query}'. Requesting correction from Llama.")
            full_prompt = apply_error_template(prompt, cypher_query, error_msg="Query does not start with MATCH")
            cypher_query = query_llama(full_prompt)
            tries += 1
            continue
        logger.info(f"Attempt {tries + 1} - Querying Neo4j...")
        results = run_cypher_query(cypher_query)
        
        if results is None or results == [] or str(results).startswith("Neo4j query error"):
            logger.warning(f"Attempt {tries + 1} - Neo4j query returned error or empty result. Requesting correction from Llama.")
            if results is None or results == []:
                error_msg = "Query returned no results."
            else:
                error_msg = str(results)
            full_prompt = apply_error_template(prompt, cypher_query, error_msg)
            cypher_query = query_llama(full_prompt)
            tries += 1
        else:
            break

    if results is None or str(results).startswith("Neo4j query error"):
        logger.error(f"Failed to get valid results from Neo4j after {max_tries} attempts.")
        logger.error(f"Final failing Cypher query: {cypher_query}")
        return ""
    
    logger.info(f"Final successful Cypher Query: {cypher_query}")
    
    if not results:
        logger.info("Process finished with no results.")
        results = ""
    else:
        logger.info(f"Process finished successfully with {len(results)} result items.")

    return results


if __name__ == "__main__":
    if not API_KEY:
        logger.error("LLAMA_API_KEY environment variable not set.")
    else:
        prompt = input("Enter your question: ")
        query_neo4j(prompt)
