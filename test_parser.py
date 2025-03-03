from util.enron_parser import EnronMaildirParser
from pprint import pprint
import json
from collections import defaultdict

def print_section(title, content):
    print(f"\n{'='*20} {title} {'='*20}")
    print(content)

def main():
    # Initialize parser
    parser = EnronMaildirParser("data/maildir")
    
    # Process all emails
    parser.process_maildir()
    
    # Print parsing statistics
    print_section("Parsing Statistics", json.dumps(parser.stats.to_dict(), indent=2))
    
    # Print dataset overview
    print_section("Dataset Overview", f"""
Total Unique People: {len(parser.people)}
Total Emails: {len(parser.emails)}
Total Email Threads: {len(parser.threads)}
Average Emails per Thread: {len(parser.emails) / len(parser.threads):.2f}
Emails with Attachments: {parser.stats.emails_with_attachments}
Total Attachments: {parser.stats.total_attachments}
    """.strip())
    
    # Print sample of people with most emails sent
    sender_counts = {}
    for email in parser.emails.values():
        sender_counts[email.sender.email] = sender_counts.get(email.sender.email, 0) + 1
    
    print_section("Top 10 Email Senders", "\n".join(
        f"{parser.people[email].name or 'Unknown'} ({email}): {count} emails"
        for email, count in sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ))
    
    # Print sample of largest threads
    thread_sizes = {
        thread_id: len(thread.emails)
        for thread_id, thread in parser.threads.items()
    }
    
    print_section("Largest Email Threads", "\n".join(
        f"Thread {thread_id}: {size} emails"
        for thread_id, size in sorted(thread_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    ))
    
    # Print sample of folders with most emails
    folder_structure = parser.get_folder_structure()
    folder_sizes = {
        folder: len(emails)
        for folder, emails in folder_structure.items()
    }
    
    print_section("Largest Folders", "\n".join(
        f"{folder}: {size} emails"
        for folder, size in sorted(folder_sizes.items(), key=lambda x: x[1], reverse=True)[:5]
    ))
    
    # Print sample of most common attachment types
    attachment_types = defaultdict(int)
    for email in parser.emails.values():
        for attachment in email.attachments:
            attachment_types[attachment.content_type] += 1
    
    if attachment_types:
        print_section("Most Common Attachment Types", "\n".join(
            f"{content_type}: {count} files"
            for content_type, count in sorted(attachment_types.items(), key=lambda x: x[1], reverse=True)[:5]
        ))

if __name__ == "__main__":
    main() 