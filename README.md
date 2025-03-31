# Enron Email Dataset to Neo4j

## Setup
```bash
chmod +x setup_venv.sh
./setup_venv.sh
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