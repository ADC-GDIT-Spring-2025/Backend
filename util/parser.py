import re
from os import path, listdir
import sys
import json
from tqdm import tqdm
import logging

#
# Precompiled regular expression patterns for email parsing
# These patterns are compiled once for performance optimization when processing many emails
#
time_pattern = re.compile(r"Date: (?P<data>[A-Z][a-z]+, \d{1,2} [A-Z][a-z]+ \d{4} \d{2}:\d{2}:\d{2} -\d{4} \([A-Z]{3}\))")
subject_pattern = re.compile(r"Subject: (?P<data>.*)")
sender_pattern = re.compile(r"From: (?P<data>.*)")
recipient_pattern = re.compile(r"To: (?P<data>.*)")
cc_pattern = re.compile(r"cc: (?P<data>.*)")
bcc_pattern = re.compile(r"bcc: (?P<data>.*)")
msg_start_pattern = re.compile(r"\n\n", re.MULTILINE)  # Email body typically starts after two newlines
msg_end_pattern = re.compile(r"\n+.*\n\d+/\d+/\d+ \d+:\d+ [AP]M", re.MULTILINE)  # Pattern to detect end of message in replies

# Global data structures to store parsed email information
feeds = []  # List to store all parsed email data
users = {}  # Dictionary mapping user email addresses to unique IDs
threads = {}  # Dictionary mapping email subjects to unique thread IDs
thread_users = {}  # Dictionary mapping thread IDs to sets of user IDs involved in that thread
user_threads = {}  # Dictionary mapping user IDs to sets of thread IDs they're involved in

def count_files(pathname):
    """
    Recursively count the number of files in a directory.
    
    Args:
        pathname (str): Path to the directory or file to count
        
    Returns:
        int: Total number of files found
        
    This function is used to determine the total for the progress bar.
    """
    if path.isdir(pathname):
        total_files = 0
        for child in listdir(pathname):
            if child[0] != ".":  # Skip hidden files
                total_files += count_files(path.join(pathname, child))
        return total_files
    else:
        return 1  # Count this file

def parse_email(pathname, orig=True, progress_bar=None):
    """
    Recursively parse email files from a directory or single file.
    
    Args:
        pathname (str): Path to the directory or file to parse
        orig (bool): Whether this is the original (top-level) call
        progress_bar (tqdm): Progress bar object for tracking
        
    Returns:
        None
        
    Effects:
        - Populates global data structures with parsed email information
        - Writes JSON output files when processing is complete (if orig=True)
    """
    if orig:
        total_files = count_files(pathname)  # Count total files for progress bar
        print(f"Total files to process: {total_files}")
        progress_bar = tqdm(total=total_files, desc="Processing files", unit="file")  # Overall progress bar

    if path.isdir(pathname):
        progress_bar.write(f"Processing directory: {pathname}")  # Use write for directory messages
        for child in listdir(pathname):
            if child[0] != ".":
                parse_email(path.join(pathname, child), False, progress_bar)
    else:
        # Process individual email file
        with open(pathname, encoding='utf-8', errors='replace') as TextFile:
            text = TextFile.read().replace("\r", "")
            # Skip characters outside of Unicode range
            text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
            try:
                # Extract email metadata
                time = time_pattern.search(text).group("data").replace("\n", "")
                subject = subject_pattern.search(text).group("data").replace("\n", "")
                sender = sender_pattern.search(text).group("data").replace("\n", "")
                recipient = recipient_pattern.search(text).group("data").split(", ")
                cc = cc_pattern.search(text).group("data").split(", ")
                bcc = bcc_pattern.search(text).group("data").split(", ")
                
                # Extract email body
                msg_start_iter = msg_start_pattern.search(text).end()
                try:
                    msg_end_iter = msg_end_pattern.search(text).start()
                    message = text[msg_start_iter:msg_end_iter]
                except AttributeError:  # not a reply
                    message = text[msg_start_iter:]
                
                # Clean up the message text to avoid errors from special characters
                message = re.sub("[\n\r]", " ", message)
                message = re.sub("  +", " ", message)
            except AttributeError:
                logging.error("Failed to parse %s" % pathname)
                return None
                
            # Get or create unique IDs for users and threads
            sender_id = get_or_allocate_uid(sender)
            recipient_id = [get_or_allocate_uid(u.replace("\n", "")) for u in recipient if u!=""]
            cc_ids = [get_or_allocate_uid(u.replace("\n", "")) for u in cc if u!=""]
            bcc_ids = [get_or_allocate_uid(u.replace("\n", "")) for u in bcc if u!=""]
            thread_id = get_or_allocate_tid(subject)
            
        # Initialize thread_users dictionary entry if needed
        if thread_id not in thread_users:
            thread_users[thread_id] = set()
            
        # Track all users involved in this email thread
        users_involved = []
        users_involved.append(sender_id)
        users_involved.extend(recipient_id)
        users_involved.extend(cc_ids)
        users_involved.extend(bcc_ids)
        thread_users[thread_id] |= set(users_involved)
        
        # Update user_threads to track which threads each user is involved in
        for user in set(users_involved):
            if user not in user_threads:
                user_threads[user] = set()
            user_threads[user].add(thread_id)
 
        # Create the email entry and add it to the feeds list
        entry =  {"time": time, "thread": thread_id, "sender": sender_id, "recipient": recipient_id, "cc": cc_ids, "bcc": bcc_ids, "message": message}
        feeds.append(entry)

        # Update progress bar after processing each file
        progress_bar.update(1)

    # If this is the original call, write results to JSON files and clean up
    if orig:
        progress_bar.close()  # Close the progress bar when done
        try:
            # Write all collected data to JSON files
            with open('user_data/messages.json', 'w') as f:
                json.dump(feeds, f)
            with open('user_data/users.json', 'w') as f:
                json.dump(users, f)
            with open('user_data/threads.json', 'w') as f:
                json.dump(threads, f)
            with open('user_data/thread-users.json', 'w') as f:
                # Convert sets to lists for JSON serialization
                for thread in thread_users:
                    thread_users[thread] = list(thread_users[thread])
                json.dump(thread_users, f)
            with open('user_data/user-threads.json', 'w') as f:
                # Convert sets to lists for JSON serialization
                for user in user_threads:
                    user_threads[user] = list(user_threads[user])
                json.dump(user_threads, f)
        except IOError:
            print("Unable to write to output files, aborting")
            exit(1)

def get_or_allocate_uid(name):
    """
    Get or create a unique ID for a user email address.
    
    Args:
        name (str): Email address of a user
        
    Returns:
        int: Unique ID for this user
        
    This function ensures each unique email address gets a consistent ID.
    """
    if name not in users:
        users[name] = len(users)
    return users[name]

def get_or_allocate_tid(name):
    """
    Get or create a unique ID for an email thread based on subject.
    
    Args:
        name (str): Email subject line
        
    Returns:
        int: Unique ID for this thread
        
    This function removes common prefixes like "RE:" or "Fwd:" to group
    related emails into the same thread.
    """
    parsed_name = re.sub("(RE|Re|FWD|Fwd): ", "", name)
    if parsed_name not in threads:
        threads[parsed_name] = len(threads)
    return threads[parsed_name]

# Main execution block - run the parser if this script is called directly
try:
    parse_email(sys.argv[1])
except Exception as e:
    logging.error(f"Error: {e}")
    logging.error(f"Error: Specify a file path to parse.")
    logging.error(f"Usage: python parser.py <file_path>")
    exit(1)