from llama.llama_to_neo4j import process_prompt
import flask
import json
from flask_cors import CORS

FLASK_HOST='127.0.0.1'
FLASK_PORT=8080

app = flask.Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return 'Server is running on port 5002.'

@app.route('/neo4j', methods=['POST'])
def query_neo4j():
    data = flask.request.get_json()
    prompt = data.get("prompt")
    
    # Run the pipeline on the prompt
    results = process_prompt(prompt)

    return flask.jsonify(results)


if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT)