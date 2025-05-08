from llama_code.llama_to_neo4j import query_neo4j
from qdrant_code.qdrant_langchain import query_qdrant
import flask
from flask import jsonify
import json
import os
import re
from flask_cors import CORS
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

FLASK_HOST='127.0.0.1'
FLASK_PORT=8080
API_KEY = os.environ.get("LLAMA_API_KEY")

SYSTEM_PROMPT="""
    You are LLaMA, a generative AI chatbot trained to assist users by generating informative, accurate, and context-aware responses. 
    Your primary task is to answer user questions related to the Enron email dataset.  
    You may receive additional background information derived from structured databases, including graph-based relationships and semantic search results.  
    If relevant data is available, incorporate it naturally into your response without explicitly stating its source.  

    Your response should:  
    1. **Present information clearly and conversationally**, avoiding any mention of databases, queries, file formats, email ids, person ids, thread ids, or filepaths.  
    2. **Seamlessly integrate retrieved data** with your general knowledge to provide insightful and well-structured answers.  
    3. **Indicate when a response is based purely on AI knowledge**, particularly if no supporting data is available.  
    4. **Use markdown for formatting** when presenting structured information (e.g., lists, summaries).  
    5. ***DO NOT HALLUCINATE OR MAKE UP DATA.*** If you have no relevant data on the topic, just state this to the user.
    
    Always aim to be **concise, accurate, and engaging**, ensuring clarity in your explanations."""

app = flask.Flask(__name__)
CORS(app)

# MAIN THREAD OF CONVERSATION, FOR CONTEXT
thread = []

@app.route('/', methods=['GET'])
def index():
    return 'Server is running on port 5002.'

@app.route('/clear', methods=['GET'])
def clear():
    global thread
    thread = []
    logger.info("Thread cleared")
    return flask.jsonify({ "message": "Backend thread cleared" }), 200
    

@app.route('/', methods=['POST'])
def route():
    global thread
    try:
        prompt = flask.request.json.get('prompt', '').strip()
        logger.info(f'RECIEVED PROMPT: {prompt}')

        if not prompt:
            logger.error("No prompt provided")
            return flask.jsonify({ "error": "No prompt provided" }), 400
        
        filters = flask.request.json.get('filters', None)
        logger.info(f'RECIEVED FILTERS: {filters}')


        neo4j_data = []
        if filters['useNeo4j']:
            neo4j_data = query_neo4j(prompt, filters)
            logger.info(f"NEO4J RESULT —————————————————————————————————————————————————————————")
            if neo4j_data:
                logger.info(neo4j_data)
            else:
                logger.info("No Neo4j results, or error occurred.")
                neo4j_data = []

        def extract_filenames(data):
            filenames = []
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in ['filename', 'e.filename']:
                        filenames.append(value)
                        filenames.extend(extract_filenames(value))
                    elif isinstance(data, list):
                        for item in data:
                            filenames.extend(extract_filenames(item))
            elif isinstance(data, list):
                for item in data:
                    filenames.extend(extract_filenames(item))
            return filenames

        neo4j_emails = extract_filenames(neo4j_data)
        print(f"NEO4J EMAILS: {neo4j_emails}")

        # Get the email files from the filenames via the parsed data
        # open the parsed data json file
        with open('user_data/messages.json', 'r') as f:
            messages = json.load(f)

        with open('user_data/users.json', 'r') as f:
            users = json.load(f)
            # Swap key/value of the users dictionary
            users = {v: k for k, v in users.items()}

        # get the email files using filename
        neo4j_emails = [{
            'subject': email['subject'],
            'body': email['body'],
            'to': [users[id] for id in email['to']],
            'from': users[email['from']],
            'time': email['time'],
            'cc': [users[id] for id in email['cc']],
            'bcc': [users[id] for id in email['bcc']]
        } for email in messages if email['filename'] in neo4j_emails]

        print(f'NEO4J EMAILS: {neo4j_emails}')
        
        
        qdrant_data_string = ""
        if filters['useQdrant']:
            qdrant_data = get_qdrant_data(prompt)
            qdrant_data_string = qdrant_data.get_data(as_text=True)
            logger.info("QDRANT RESULT —————————————————————————————————————————————————————————")
            logger.info(qdrant_data_string)

        final_prompt = apply_template(prompt, neo4j_data, qdrant_data_string)
        # logger.info("FINAL PROMPT —————————————————————————————————————————————————————————")
        # logger.info(final_prompt)

        final_response = query_llama(final_prompt)
        logger.info("RETURNING LLAMA RESPONSE —————————————————————————————————————————————————————————")
        logger.info(final_response)

        # logger.debug(f"final_response: {final_response}")

        return flask.jsonify({ "llm_response": final_response, "raw_emails": neo4j_emails })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return flask.jsonify({ "error": str(e) }), 500
    
def get_qdrant_data(prompt: str) -> str:
    logger.setLevel(logging.INFO)
    if not prompt:
        logger.error("Missing Prompt")
        return jsonify({"error": "Missing prompt"}), 400
    try:
        answer = query_qdrant(prompt)
        return jsonify({"answer": answer})
    except Exception as e:
        logger.error(f"error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        logger.setLevel(logging.DEBUG)

def apply_template(prompt: str, neo4j_data: str, qdrant_data: str) -> str:
    return f'Here is the original prompt from the user: {prompt}\nNext is some relevant information from Neo4j, this is blank if there was no relevant info in the knowledge graph database. This info can be a count of emails if the user prompt asks something along the lines of "how many emails did person X send to person Y?". Or it can be the body of emails that are relevant to the question, like if the user prompt was "Summarize the emails sent between person X and person Y". Use the returned info to answer the user prompt, and quote lines from the email bodies directly when possible, citing the email you used. Here are the results from querying Neo4j with the prompt: {neo4j_data}\nNext is the result of running the prompt through Qdrant. Qdrant should return examples of emails that are relevant or help answer the prompt. Use these emails as the source for your answer to the prompt, and directly quote them as examples. Here is the result of running the prompt through Qdrant: {qdrant_data}\nRemember to use both the info from Neo4j and Qdrant to answer your question, using direct quotes and citations from the data as much as possible. If there was any data returned by Neo4j and Qdrant use that and avoid using your own knowledge.\n'

def get_files(filenames: list[str]):
    """
    code taken from parser.py
    """
    email_files = []
    for filename in filenames:
        filename = os.path.join(os.path.dirname(__file__), "data/maildir", filename)
        with open(filename, encoding='utf-8', errors='replace') as TextFile:
            text = TextFile.read().replace("\r", "")
            # Skip characters outside of Unicode range
            text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
            try:
                #
                # Precompiled regular expression patterns for email parsing
                # These patterns are compiled once for performance optimization when processing many emails
                #
                time_pattern = re.compile(r"Date: (?P<data>[A-Z][a-z]+, \d{1,2} [A-Z][a-z]+ \d{4} \d{2}:\d{2}:\d{2} -\d{4} \([A-Z]{3}\))")
                subject_pattern = re.compile(r"Subject: (?P<data>.*)")
                sender_pattern = re.compile(r"From: (?P<data>.*)")
                recipient_pattern = re.compile(r"To: (?P<data>.*)")
                cc_pattern = re.compile(r"cc: (?P<data>.*)")
                bcc_pattern = re.compile(r"bcc: (?P<data>.*)")
                msg_start_pattern = re.compile(r"\n\n", re.MULTILINE)  # Email body typically starts after two newlines
                msg_end_pattern = re.compile(r"\n+.*\n\d+/\d+/\d+ \d+:\d+ [AP]M", re.MULTILINE)  # Pattern to detect end of message in replies


                # Extract email metadata
                time = time_pattern.search(text).group("data").replace("\n", "")
                subject = subject_pattern.search(text).group("data").replace("\n", "")
                sender = sender_pattern.search(text).group("data").replace("\n", "")
                recipient = recipient_pattern.search(text).group("data").split(", ")
                cc = cc_pattern.search(text).group("data").split(", ")
                bcc = bcc_pattern.search(text).group("data").split(", ")
                
                # Extract email body
                msg_start_iter = msg_start_pattern.search(text).end()
                try:
                    msg_end_iter = msg_end_pattern.search(text).start()
                    message = text[msg_start_iter:msg_end_iter]
                except AttributeError:  # not a reply
                    message = text[msg_start_iter:]
                
                # Clean up the message text to avoid errors from special characters
                message = re.sub("[\n\r]", " ", message)
                message = re.sub("  +", " ", message)


                parsed_email = {
                    "time": time,
                    "subject": subject,
                    "from": sender,
                    "to": recipient,
                    "cc": cc,
                    "bcc": bcc,
                    "message": message
                }
                email_files.append(parsed_email)
                
            except AttributeError:
                logger.error(f"Failed to parse {filename}")
                return None
        
    return email_files

# temperature = amount of randomness in the output
def query_llama(prompt: str, model: str = 'meta-llama4-maverick-17b', temperature: float = 0.1) -> str:
    # tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-70b-chat-hf")
    # input_tokens_count = tokenizer.encode(prompt.append(SYSTEM_PROMPT), add_special_tokens=False)
    # print(" ============ Input token count:", len(input_tokens_count), " =============== ")
    
    # add the prompt to the thread
    thread.append({
        'role': 'user',
        'message': prompt
    })
    
    logger.info(f"Using API KEY: {API_KEY[:6]}..." if API_KEY else "None set")

    
    response = requests.post('https://api.llms.afterhoursdev.com/chat/completions',
                           headers={
                               'Content-Type': 'application/json',
                               'Authorization': f'Bearer {API_KEY}',
                           },
                           json={
                               'model': model,
                               'messages': thread,
                               'system': SYSTEM_PROMPT,
                               'temperature': temperature,
                                'max_tokens': 10000000 - len(prompt.split(sep = ' ')) * 0.2 - len(SYSTEM_PROMPT.split(sep = ' ')) * 0.2,
                           })
    
    
    if response.status_code != 200:
        # remove the prompt from the thread
        thread.pop()
        raise Exception(f"LLAMA API request failed with status code {response.status_code}: {response.text}")
    
    response_json = response.json()
    llama_output = response_json['generation'].strip()

    thread.append({
        'role': 'assistant',
        'message': llama_output
    })


    return llama_output

if __name__ == '__main__':
    logger.info(f"Starting Flask server on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
