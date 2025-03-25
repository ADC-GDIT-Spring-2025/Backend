# Enron Email Dataset to Neo4j

## Setup
```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

## Populate Neo4j Graph
First make sure you have a local instance of Neo4j running:
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
```bash
source venv/bin/activate # Activate the virtual environment if not already activated
python neo4j_uploader.py <max_emails> <max_users>
```
