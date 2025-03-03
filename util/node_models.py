'''
node_modules.py

This module defines the data classes used to represent nodes on our knowledge graph.

The different nodes are: Person, Attachment, Email, and EmailThread.

** this module should be updated as per the Neo4j schema **
'''

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from email.message import Message
from email.utils import parseaddr
import email
import os

@dataclass
class Person:
    """Represents an email participant (sender or recipient)"""
    email: str
    name: Optional[str] = None
    
    @classmethod
    def from_address_string(cls, address: str) -> 'Person':
        """Create a Person from an email address string (e.g. 'John Doe <john@example.com>')"""
        name, email = parseaddr(address)
        return cls(
            email=email.lower(),
            name=name if name else None
        )

@dataclass
class Attachment:
    """Represents an email attachment"""
    filename: str
    content_type: str
    content: bytes
    size: int

@dataclass
class Email:
    """Represents an email message"""
    message_id: str
    subject: str
    body: str
    date: Optional[datetime]
    sender: Person
    recipients: List[Person] = field(default_factory=list)
    cc_recipients: List[Person] = field(default_factory=list)
    bcc_recipients: List[Person] = field(default_factory=list)
    attachments: List[Attachment] = field(default_factory=list)
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    folder_path: str = ""
    
    @classmethod
    def from_file(cls, file_path: str) -> 'Email':
        """Create an Email object from a file path"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            msg = email.message_from_file(f)
            return cls.from_message(msg, file_path)
    
    @classmethod
    def from_message(cls, msg: Message, file_path: str = "") -> 'Email':
        """Create an Email object from an email.message.Message object"""
        # Extract basic metadata
        message_id = msg.get('Message-ID', '').strip('<>')
        subject = msg.get('Subject', '')
        date_str = msg.get('Date', '')
        try:
            date = email.utils.parsedate_to_datetime(date_str)
        except:
            date = None
        
        # Parse sender
        sender = Person.from_address_string(msg.get('From', ''))
        
        # Parse recipients
        to_list = []
        cc_list = []
        bcc_list = []
        
        if msg.get('To'):
            to_list = [Person.from_address_string(addr) for addr in msg.get('To', '').split(',') if addr.strip()]
        if msg.get('Cc'):
            cc_list = [Person.from_address_string(addr) for addr in msg.get('Cc', '').split(',') if addr.strip()]
        if msg.get('Bcc'):
            bcc_list = [Person.from_address_string(addr) for addr in msg.get('Bcc', '').split(',') if addr.strip()]
        
        # Extract body and attachments
        body = []
        attachments = []
        
        def process_part(part):
            """Process a message part to extract body or attachment"""
            content_type = part.get_content_type()
            content_disp = str(part.get('Content-Disposition', ''))
            
            # Handle attachments
            filename = part.get_filename()
            if filename or 'attachment' in content_disp.lower():
                try:
                    content = part.get_payload(decode=True)
                    if content:  # Only add if we could get content
                        attachments.append(Attachment(
                            filename=filename or 'unknown',
                            content_type=content_type,
                            content=content,
                            size=len(content)
                        ))
                except Exception:
                    pass  # Skip problematic attachments
                return
            
            # Handle body parts
            if content_type == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body.append(payload.decode('utf-8', errors='ignore'))
                except Exception:
                    pass
        
        # Process all parts
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                process_part(part)
        else:
            process_part(msg)
        
        # If no text body was found, try to get raw payload
        if not body:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body.append(payload.decode('utf-8', errors='ignore'))
            except:
                body.append('')
        
        # Get thread information
        in_reply_to = msg.get('In-Reply-To', '').strip('<>')
        references = []
        if msg.get('References'):
            references = [ref.strip() for ref in msg.get('References').split() if ref.strip()]
            references = [ref.strip('<>') for ref in references]  # Clean up reference IDs
        
        # Get folder path relative to maildir
        folder_path = os.path.dirname(file_path)
        
        return cls(
            message_id=message_id,
            subject=subject,
            body='\n'.join(body),
            date=date,
            sender=sender,
            recipients=to_list,
            cc_recipients=cc_list,
            bcc_recipients=bcc_list,
            attachments=attachments,
            in_reply_to=in_reply_to,
            references=references,
            folder_path=folder_path
        )

