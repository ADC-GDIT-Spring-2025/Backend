import sys
import json
import requests
from neo4j import GraphDatabase
import time

# Neo4j connection details (adjust these as needed)
URI = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "cheerios4150"

def create_person(tx, person_id, email):
    query = """
    MERGE (p:Person {id: $person_id})
    SET p.email = $email
    """
    tx.run(query, person_id=person_id, email=email)

def create_email(tx, email_id, time, thread, body):
    query = """
    MERGE (e:Email {id: $email_id})
    SET e.time = $time, e.thread = $thread, e.body = $body
    """
    tx.run(query, email_id=email_id, time=time, thread=thread, body=body)

def create_relationship_sent(tx, person_id, email_id):
    query = """
    MATCH (p:Person {id: $person_id}), (e:Email {id: $email_id})
    MERGE (p)-[:SENT]->(e)
    """
    tx.run(query, person_id=person_id, email_id=email_id)

def create_relationship_received(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id}), (p:Person {id: $person_id})
    MERGE (e)-[:RECEIVED]->(p)
    """
    tx.run(query, email_id=email_id, person_id=person_id)

def create_relationship_received_cc(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id}), (p:Person {id: $person_id})
    MERGE (e)-[:RECEIVED_CC]->(p)
    """
    tx.run(query, email_id=email_id, person_id=person_id)

def create_relationship_received_bcc(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id}), (p:Person {id: $person_id})
    MERGE (e)-[:RECEIVED_BCC]->(p)
    """
    tx.run(query, email_id=email_id, person_id=person_id)

def main():
    # Check for command line arguments for maximum emails and maximum users to process
    if len(sys.argv) < 3:
        print("Usage: python neo4j_importer.py <max_emails> <max_users>")
        sys.exit(1)
    
    try:
        max_emails = int(sys.argv[1])
        max_users = int(sys.argv[2])
    except ValueError:
        print("Invalid value provided for max_emails or max_users. Please provide integers.")
        sys.exit(1)

    users_url = f'http://localhost:5002/users?limit={max_users}'
    messages_url = f'http://localhost:5002/messages?limit={max_emails}'

    users_data = requests.get(users_url, stream=True).json()
    messages_data = requests.get(messages_url, stream=True).json()

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        # Start timing the node upload
        start_time = time.time()

        # Create Person nodes from the limited users data
        for email, person_id in users_data.items():
            session.write_transaction(create_person, person_id, email)

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Uploaded {len(users_data)} Person nodes in {elapsed_time:.2f} seconds.")

        # Create Email nodes and relationships for the messages
        for idx, message in enumerate(messages_data):
            email_id = str(idx)  # Unique email id based on the index
            time_ = message.get("time", "")
            thread = message.get("thread", "")
            body = message.get("message", "")

            session.write_transaction(create_email, email_id, time_, thread, body)

            sender_id = message.get("sender")
            if sender_id is not None and sender_id in users_data.values():
                session.write_transaction(create_relationship_sent, sender_id, email_id)

            for rec in message.get("recipient", []):
                if rec in users_data.values():
                    session.write_transaction(create_relationship_received, email_id, rec)

            for cc in message.get("cc", []):
                if cc in users_data.values():
                    session.write_transaction(create_relationship_received_cc, email_id, cc)

            for bcc in message.get("bcc", []):
                if bcc in users_data.values():
                    session.write_transaction(create_relationship_received_bcc, email_id, bcc)

    driver.close()
    print("Data import complete.")

if __name__ == "__main__":
    main()