import os
from util.enron_parser import EnronMaildirParser

def main():
    # Define the directories to be processed
    maildir_paths = [
        "data/test-data",
    ]
    
    # Create an instance of the parser
    parser = EnronMaildirParser(maildir_paths)
    
    # Process the emails
    parser.process_maildir(max_emails=None)  # Set max_emails to None to process all emails
    
    # Print the parsing statistics
    stats = parser.stats.to_dict()
    print("Parsing Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # print how many emails have the "in_reply_to" attribute initialized
    for i, email in enumerate(parser.emails.values()):
        print(f"{i:2}: {email.recipients}")

if __name__ == "__main__":
    main() 