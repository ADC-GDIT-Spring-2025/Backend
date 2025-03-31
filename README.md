# Enron Email Dataset to Neo4j

## Setup
```bash
chmod +x setup_venv.sh
source ./setup_venv.sh
```

## Neo4j Graph Setup
First make sure you have a local instance of Neo4j RUNNING:
- Download Neo4j Desktop from [here](https://neo4j.com/download/)
- Create a new instance called EmailMiner
- Set the password to `cheerios4150`
- Start the instance
### To verify that Neo4j is running locally:
- Open a browser and go to `http://localhost:7474`
- Enter the username and password (neo4j/cheerios4150)
- Enter the command `MATCH (n) RETURN n` to get all nodes/relationships in the graph
- Enter the command `MATCH (n) DETACH DELETE n` to get rid of all nodes/relationships in the graph

### To populate the graph with the Enron email dataset:
First make sure the ETL data server is running:
- clone the ETL repository:
```bash
git clone https://github.com/ADC-GDIT-Spring-2025/ETL # for HTTPS

# OR:

git clone git@github.com:ADC-GDIT-Spring-2025/ETL.git # for SSH
```
- run the setup scripts as detailed in the README.md file in the ETL repository
- the server should be running on `http://localhost:5002`

Then run the following command:
```bash
source venv/bin/activate # Activate the virtual environment if not already activated
python Neo4j/neo4j_uploader.py <max_emails> <max_users>
```

### Viewing the Neo4j Graph
Open a browser and go to `http://localhost:7474`
- Enter the username and password (neo4j/cheerios4150)
- Enter the command `MATCH (n) RETURN n` in the console at the top to get all nodes in the graph
- Click on the `Graph` tab (on the left) to view the graph


## Testing the Llama chatbot for backend use
There is a Python script called `test_llama.py` within the Llama folder which is used to test a successful connection to our llama model.

### Setup for the script
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
- Run the Python script:
```bash
python test_llama.py
```

### Usage
The script will prompt you to enter a message to send to the llama model. The model will then respond with a message.

You can analyze and modify the python code to change the context. You can see that the `thread` variable stores the context for the current chat.

There is also an option in the API request to add pre-written instructions for the chatbot to apply to all prompts:
```python
'system': 'You are a chatbot meant to teach geography. Any answer to a question should be accompanied by a description of where in the world the relevant place is.',
```

## Running the Full Pipeline

### Here is the full pipeline
1. Takes in a user prompt
2. Converts it to a Cypher query using LLaMA API
3. Runs that query on the Neo4j database
4. Prints the final answer

### llama_to_neo4j.py
Navigate to the Llama directory and run the following command:
```bash
python llama_to_neo4j
```
It will prompt you for your query and then return the generated cypher script and the result from the Neo4j database of running that script.
Then we can send this result to the frontend as part of the context for the final response. 