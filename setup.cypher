// --- Step 1: Create Constraints and Indexes ---
CREATE CONSTRAINT unique_person_email FOR (p:Person) REQUIRE p.email IS UNIQUE;
CREATE CONSTRAINT unique_email_messageId FOR (e:Email) REQUIRE e.messageId IS UNIQUE;
CREATE CONSTRAINT unique_attachment_filename FOR (a:Attachment) REQUIRE a.fileName IS UNIQUE;

// --- Step 2: Create Nodes ---
// Create Enron Employees
CREATE (:Person {name: "Jeff Skilling", title: "CEO", email: "jeff.skilling@enron.com"});
CREATE (:Person {name: "Kenneth Lay", title: "Chairman", email: "ken.lay@enron.com"});
CREATE (:Person {name: "Andrew Fastow", title: "CFO", email: "andrew.fastow@enron.com"});
CREATE (:Person {name: "Rebecca Mark", title: "Exec VP", email: "rebecca.mark@enron.com"});
CREATE (:Person {name: "Richard Causey", title: "Chief Accounting Officer", email: "richard.causey@enron.com"});

// Create Sample Emails from the Enron Dataset
CREATE (:Email {messageId: "E1001", subject: "Financial Reports Q4", content: "Please review the latest financial results for Q4.", date: datetime("2000-12-15T09:00:00")});
CREATE (:Email {messageId: "E1002", subject: "Meeting on Risk Exposure", content: "We need to discuss risk exposure from our off-balance sheet transactions.", date: datetime("2001-02-20T14:30:00")});
CREATE (:Email {messageId: "E1003", subject: "SEC Investigation", content: "The SEC has requested additional financial disclosures.", date: datetime("2001-07-10T16:00:00")});

// Create Sample Attachments
CREATE (:Attachment {fileName: "q4_financials.pdf", fileType: "PDF", size: "1.2MB"});
CREATE (:Attachment {fileName: "risk_analysis.xls", fileType: "Excel", size: "600KB"});
CREATE (:Attachment {fileName: "sec_request.doc", fileType: "Word", size: "450KB"});

// --- Step 3: Create Relationships ---
// Jeff Skilling sent an email about Financial Reports Q4
MATCH (p:Person {email: "jeff.skilling@enron.com"}), (e:Email {messageId: "E1001"})
CREATE (p)-[:SENT_EMAIL]->(e);

// Email about Financial Reports was received by Kenneth Lay
MATCH (e:Email {messageId: "E1001"}), (p:Person {email: "ken.lay@enron.com"})
CREATE (e)-[:RECEIVED_EMAIL_TO]->(p);

// Email about Risk Exposure was sent by Andrew Fastow and received by Rebecca Mark
MATCH (p:Person {email: "andrew.fastow@enron.com"}), (e:Email {messageId: "E1002"})
CREATE (p)-[:SENT_EMAIL]->(e);

MATCH (e:Email {messageId: "E1002"}), (p:Person {email: "rebecca.mark@enron.com"})
CREATE (e)-[:RECEIVED_EMAIL_TO]->(p);

// Email about SEC Investigation was sent by Richard Causey and received by Jeff Skilling
MATCH (p:Person {email: "richard.causey@enron.com"}), (e:Email {messageId: "E1003"})
CREATE (p)-[:SENT_EMAIL]->(e);

MATCH (e:Email {messageId: "E1003"}), (p:Person {email: "jeff.skilling@enron.com"})
CREATE (e)-[:RECEIVED_EMAIL_TO]->(p);

// Attachments to Emails
MATCH (e:Email {messageId: "E1001"}), (a:Attachment {fileName: "q4_financials.pdf"})
CREATE (e)-[:HAS_ATTACHMENT]->(a);

MATCH (e:Email {messageId: "E1002"}), (a:Attachment {fileName: "risk_analysis.xls"})
CREATE (e)-[:HAS_ATTACHMENT]->(a);

MATCH (e:Email {messageId: "E1003"}), (a:Attachment {fileName: "sec_request.doc"})
CREATE (e)-[:HAS_ATTACHMENT]->(a);

// --- Step 4: Query the Database (Optional) ---
// Return all emails sent by Jeff Skilling
MATCH (p:Person {name: "Jeff Skilling"})-[:SENT_EMAIL]->(e:Email)
RETURN e.subject, e.content, e.date;

// Return all recipients of the Financial Reports Q4 email
MATCH (e:Email {messageId: "E1001"})-[:RECEIVED_EMAIL_TO]->(p:Person)
RETURN p.name, p.email;

// Return all emails related to Risk Exposure
MATCH (e:Email {subject: "Meeting on Risk Exposure"})-[:RECEIVED_EMAIL_TO|SENT_EMAIL]->(p:Person)
RETURN e.subject, e.content, p.name;

// Return all attachments for the SEC Investigation email
MATCH (e:Email {messageId: "E1003"})-[:HAS_ATTACHMENT]->(a:Attachment)
RETURN a.fileName, a.fileType, a.size;


