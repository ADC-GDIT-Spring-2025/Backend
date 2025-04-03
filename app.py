from Llama.llama_to_neo4j import process_prompt
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
    try:
        prompt = flask.request.data.decode('utf-8').strip()

        if not prompt:
            return flask.jsonify({ "error": "No prompt provided" }), 400

        results = process_prompt(prompt)
        return flask.jsonify({ "results": results })

    except Exception as e:
        return flask.jsonify({ "error": str(e) }), 500



if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT)