# Enron Email Dataset to Neo4j

This project helps you import the Enron email dataset into a Neo4j graph database for analysis and exploration.

## Prerequisites

1. Python 3.7+
2. Neo4j Database (local or remote)
3. Enron Email Dataset

## Setup

1. Install the required Python packages:
```bash
pip install -r requirements.txt
```

2. Make sure your Neo4j database is running and accessible

3. Update the Neo4j credentials in `enron_to_neo4j.py`:
```python
parser = EnronEmailParser(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your_password"  # Replace with your actual password
)
```

## Usage

Run the script:
```bash
python enron_to_neo4j.py
```

The script will:
1. Create necessary constraints in Neo4j
2. Process all emails in the maildir
3. Create nodes for:
   - People (senders and recipients)
   - Emails (with metadata and content)
4. Create relationships:
   - SENT (Person -> Email)
   - RECEIVED (Person -> Email)

## Graph Structure

The resulting graph will have:

### Nodes
- `Person`: Email participants
  - Properties: `email`
- `Email`: Individual emails
  - Properties: `message_id`, `subject`, `date`, `body`

### Relationships
- `SENT`: Connects a person to an email they sent
- `RECEIVED`: Connects a person to an email they received

## Example Queries

1. Find all emails sent by a specific person:
```cypher
MATCH (p:Person {email: 'phillip.allen@enron.com'})-[:SENT]->(e:Email)
RETURN e.subject, e.date
ORDER BY e.date DESC
LIMIT 10
```

2. Find communication patterns between two people:
```cypher
MATCH path = (p1:Person {email: 'phillip.allen@enron.com'})-[:SENT]->(e:Email)<-[:RECEIVED]-(p2:Person)
RETURN p1.email, p2.email, count(e) as communication_count
ORDER BY communication_count DESC
LIMIT 10
```

3. Find the most active email participants:
```cypher
MATCH (p:Person)-[r:SENT|RECEIVED]->(e:Email)
RETURN p.email, count(r) as activity_count
ORDER BY activity_count DESC
LIMIT 10
```