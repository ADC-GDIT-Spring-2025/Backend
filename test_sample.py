from util.enron_parser import EnronMaildirParser
from util.node_models import Email
import json
import os

def print_section(title, content):
    print(f"\n{'='*20} {title} {'='*20}")
    print(content)

class SampleEnronParser(EnronMaildirParser):
    """Parser that only processes specific mailboxes"""
    
    def __init__(self, maildir_path: str, target_people: list[str]):
        super().__init__(maildir_path)
        self.target_people = target_people
    
    def iter_emails(self):
        """Override to only process specific mailboxes"""
        for person in self.target_people:
            person_dir = os.path.join(self.mail_dir, person)
            if not os.path.exists(person_dir):
                self.logger.warning(f"Directory not found for {person}")
                continue
                
            self.logger.info(f"Processing mailbox: {person}")
            
            # Walk through person's directory
            for root, _, files in os.walk(person_dir):
                folder_name = os.path.relpath(root, self.mail_dir)
                files_to_process = [f for f in files if not f.startswith('.')]
                
                if not files_to_process:
                    continue
                    
                self.logger.info(f"Processing folder: {folder_name} ({len(files_to_process)} files)")
                
                for file in files_to_process:
                    file_path = os.path.join(root, file)
                    if file_path in self._processed_files:
                        continue
                    
                    try:
                        email = Email.from_file(file_path)
                        self._processed_files.add(file_path)
                        self.stats.files_processed += 1
                        
                        # Track attachment statistics
                        if email.attachments:
                            self.stats.emails_with_attachments += 1
                            self.stats.total_attachments += len(email.attachments)
                        
                        yield email
                        
                    except Exception as e:
                        self.stats.files_errored += 1
                        self.stats.parse_errors[str(e)] += 1
                        self.logger.error(f"Error processing {file_path}: {str(e)}")

def main():
    # Select 3 interesting mailboxes to process
    target_people = [
        'lay-k',      # Ken Lay (CEO)
        'skilling-j', # Jeff Skilling (CEO)
        'fastow-a'    # Andrew Fastow (CFO)
    ]
    
    # Initialize parser with target people
    parser = SampleEnronParser("data/maildir", target_people)
    
    # Process emails
    parser.process_maildir()
    
    # Print parsing statistics
    print_section("Parsing Statistics", json.dumps(parser.stats.to_dict(), indent=2))
    
    # Print dataset overview
    avg_emails_per_thread = f"{(len(parser.emails) / len(parser.threads)):.2f}" if len(parser.threads) > 0 else "N/A"
    print_section("Dataset Overview", f"""
        Total Unique People: {len(parser.people)}
        Total Emails: {len(parser.emails)}
        Total Email Threads: {len(parser.threads)}
        Average Emails per Thread: {avg_emails_per_thread}
        Emails with Attachments: {parser.stats.emails_with_attachments}
        Total Attachments: {parser.stats.total_attachments}
    """.strip())
    
    # Print email counts by person
    email_counts = defaultdict(int)
    for email in parser.emails.values():
        email_counts[email.sender.email] += 1
    
    print_section("Emails per Person", "\n".join(
        f"{parser.people[email].name or 'Unknown'} ({email}): {count} emails"
        for email, count in sorted(email_counts.items(), key=lambda x: x[1], reverse=True)
    ))
    
    # Print largest threads
    thread_sizes = {
        thread_id: len(thread.emails)
        for thread_id, thread in parser.threads.items()
    }
    
    print_section("Largest Email Threads", "\n".join(
        f"Thread {thread_id}: {size} emails"
        for thread_id, size in sorted(thread_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    ))
    
    # Print attachment statistics
    if parser.stats.emails_with_attachments > 0:
        attachment_types = defaultdict(int)
        for email in parser.emails.values():
            for attachment in email.attachments:
                attachment_types[attachment.content_type] += 1
        
        print_section("Attachment Types", "\n".join(
            f"{content_type}: {count} files"
            for content_type, count in sorted(attachment_types.items(), key=lambda x: x[1], reverse=True)
        ))

if __name__ == "__main__":
    from collections import defaultdict
    main() 