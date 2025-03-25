import sys
import json
from neo4j import GraphDatabase

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

    # Load users and messages from JSON files
    with open("../user_data/users2.json", "r") as f:
        users_data = json.load(f)
    with open("../user_data/messages2.json", "r") as f:
        messages_data = json.load(f)

    # Limit the messages to only the first max_emails messages
    messages_data = messages_data[:max_emails]

    # Limit the users to only the first max_users entries.
    limited_users_data = dict(list(users_data.items())[:max_users])
    
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        # Create Person nodes from the limited users data
        for email, person_id in limited_users_data.items():
            session.write_transaction(create_person, person_id, email)

        # Create Email nodes and relationships for the messages
        for idx, message in enumerate(messages_data):
            email_id = str(idx)  # Unique email id based on the index
            time = message.get("time", "")
            thread = message.get("thread", "")
            body = message.get("message", "")

            # Create the Email node
            session.write_transaction(create_email, email_id, time, thread, body)

            # Create the SENT relationship from the sender to the email if the sender exists in our limited users
            sender_id = message.get("sender")
            if sender_id is not None and sender_id in limited_users_data.values():
                session.write_transaction(create_relationship_sent, sender_id, email_id)

            # Create RECEIVED relationships for each recipient if they exist in our limited users
            for rec in message.get("recipient", []):
                if rec in limited_users_data.values():
                    session.write_transaction(create_relationship_received, email_id, rec)

            # Create RECEIVED_CC relationships for each cc if they exist in our limited users
            for cc in message.get("cc", []):
                if cc in limited_users_data.values():
                    session.write_transaction(create_relationship_received_cc, email_id, cc)

            # Create RECEIVED_BCC relationships for each bcc if they exist in our limited users
            for bcc in message.get("bcc", []):
                if bcc in limited_users_data.values():
                    session.write_transaction(create_relationship_received_bcc, email_id, bcc)

    driver.close()
    print("Data import complete.")

if __name__ == "__main__":
    main()
