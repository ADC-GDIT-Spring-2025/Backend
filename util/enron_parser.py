import re
from os import path, listdir
import sys
import json
from tqdm import tqdm

#
# Precompiled patterns for performance
#
time_pattern = re.compile("Date: (?P<data>[A-Z][a-z]+\, \d{1,2} [A-Z][a-z]+ \d{4} \d{2}\:\d{2}\:\d{2} \-\d{4} \([A-Z]{3}\))")
subject_pattern = re.compile("Subject: (?P<data>.*)")
sender_pattern = re.compile("From: (?P<data>.*)")
recipient_pattern = re.compile("To: (?P<data>.*)")
cc_pattern = re.compile("cc: (?P<data>.*)")
bcc_pattern = re.compile("bcc: (?P<data>.*)")
msg_start_pattern = re.compile("\n\n", re.MULTILINE)
msg_end_pattern = re.compile("\n+.*\n\d+/\d+/\d+ \d+:\d+ [AP]M", re.MULTILINE)

#
# Function: parse_email
# Arguments: pathname - relative path of folder/file to be parsed
#            orig     - whether this call is the original, used for writing to file
#            progress_bar - progress bar for tracking progress
# Returns: none
# Effects: dumps json into file
#
feeds = []
users = {}
threads = {}
thread_users = {}
user_threads = {}

def count_files(pathname):
    """Recursively count the number of files in the directory."""
    if path.isdir(pathname):
        total_files = 0
        for child in listdir(pathname):
            if child[0] != ".":  # Skip hidden files
                total_files += count_files(path.join(pathname, child))
        return total_files
    else:
        return 1  # Count this file

def parse_email(pathname, orig=True, progress_bar=None):
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
        # progress_bar.write(f"Processing file: {pathname}")  # Use write for file messages
        # Open the file with error handling for invalid characters
        with open(pathname, encoding='utf-8', errors='replace') as TextFile:
            text = TextFile.read().replace("\r", "")
            # Skip characters outside of Unicode range
            text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
            try:
                time = time_pattern.search(text).group("data").replace("\n", "")
                subject = subject_pattern.search(text).group("data").replace("\n", "")
                sender = sender_pattern.search(text).group("data").replace("\n", "")
                recipient = recipient_pattern.search(text).group("data").split(", ")
                cc = cc_pattern.search(text).group("data").split(", ")
                bcc = bcc_pattern.search(text).group("data").split(", ")
                msg_start_iter = msg_start_pattern.search(text).end()
                try:
                    msg_end_iter = msg_end_pattern.search(text).start()
                    message = text[msg_start_iter:msg_end_iter]
                except AttributeError:  # not a reply
                    message = text[msg_start_iter:]
                message = re.sub("[\n\r]", " ", message)
                message = re.sub("  +", " ", message)
            except AttributeError:
                logging.error("Failed to parse %s" % pathname)
                return None
            # get user and thread ids
            sender_id = get_or_allocate_uid(sender)
            recipient_id = [get_or_allocate_uid(u.replace("\n", "")) for u in recipient if u!=""]
            cc_ids = [get_or_allocate_uid(u.replace("\n", "")) for u in cc if u!=""]
            bcc_ids = [get_or_allocate_uid(u.replace("\n", "")) for u in bcc if u!=""]
            thread_id = get_or_allocate_tid(subject)
        if thread_id not in thread_users:
            thread_users[thread_id] = set()
        # maintain list of users involved in thread
        users_involved = []
        users_involved.append(sender_id)
        users_involved.extend(recipient_id)
        users_involved.extend(cc_ids)
        users_involved.extend(bcc_ids)
        thread_users[thread_id] |= set(users_involved)
        # maintain list of threads where user is involved
        for user in set(users_involved):
            if user not in user_threads:
                user_threads[user] = set()
            user_threads[user].add(thread_id)
 
        entry =  {"time": time, "thread": thread_id, "sender": sender_id, "recipient": recipient_id, "cc": cc_ids, "bcc": bcc_ids, "message": message}
        feeds.append(entry)

        # Update progress bar after processing each file
        progress_bar.update(1)  # Update progress bar after processing each file

    if orig:
        progress_bar.close()  # Close the progress bar when done
        try:
            with open('messages2.json', 'w') as f:
                json.dump(feeds, f)
            with open('users2.json', 'w') as f:
                json.dump(users, f)
            with open('threads2.json', 'w') as f:
                json.dump(threads, f)
            with open('thread-users2.json', 'w') as f:
                for thread in thread_users:
                    thread_users[thread] = list(thread_users[thread])
                json.dump(thread_users, f)
            with open('user-threads2.json', 'w') as f:
                for user in user_threads:
                    user_threads[user] = list(user_threads[user])
                json.dump(user_threads, f)
        except IOError:
            print("Unable to write to output files, aborting")
            exit(1)

#
# Function: get_or_allocated_uid
# Arguments: name - string of a user email
# Returns: unique integer id
#
def get_or_allocate_uid(name):
     if name not in users:
         users[name] = len(users)
     return users[name]

#
# Function: get_or_allocate_tid
# Arguments: name - string of email subject line
# Returns: unique integer id
#
def get_or_allocate_tid(name):
    parsed_name = re.sub("(RE|Re|FWD|Fwd): ", "", name)
    if parsed_name not in threads:
        threads[parsed_name] = len(threads)
    return threads[parsed_name]

parse_email(sys.argv[1])