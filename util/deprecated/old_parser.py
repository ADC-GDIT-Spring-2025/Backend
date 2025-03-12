import os
from typing import Dict, Generator, List, Set, Tuple
from tqdm import tqdm
from collections import defaultdict
from datetime import datetime
from enum import Enum

from util.deprecated.node_models import Email, Person

class EmailRelationship(Enum):
    """Relationships between two Emails"""
    REPLY = "reply"
    FORWARD = "forward"
    REFERENCE = "reference"
    IN_REPLY_TO = "in_reply_to"

class PersonEmailRelationship(Enum):
    """Relationships between Persons and Emails"""
    SENT = "sent"
    RECIEVED = "recieved"
    CC_RECIEVED = "cc_recieved"
    BCC_RECIEVED = "bcc_recieved"

class ParsingStatistics:
    """Tracks statistics during parsing"""
    def __init__(self):
        self.total_files_found = 0
        self.files_processed = 0
        self.files_errored = 0
        self.total_emails = 0
        self.emails_with_attachments = 0
        self.total_attachments = 0
        self.parse_errors = defaultdict(int)
        self.start_time = None
        self.end_time = None
        
    def to_dict(self):
        return {
            "total_files_found": self.total_files_found,
            "files_processed": self.files_processed,
            "files_errored": self.files_errored,
            "success_rate": f"{(self.files_processed / self.total_files_found * 100):.2f}%" if self.total_files_found else "0%",
            "total_emails": self.total_emails,
            "emails_with_attachments": self.emails_with_attachments,
            "total_attachments": self.total_attachments,
            "parse_errors": dict(self.parse_errors),
            "processing_time": str(self.end_time - self.start_time) if self.end_time else "N/A"
        }

class EnronMaildirParser:
    """Parser for the Enron email dataset"""
    
    def __init__(self, maildir_paths: List[str]):
        self.maildir_paths = maildir_paths  # Now accepts a list of directories
        self.emails: Dict[str, Email] = {}  # message_id -> Email
        self.people: Dict[str, Person] = {}  # email -> Person
        self._processed_files: Set[str] = set()
        self.stats = ParsingStatistics()
        
    def process_maildir(self, max_emails: int = None) -> None:
        """Process all emails in the given directories, up to a maximum number if specified"""

        # log the start time
        self.stats.start_time = datetime.now()
        
        # First count total files across all specified directories
        self.stats.total_files_found = sum(
            len([f for f in files if not f.startswith('.')])
            for maildir_path in self.maildir_paths
            for _, _, files in os.walk(maildir_path)
        )
        
        # Process emails iteratively
        email_count = 0  # Counter for processed emails
        for maildir_path in self.maildir_paths:
            for email in self.iter_emails(maildir_path):
                self._add_email(email)
                email_count += 1
                
                if max_emails is not None and email_count >= max_emails:
                    break  # Stop processing if the limit is reached
        
        # log the end time
        self.stats.end_time = datetime.now()
    
    def iter_emails(self, maildir_path: str) -> Generator[Email, None, None]:
        """Iterate through all email files in the given directory and its subdirectories"""
        print(f"Processing directory: {maildir_path}")  # //////////////////////////////////
        
        for root, _, files in os.walk(maildir_path):
            files_to_process = [f for f in files if not f.startswith('.')]
            for file in tqdm(files_to_process, desc=f"Processing emails in {root}"):
                file_path = os.path.join(root, file)

                # check if we have already processed the file
                if file_path in self._processed_files:
                    continue
                
                # try to parse the email
                try:
                    email = Email.from_file(file_path)
                    self._processed_files.add(file_path)
                    
                    self.stats.files_processed += 1
                    
                    # Track attachment statistics
                    if email.attachments:
                        print("Found email with attachments: ", email.message_id)  # /////// this never prints, no attachments are ever found
                        self.stats.emails_with_attachments += 1
                        self.stats.total_attachments += len(email.attachments)
                    
                    yield email
                    
                except Exception as e:
                    self.stats.files_errored += 1
                    self.stats.parse_errors[str(e)] += 1
    
    def _add_email(self, email: Email) -> None:
        """Add an email to the internal data structures"""
        self.stats.total_emails += 1
        
        # Store email in internal list
        self.emails[email.message_id] = email
        
        # Store people
        self._add_person(email.sender)
        for recipient in email.recipients + email.cc_recipients + email.bcc_recipients:
            self._add_person(recipient)
        
    
    def _add_person(self, person: Person) -> None:
        """Add a person to the internal data structures"""
        if person.email not in self.people:
            # add new person if they don't exist
            self.people[person.email] = person

        elif person.name and not self.people[person.email].name:
            # Update name if we find one for an existing person
            self.people[person.email].name = person.name

    
    def get_folder_structure(self) -> Dict[str, List[str]]:
        """Get the folder structure and emails in each folder"""
        structure = defaultdict(list)
        
        for email in self.emails.values():
            structure[email.folder_path].append(email.message_id)
        
        return structure
    