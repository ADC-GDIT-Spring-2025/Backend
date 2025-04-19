import sys
import json
import requests
from neo4j import GraphDatabase
import time
from tqdm import tqdm  # Added tqdm import

# Neo4j connection details (adjust these as needed)
URL = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "cheerios4150"

def create_person(tx, person_id, email):
    query = """
    MERGE (p:Person {id: $person_id})
    SET p.email = $email
    """
    tx.run(query, person_id=person_id, email=email)

def create_email(tx, email_id, time, thread, body, filepath):
    query = """
    MERGE (e:Email {id: $email_id})
    SET e.time = $time, e.thread = $thread, e.body = $body, e.filepath = $filepath
    """
    tx.run(query, email_id=email_id, time=time, thread=thread, body=body, filepath=filepath)

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

def person_exists(tx, person_id):
    query = """
    MATCH (p:Person {id: $person_id}) RETURN p LIMIT 1
    """
    result = tx.run(query, person_id=person_id)
    return result.single() is not None

def email_exists(tx, email_id):
    query = """
    MATCH (e:Email {id: $email_id}) RETURN e LIMIT 1
    """
    result = tx.run(query, email_id=email_id)
    return result.single() is not None

def relationship_exists_sent(tx, person_id, email_id):
    query = """
    MATCH (p:Person {id: $person_id})-[r:SENT]->(e:Email {id: $email_id}) RETURN r LIMIT 1
    """
    result = tx.run(query, person_id=person_id, email_id=email_id)
    return result.single() is not None

def relationship_exists_received(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id})-[r:RECEIVED]->(p:Person {id: $person_id}) RETURN r LIMIT 1
    """
    result = tx.run(query, email_id=email_id, person_id=person_id)
    return result.single() is not None

def relationship_exists_received_cc(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id})-[r:RECEIVED_CC]->(p:Person {id: $person_id}) RETURN r LIMIT 1
    """
    result = tx.run(query, email_id=email_id, person_id=person_id)
    return result.single() is not None

def relationship_exists_received_bcc(tx, email_id, person_id):
    query = """
    MATCH (e:Email {id: $email_id})-[r:RECEIVED_BCC]->(p:Person {id: $person_id}) RETURN r LIMIT 1
    """
    result = tx.run(query, email_id=email_id, person_id=person_id)
    return result.single() is not None

def main():
    limit_data = False
    
    # Check for command line arguments for maximum emails and maximum users to process
    if len(sys.argv) != 1 and len(sys.argv) != 3:
        print("Usage: \n\tpython neo4j_uploader.py \n\tpython neo4j_uploader.py <max_emails> <max_users>")
        sys.exit(1)
    elif len(sys.argv) == 3:
        try:
            max_emails = int(sys.argv[1])
            max_users = int(sys.argv[2])
            limit_data = True
        except ValueError:
            print("Invalid value provided for max_emails or max_users. Please provide integers.")
            sys.exit(1)
    

    # Load data from local JSON files
    try:
        with open('user_data/users.json', 'r') as f:
            all_users_data = json.load(f)
        with open('user_data/messages.json', 'r') as f:
            all_messages_data = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}. Make sure 'user_data/users.json' and 'user_data/messages.json' exist.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        sys.exit(1)

    if limit_data:
        # Limit users data (dictionary)
        users_items = list(all_users_data.items())[:max_users]
        users_data = dict(users_items)
        # Limit messages data (list)
        messages_data = all_messages_data[:max_emails]
        print(f"Limiting data to {len(messages_data)} emails and {len(users_data)} users.")
    else:
        users_data = all_users_data
        messages_data = all_messages_data
        print(f"Processing all {len(messages_data)} emails and {len(users_data)} users.")

    driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        # Start timing the node upload
        start_time = time.time()

        skipped_persons = 0
        skipped_emails = 0
        skipped_sent = 0
        skipped_received = 0
        skipped_received_cc = 0
        skipped_received_bcc = 0

        # Create Person nodes from the limited users data
        for email, person_id in tqdm(users_data.items(), desc="Uploading Person nodes"):
            if not session.read_transaction(person_exists, person_id):
                # print("c")
                session.execute_write(create_person, person_id, email)
            else:
                skipped_persons += 1
                # print("s")

        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Uploaded {len(users_data) - skipped_persons} Person nodes in {elapsed_time:.2f} seconds. Skipped {skipped_persons} already existing Person nodes.")

        # Create Email nodes and relationships for the messages
        for idx, message in tqdm(enumerate(messages_data), total=len(messages_data), desc="Uploading Email nodes & relationships"):
            email_id = str(idx)  # Unique email id based on the index
            time_ = message.get("time", "")
            thread = message.get("thread", "")
            body = message.get("message", "")
            filepath = message.get("filepath", "")

            if session.read_transaction(email_exists, email_id):
                skipped_emails += 1
                print("s")
                continue  # Skip if email already exists

            
                print("c")
            session.execute_write(create_email, email_id, time_, thread, body, filepath)

            sender_id = message.get("sender")
            if sender_id is not None and sender_id in users_data.values():
                if not session.read_transaction(relationship_exists_sent, sender_id, email_id):
                    print("c")
                    session.execute_write(create_relationship_sent, sender_id, email_id)
                else:
                    skipped_sent += 1
                    print("s")
                    

            for rec in message.get("recipients", []):
                if rec in users_data.values():
                    if not session.read_transaction(relationship_exists_received, email_id, rec):
                        print("c")
                        session.execute_write(create_relationship_received, email_id, rec)
                    else:
                        skipped_received += 1
                        print("s")
                        

            for cc in message.get("cc", []):
                if cc in users_data.values():
                    if not session.read_transaction(relationship_exists_received_cc, email_id, cc):
                        print("c")
                        session.execute_write(create_relationship_received_cc, email_id, cc)
                    else:
                        skipped_received_cc += 1
                        print("s")
                        

            for bcc in message.get("bcc", []):
                if bcc in users_data.values():
                    if not session.read_transaction(relationship_exists_received_bcc, email_id, bcc):
                        print("c")
                        session.execute_write(create_relationship_received_bcc, email_id, bcc)
                    else:
                        skipped_received_bcc += 1
                        print("s")
                        

    driver.close()
    print("Data import complete.")
    print(f"Skipped {skipped_persons} Person nodes, {skipped_emails} Email nodes.")
    print(f"Skipped {skipped_sent} SENT, {skipped_received} RECEIVED, {skipped_received_cc} RECEIVED_CC, {skipped_received_bcc} RECEIVED_BCC relationships.")

if __name__ == "__main__":
    main()