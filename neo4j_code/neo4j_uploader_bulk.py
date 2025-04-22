import sys
import json
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from tqdm import tqdm
import os

# Neo4j connection details (adjust these as needed)
URL = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD") or "cheerios4150"

BATCH_SIZE = 1000  # Tune this for your memory/DB

def check_neo4j_connection():
    """Check if Neo4j database is running and accessible."""
    print("Checking Neo4j connection...")
    try:
        driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
        with driver.session() as session:
            # Simple query to check connection
            result = session.run("RETURN 1 as n").single()
            if result and result["n"] == 1:
                print("✅ Successfully connected to Neo4j database")
                return True
    except ServiceUnavailable:
        print("❌ Failed to connect to Neo4j database. Is it running?")
        print(f"   Connection URL: {URL}")
        print("   Please make sure Neo4j is running and try again.")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Neo4j: {e}")
        return False
    finally:
        driver.close()
    return False

def check_email_exists(tx, email_id):
    """Check if an email with the given ID exists in the database."""
    query = "MATCH (e:Email {id: $id}) RETURN count(e) > 0 as exists"
    result = tx.run(query, id=email_id)
    return result.single()["exists"]

def bulk_create_persons(tx, persons):
    query = """
    UNWIND $batch AS row
    MERGE (p:Person {id: row.id})
    SET p.email = row.email
    """
    tx.run(query, batch=persons)

def bulk_create_emails(tx, emails):
    query = """
    UNWIND $batch AS row
    MERGE (e:Email {id: row.id})
    SET e.time = row.time, e.thread = row.thread, e.body = row.body, e.filepath = row.filepath
    """
    tx.run(query, batch=emails)

def bulk_create_sent_relationships(tx, rels):
    query = """
    UNWIND $batch AS row
    MATCH (p:Person {id: row.person_id}), (e:Email {id: row.email_id})
    MERGE (p)-[:SENT]->(e)
    """
    tx.run(query, batch=rels)

def bulk_create_received_relationships(tx, rels, rel_type):
    rel_map = {
        'RECEIVED': 'RECEIVED',
        'RECEIVED_CC': 'RECEIVED_CC',
        'RECEIVED_BCC': 'RECEIVED_BCC',
    }
    query = f"""
    UNWIND $batch AS row
    MATCH (e:Email {{id: row.email_id}}), (p:Person {{id: row.person_id}})
    MERGE (e)-[:{rel_map[rel_type]}]->(p)
    """
    tx.run(query, batch=rels)

def main():
    limit_data = False
    if len(sys.argv) != 1 and len(sys.argv) != 3:
        print("Usage: \n\tpython neo4j_uploader_bulk.py \n\tpython neo4j_uploader_bulk.py <max_emails> <max_users>")
        sys.exit(1)
    elif len(sys.argv) == 3:
        try:
            max_emails = int(sys.argv[1])
            max_users = int(sys.argv[2])
            limit_data = True
        except ValueError:
            print("Invalid value provided for max_emails or max_users. Please provide integers.")
            sys.exit(1)

    if not check_neo4j_connection():
        sys.exit(1)

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
        users_items = list(all_users_data.items())[:max_users]
        users_data = dict(users_items)
        messages_data = all_messages_data[:max_emails]
        print(f"Limiting data to {len(messages_data)} emails and {len(users_data)} users.")
    else:
        users_data = all_users_data
        messages_data = all_messages_data
        print(f"Processing all {len(messages_data)} emails and {len(users_data)} users.")

    driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        start_time = time.time()
        
        # --- Process Person nodes ---
        print("Processing Person nodes...")
        persons = [{"id": pid, "email": email} for email, pid in users_data.items()]
        session.execute_write(bulk_create_persons, persons)
        
        # --- Process Email nodes with batch resume functionality ---
        # Convert messages to email objects
        emails = []
        for idx, message in enumerate(messages_data):
            emails.append({
                "id": str(idx),
                "time": message.get("time", ""),
                "thread": message.get("thread", ""),
                "body": message.get("message", ""),
                "filepath": message.get("filepath", "")
            })
        
        # Calculate number of batches
        num_batches = (len(emails) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"Total email batches: {num_batches}")
        
        # Find the first batch where the first email doesn't exist
        start_batch = None
        for batch_num in tqdm(range(num_batches), desc="Finding resume point"):
            start_idx = batch_num * BATCH_SIZE
            if start_idx < len(emails):
                first_email_id = emails[start_idx]["id"]
                exists = session.read_transaction(check_email_exists, first_email_id)
                
                # If we find a batch where the first email doesn't exist, and we've seen at least one batch
                # that exists, go back one batch to ensure we don't miss any emails
                if not exists:
                    # Start from the previous batch if this isn't the first batch
                    start_batch = max(0, batch_num - 1) if batch_num > 0 else 0
                    print(f"Resume point found: Batch {start_batch} (emails {start_batch * BATCH_SIZE} to {min((start_batch + 1) * BATCH_SIZE - 1, len(emails) - 1)})")
                    break
        
        # If all batches exist, we're done with email processing
        if start_batch is None:
            print("All email batches appear to be already processed.")
            start_batch = num_batches  # Skip all batches
        
        # Process emails from the determined starting point
        for batch_num in tqdm(range(start_batch, num_batches), desc="Bulk inserting Email nodes"):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(emails))
            if start_idx < len(emails):
                batch = emails[start_idx:end_idx]
                session.execute_write(bulk_create_emails, batch)
        
        # --- Process relationships similarly with batch resume functionality ---
        # Create sent relationships
        sent_rels = []
        for idx, message in enumerate(messages_data):
            sender_id = message.get("sender")
            if sender_id is not None and sender_id in users_data.values():
                sent_rels.append({"person_id": sender_id, "email_id": str(idx)})
        
        # Process sent relationships in batches
        start_batch = None
        num_batches = (len(sent_rels) + BATCH_SIZE - 1) // BATCH_SIZE
        
        # Only check for resume point if we have sent relationships to process
        if sent_rels:
            for batch_num in tqdm(range(num_batches), desc="Finding sent relationships resume point"):
                start_idx = batch_num * BATCH_SIZE
                if start_idx < len(sent_rels):
                    # Check if the first email in this batch exists
                    first_email_id = sent_rels[start_idx]["email_id"]
                    exists = session.read_transaction(check_email_exists, first_email_id)
                    
                    if not exists:
                        start_batch = max(0, batch_num - 1) if batch_num > 0 else 0
                        print(f"Sent relationships resume point: Batch {start_batch}")
                        break
        
        if start_batch is None and sent_rels:
            print("All sent relationship batches appear to be already processed.")
            start_batch = num_batches  # Skip all batches
        elif not sent_rels:
            start_batch = 0
        
        for batch_num in tqdm(range(start_batch, num_batches), desc="Bulk inserting SENT relationships"):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(sent_rels))
            if start_idx < len(sent_rels):
                batch = sent_rels[start_idx:end_idx]
                session.execute_write(bulk_create_sent_relationships, batch)
        
        # --- Process received relationships ---
        received_rels = []
        received_cc_rels = []
        received_bcc_rels = []
        
        for idx, message in enumerate(messages_data):
            for rec in message.get("recipients", []):
                if rec in users_data.values():
                    received_rels.append({"email_id": str(idx), "person_id": rec})
            for cc in message.get("cc", []):
                if cc in users_data.values():
                    received_cc_rels.append({"email_id": str(idx), "person_id": cc})
            for bcc in message.get("bcc", []):
                if bcc in users_data.values():
                    received_bcc_rels.append({"email_id": str(idx), "person_id": bcc})
        
        # Process each type of received relationship with batch resume capability
        for rels, rel_type, desc in [
            (received_rels, 'RECEIVED', "RECEIVED relationships"),
            (received_cc_rels, 'RECEIVED_CC', "RECEIVED_CC relationships"),
            (received_bcc_rels, 'RECEIVED_BCC', "RECEIVED_BCC relationships")
        ]:
            start_batch = None
            num_batches = (len(rels) + BATCH_SIZE - 1) // BATCH_SIZE
            
            # Only check for resume point if we have relationships to process
            if rels:
                for batch_num in tqdm(range(num_batches), desc=f"Finding {rel_type} resume point"):
                    start_idx = batch_num * BATCH_SIZE
                    if start_idx < len(rels):
                        # Check if the first email in this batch exists
                        first_email_id = rels[start_idx]["email_id"]
                        exists = session.read_transaction(check_email_exists, first_email_id)
                        
                        if not exists:
                            start_batch = max(0, batch_num - 1) if batch_num > 0 else 0
                            print(f"{rel_type} relationships resume point: Batch {start_batch}")
                            break
            
            if start_batch is None and rels:
                print(f"All {rel_type} relationship batches appear to be already processed.")
                start_batch = num_batches  # Skip all batches
            elif not rels:
                start_batch = 0
            
            for batch_num in tqdm(range(start_batch, num_batches), desc=f"Bulk inserting {rel_type} relationships"):
                start_idx = batch_num * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(rels))
                if start_idx < len(rels):
                    batch = rels[start_idx:end_idx]
                    session.execute_write(bulk_create_received_relationships, batch, rel_type)
        
        end_time = time.time()
        print(f"Bulk import complete in {end_time - start_time:.2f} seconds.")
    driver.close()

if __name__ == "__main__":
    main()
