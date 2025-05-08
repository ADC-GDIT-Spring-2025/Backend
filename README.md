# Running Backend and Database Systems

## Project Structure

The project is organized into the following directories and files:

```
├── app.py                     # Main Flask application for handling API requests
├── etl_parse.sh               # Script for parsing and setting up the Enron dataset
├── README.md                  # Documentation for the project
├── requirements.txt           # Python dependencies for the project
├── setup_venv.sh              # Script to set up the Python virtual environment
├── startup.sh                 # Script to start the backend and frontend
├── data/                      # Directory containing the raw Enron dataset
│   ├── enron_mail.tar.gz      # Compressed Enron email dataset
│   └── maildir/               # Extracted email data organized by user
├── llama_code/                # Code for interacting with LLaMA API
│   └── llama_to_neo4j.py      # Converts user queries to Cypher queries for Neo4j
├── neo4j_code/                # Code for interacting with Neo4j database
│   ├── neo4j_uploader_bulk.py # Script to upload data to Neo4j in bulk
│   └── schema.json            # Schema definition for Neo4j
├── qdrant_code/               # Code for interacting with Qdrant vector database
│   ├── initialize_groq.py     # Initializes Groq API client
│   ├── qdrant_cli_test.py     # CLI for testing Qdrant queries
│   ├── qdrant_langchain.py    # LangChain integration with Qdrant
│   ├── data_for_qdrant/       # Data preparation for Qdrant
│   │   ├── clean_emails.py    # Script to clean and preprocess emails
│   │   ├── docslist.pkl       # Preprocessed document list
│   │   └── embeddings.npy     # Precomputed embeddings
│   └── qdrant_db/             # Qdrant database files
├── util/                      # Utility scripts
│   ├── fetch_data.py          # Script to fetch the Enron dataset
│   └── parser.py              # Script to parse raw email data
```

## Setup

```bash
# setup the virtual environment, installing dependencies
chmod +x setup_venv.sh

# activate the virtual environment
source ./setup_venv.sh

# download and parse the dataset
./etl_parse.sh
```

**NOTE: DO NOT DELETE THE DATASET OR THE PARSED FILES LATER, AS IT TAKES A LONG TIME TO GENERATE**

### Neo4j Setup

First make sure you have a local instance of Neo4j RUNNING:

- Download Neo4j Desktop from [here](https://neo4j.com/download/)
- Create a new instance called EmailMiner
- Set the password to `cheerios4150`
- Start the instance

#### To verify that Neo4j is running locally:

- Open a browser and go to `http://localhost:7474`
- Enter the username and password (neo4j/cheerios4150)
- Enter the command `MATCH (n) RETURN n` to get all nodes/relationships in the graph

#### To populate the graph with the Enron email dataset:

```bash
python neo4j_code/neo4j_uploader_bulk.py

# If you want to clear the neo4j database before uploading the new data, run with the flag:
python neo4j_code/neo4j_uploader_bulk.py --clear
```

#### Viewing the Neo4j Graph

Open a browser and go to `http://localhost:7474`

- Enter the username and password (neo4j/cheerios4150)
- Enter the command `MATCH (n) RETURN n` in the console at the top to get all nodes in the graph
- Click on the `Graph` tab (on the left) to view the graph

#### Setting up Qdrant

- In `qdrant_code/qdrant_db`, create a new folder named `collection`
- Create a new folder inside the `collection` folder called `enron_emails`
- Move the provided `storage.sqlite` file into `qdrant_code/qdrant_db/collection/enron_emails`

### Setup for the full pipeline

A short description of the pipeline:

1. Takes in a user prompt
2. Converts it to a Cypher query using LLaMA API
3. Runs that query on the Neo4j database
4. Prints the final answer

STEPS TO SETUP THE PIPELINE:

- Make sure you have the virtual environment activated by running the bash command at the top of this README.
- Save the llama API key in your environment variables as `LLAMA_API_KEY`:

```bash
# For mac:
export LLAMA_API_KEY=<your_llama_api_key_here>

# For windows CMD:
setx LLAMA_API_KEY=<your_llama_api_key_here>
# For windows PowerShell:
$env:LLAMA_API_KEY = "<your_llama_api_key_here>"
```

#### Running the Pipeline

If you have the frontend set up, you can start the backend server by running:

```bash
python app.py
```

If you don't have the frontend set up, you can run the pipeline directly from the command line:

```bash
python llama/llama_to_neo4j.py
```

It will prompt you for your query and then generate a cypher script and the print result from the Neo4j database of running that script.
