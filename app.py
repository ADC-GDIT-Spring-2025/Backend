from Llama.llama_to_neo4j import process_prompt
import flask
import json
import os
from flask_cors import CORS
import requests

FLASK_HOST='127.0.0.1'
FLASK_PORT=8080
API_KEY = os.environ.get("LLAMA_API_KEY")

SYSTEM_PROMPT="""
    You are LLaMA, a generative AI chatbot trained to assist users by generating informative, accurate, and context-aware responses. 
    Your primary task is to answer user questions related to the Enron email dataset.  
    You may receive additional background information derived from structured databases, including graph-based relationships and semantic search results.  
    If relevant data is available, incorporate it naturally into your response without explicitly stating its source.  

    Your response should:  
    1. **Present information clearly and conversationally**, avoiding any mention of databases, queries, or file formats.  
    2. **Seamlessly integrate retrieved data** with your general knowledge to provide insightful and well-structured answers.  
    3. **Indicate when a response is based purely on AI knowledge**, particularly if no supporting data is available.  
    4. **Use markdown for formatting** when presenting structured information (e.g., lists, summaries).  
    
    Always aim to be **concise, accurate, and engaging**, ensuring clarity in your explanations."""

app = flask.Flask(__name__)
CORS(app)

# MAIN THREAD OF CONVERSATION, FOR CONTEXT
thread = []

@app.route('/', methods=['GET'])
def index():
    return 'Server is running on port 5002.'

@app.route('/', methods=['POST'])
def route():
    try:
        prompt = flask.request.json.get('prompt', '').strip()

        thread.append({
            'role': 'user',
            'message': prompt
        })

        if not prompt:
            return flask.jsonify({ "error": "No prompt provided" }), 400

        neo4j_data = process_prompt(prompt)
        qdrant_data = query_qdrant(prompt)

        final_prompt = apply_template(prompt, neo4j_data, qdrant_data)

        final_response = query_llama(final_prompt)

        return flask.jsonify({ "llm_response": final_response })

    except Exception as e:
        return flask.jsonify({ "error": str(e) }), 500


def query_qdrant(prompt: str) -> str:
    # perform similarity search
    return ""

def query_neo4j(prompt: str) -> str:
    results = process_prompt(prompt)

    return results


def apply_template(prompt: str, neo4j_data: str, qdrant_data: str) -> str:
    # template = f'Prompt: {prompt}\nKnowledge Graph Data: {neo4j_data}\nQdrant Data: {qdrant_data}\n\n'
    template = f'Prompt: {prompt}\nKnowledge Graph Data: {neo4j_data}\n\n'

def query_llama(prompt: str, model: str = 'meta-llama3.3-70b', temperature: float = 0.7, maxGenLen: int = 512) -> str:
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
                               'max_tokens': maxGenLen,
                           })
    
    if response.status_code != 200:
        raise Exception(f"LLAMA API request failed with status code {response.status_code}: {response.text}")
    
    response_json = response.json()
    llama_output = response_json['data']['generation'].strip()

    thread.append({
        'role': 'assistant',
        'message': llama_output
    })

    print("LLAMA API response:", llama_output)

    return llama_output






if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT)