import sys
import json
import time
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
from tqdm import tqdm
import os
import logging
import copy

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Neo4j connection details (adjust these as needed)
URL = "bolt://localhost:7687"
USERNAME = "neo4j"
PASSWORD = os.environ.get("NEO4J_PASSWORD") or "cheerios4150"

BATCH_SIZE = 1000  # Tune this for your memory/DB

def check_neo4j_connection():
    """Check if Neo4j database is running and accessible."""
    logger.info("Checking Neo4j connection...")
    try:
        driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
        with driver.session() as session:
            # Simple query to check connection
            result = session.run("RETURN 1 as n").single()
            if result and result["n"] == 1:
                logger.info("✅ Successfully connected to Neo4j database")
                return True
    except ServiceUnavailable:
        logger.error("❌ Failed to connect to Neo4j database. Is it running?")
        logger.error(f"   Connection URL: {URL}")
        logger.error("   Please make sure Neo4j is running and try again.")
        return False
    except Exception as e:
        logger.error(f"❌ Error connecting to Neo4j: {e}")
        return False
    finally:
        driver.close()
    return False


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

def clear_database(tx):
    """Clear the database by deleting all nodes and relationships."""
    tx.run("MATCH (n) DETACH DELETE n")
    logger.info("Database cleared successfully.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        # Clear the database
        logger.info("Clearing the database...")
        try:
            driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
            with driver.session() as session:
                clear_database(session)
        except Exception as e:
            logger.error(f"❌ Error clearing database: {e}")
            sys.exit(1)

    # Load data from local JSON files
    try:
        with open('user_data/users.json', 'r') as f:
            all_users_data = json.load(f)
        with open('user_data/messages.json', 'r') as f:
            all_messages_data = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Error: {e}. Make sure 'user_data/users.json' and 'user_data/messages.json' exist.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {e}")
        sys.exit(1)

    logger.info("Total emails: %d", len(all_messages_data))
    logger.info("Total users: %d", len(all_users_data))


    limit_data = False

    # Get input from the user for maximum emails and maximum users to process
    while True:
        try:
            max_emails_input = input("Enter the maximum number of emails to process (press Enter to process all): ").strip()
            max_users_input = input("Enter the maximum number of users to process (press Enter to process all): ").strip()

            if max_emails_input or max_users_input:
                limit_data = True
                max_emails = int(max_emails_input) if max_emails_input else float('inf')
                max_users = int(max_users_input) if max_users_input else float('inf')
            break
        except ValueError:
            logger.error("Invalid value provided for max_emails or max_users. Please provide integers.")
    


    if limit_data:
        # Limit users data (dictionary)
        users_items = list(all_users_data.items())[:max_users]
        users_data = dict(users_items)
        # Limit messages data (list)
        messages_data = all_messages_data[:max_emails]
        logger.info(f"Limiting data to {len(messages_data)} emails and {len(users_data)} users.")
    else:
        users_data = all_users_data
        messages_data = all_messages_data
        logger.info(f"Processing all {len(messages_data)} emails and {len(users_data)} users.")


    # Check Neo4j connection before proceeding
    if not check_neo4j_connection():
        sys.exit(1)


    driver = GraphDatabase.driver(URL, auth=(USERNAME, PASSWORD))
    with driver.session() as session:
        # record start time for upload
        global_start_time = time.time()
        
        # --- PROCESS PERSON NODES ---
        logger.info("Processing Person nodes...")
        start_time = time.time()

        # Convert users to person objects
        users = [{"id": pid, "email": email} for email, pid in users_data.items()]

        # Calculate number of batches
        num_batches = (len(users) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info(f"Total person batches: {num_batches}")

        # Find the first batch where the LAST person doesn't exist
        start_batch = 0 # Default to starting from the beginning
        found_incomplete_batch = False
        for batch_num in range(num_batches):
            # Check the LAST element of the batch
            last_idx_in_batch = min((batch_num + 1) * BATCH_SIZE - 1, len(users) - 1)
            # Ensure index is valid before accessing users list
            if last_idx_in_batch >= 0 and last_idx_in_batch < len(users):
                last_person_id = users[last_idx_in_batch]["id"]
                if not session.execute_read(person_exists, last_person_id):
                    # This is the first batch that is definitely not complete. Start processing from THIS batch.
                    start_batch = batch_num
                    found_incomplete_batch = True
                    if start_batch == 0:
                        logger.info("No persons appear to be already processed. Starting from batch 0.")
                    else:
                        logger.info(f"Resume point found: Starting processing from Person Batch {start_batch} (last element of batch {batch_num} missing or batch is incomplete)")
                    break # Stop searching
                    
        if found_incomplete_batch is False:
            logger.info("All person batches appear to be already processed.")
        else:
            for batch_num in tqdm(range(start_batch, num_batches), desc="Bulk inserting Person nodes"):
                start_idx = batch_num * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(users))
                if start_idx < len(users):
                    batch = users[start_idx:end_idx]
                    session.execute_write(bulk_create_persons, batch)

            end_time = time.time()
            logger.info(f"Uploaded {len(users) - start_batch * BATCH_SIZE} Person nodes in {end_time - start_time:.2f} seconds. Skipped {start_batch} batches of already existing nodes.")
        
        # --- PROCESS EMAIL NODES ---
        start_time = time.time()
        # Convert messages to email objects
        emails = copy.deepcopy(messages_data)
        for idx, email in enumerate(emails):
            email["id"] = str(idx)  # Unique email id based on the index
        
        # Calculate number of batches
        num_batches = (len(emails) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info(f"Total email batches: {num_batches}")
        
        # Find the first batch where the LAST person doesn't exist
        start_batch = 0 # Default to starting from the beginning
        found_incomplete_batch = False
        for batch_num in range(num_batches):
            # Check the LAST element of the batch
            last_idx_in_batch = min((batch_num + 1) * BATCH_SIZE - 1, len(emails) - 1)
            # Ensure index is valid before accessing emails list
            if last_idx_in_batch >= 0 and last_idx_in_batch < len(emails):
                last_email_id = emails[last_idx_in_batch]["id"]
                if not session.execute_read(email_exists, last_email_id):
                    # This is the first batch that is definitely not complete. Start processing from THIS batch.
                    start_batch = batch_num
                    found_incomplete_batch = True
                    if start_batch == 0:
                        logger.info("No emails appear to be already processed. Starting from batch 0.")
                    else:
                        logger.info(f"Resume point found: Starting processing from Email Batch {start_batch} (last element of batch {batch_num} missing or batch is incomplete)")
                    break # Stop searching

        
        # If all batches exist, we're done with email processing
        if found_incomplete_batch is False:
            logger.info("All email batches appear to be already processed.")
        else:
            # Initialize total counters for relationships
            total_sent = 0
            total_received = 0
            total_received_cc = 0
            total_received_bcc = 0

            # Process emails from the determined starting point
            for batch_num in tqdm(range(start_batch, num_batches), desc="Bulk inserting Email nodes and relationships"):
                start_idx = batch_num * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(emails))
                if start_idx < len(emails):
                    # insert email nodes
                    batch = emails[start_idx:end_idx]
                    session.execute_write(bulk_create_emails, batch)

                    # insert sent relationships
                    sent_rels = [{"person_id": email.get("from"), "email_id": email["id"]} for email in batch if email.get("from") in users_data.values()]
                    if sent_rels:
                        session.execute_write(bulk_create_sent_relationships, sent_rels)
                        total_sent += len(sent_rels)
                        # logger.debug(f"Batch {batch_num}: Uploaded {len(sent_rels)} SENT relationships.")

                    # insert received relationships
                    received_rels = [{"email_id": email["id"], "person_id": rec} for email in batch for rec in email.get("to", []) if rec in users_data.values()]
                    received_cc_rels = [{"email_id": email["id"], "person_id": cc} for email in batch for cc in email.get("cc", []) if cc in users_data.values()]
                    received_bcc_rels = [{"email_id": email["id"], "person_id": bcc} for email in batch for bcc in email.get("bcc", []) if bcc in users_data.values()]

                    batch_received_count = 0
                    batch_received_cc_count = 0
                    batch_received_bcc_count = 0

                    if received_rels:
                        session.execute_write(bulk_create_received_relationships, received_rels, 'RECEIVED')
                        batch_received_count = len(received_rels)
                        total_received += batch_received_count
                    if received_cc_rels:
                        session.execute_write(bulk_create_received_relationships, received_cc_rels, 'RECEIVED_CC')
                        batch_received_cc_count = len(received_cc_rels)
                        total_received_cc += batch_received_cc_count
                    if received_bcc_rels:
                        session.execute_write(bulk_create_received_relationships, received_bcc_rels, 'RECEIVED_BCC')
                        batch_received_bcc_count = len(received_bcc_rels)
                        total_received_bcc += batch_received_bcc_count

                    # Log batch relationship counts (optional, can be verbose)
                    # logger.debug(f"Batch {batch_num}: Uploaded RECEIVED={batch_received_count}, RECEIVED_CC={batch_received_cc_count}, RECEIVED_BCC={batch_received_bcc_count}")


            end_time = time.time()
            processed_email_count = len(emails) - start_batch * BATCH_SIZE
            logger.info(f"Uploaded {processed_email_count} Email nodes and associated relationships in {end_time - start_time:.2f} seconds. Skipped {start_batch} batches of already existing nodes.")
            logger.info(f"Total relationships uploaded: SENT={total_sent}, RECEIVED={total_received}, RECEIVED_CC={total_received_cc}, RECEIVED_BCC={total_received_bcc}")

        global_end_time = time.time()
        logger.info(f"Bulk import complete in {global_end_time - global_start_time:.2f} seconds.")
    driver.close()

if __name__ == "__main__":
    main()
