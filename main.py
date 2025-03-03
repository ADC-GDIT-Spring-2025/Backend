import os
from util.enron_parser import EnronMaildirParser

def main():
    # Define the directories to be processed
    maildir_paths = [
        "data/maildir/allen-p",
        "data/maildir/buy-r"
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
    
    # Print a portion of the people found
    print("\nSample of People Found:")
    sample_people = list(parser.people.values())[:10]  # Get the first 10 people
    for person in sample_people:
        print(f"Name: {person.name}, Email: {person.email}")

if __name__ == "__main__":
    main() 