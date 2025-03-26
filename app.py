from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_session

app = Flask(__name__)
CORS(app)

# Get all recipients of a specific sender
@app.route("/recipients/<sender_email>", methods=["GET"])
def get_recipients(sender_email):
    session = get_session()
    try:
        query = """
        MATCH (s:Person {email: $sender_email})-[:SENT]->(e:Email)-[:TO]->(r:Person)
        RETURN DISTINCT r.email AS recipient_email
        """
        result = session.run(query, sender_email=sender_email)
        recipients = [record["recipient_email"] for record in result]

        return jsonify({"sender_email": sender_email, "recipients": recipients})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Get all messages exchanged between two specific users
@app.route("/messages/<email1>/<email2>", methods=["GET"])
def get_messages(email1, email2):
    session = get_session()
    try:
        query = """
        MATCH (p1:Person {email: $email1})-[:SENT]->(e:Email)-[:TO]->(p2:Person {email: $email2})
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        UNION
        MATCH (p2:Person {email: $email1})-[:SENT]->(e:Email)-[:TO]->(p1:Person {email: $email2})
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        ORDER BY timestamp DESC
        """
        result = session.run(query, email1=email1, email2=email2)
        messages = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"email1": email1, "email2": email2, "messages": messages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Get an email thread based on an email ID
@app.route("/thread/<email_id>", methods=["GET"])
def get_thread(email_id):
    session = get_session()
    try:
        query = """
        MATCH (e:Email {id: $email_id})<-[:REPLY_TO*0..]-(r:Email)
        RETURN r.id AS email_id, r.subject AS subject, r.body AS body, r.timestamp AS timestamp
        ORDER BY timestamp ASC
        """
        result = session.run(query, email_id=email_id)
        thread = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"email_id": email_id, "thread": thread})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Get all emails sent by a specific sender
@app.route("/sent/<sender_email>", methods=["GET"])
def get_sent_emails(sender_email):
    session = get_session()
    try:
        query = """
        MATCH (s:Person {email: $sender_email})-[:SENT]->(e:Email)
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        ORDER BY timestamp DESC
        """
        result = session.run(query, sender_email=sender_email)
        sent_emails = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"sender_email": sender_email, "sent_emails": sent_emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Get all emails received by a specific recipient
@app.route("/received/<recipient_email>", methods=["GET"])
def get_received_emails(recipient_email):
    session = get_session()
    try:
        query = """
        MATCH (e:Email)-[:TO]->(r:Person {email: $recipient_email})
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        ORDER BY timestamp DESC
        """
        result = session.run(query, recipient_email=recipient_email)
        received_emails = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"recipient_email": recipient_email, "received_emails": received_emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Get the top N most frequently contacted recipients by a sender
@app.route("/top-recipients/<sender_email>", methods=["GET"])
def get_top_recipients(sender_email):
    session = get_session()
    try:
        N = request.args.get("limit", default=5, type=int)
        query = """
        MATCH (s:Person {email: $sender_email})-[:SENT]->(e:Email)-[:TO]->(r:Person)
        RETURN r.email AS recipient_email, COUNT(*) AS count
        ORDER BY count DESC
        LIMIT $N
        """
        result = session.run(query, sender_email=sender_email, N=N)
        top_recipients = [{"recipient_email": record["recipient_email"], "count": record["count"]} for record in result]

        return jsonify({"sender_email": sender_email, "top_recipients": top_recipients})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Search for emails by subject keyword
@app.route("/search-subject/<keyword>", methods=["GET"])
def search_subject(keyword):
    session = get_session()
    try:
        query = """
        MATCH (e:Email)
        WHERE toLower(e.subject) CONTAINS toLower($keyword)
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        ORDER BY timestamp DESC
        """
        result = session.run(query, keyword=keyword)
        emails = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"keyword": keyword, "emails": emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Search for emails by body keyword
@app.route("/search-body/<keyword>", methods=["GET"])
def search_body(keyword):
    session = get_session()
    try:
        query = """
        MATCH (e:Email)
        WHERE toLower(e.body) CONTAINS toLower($keyword)
        RETURN e.id AS email_id, e.subject AS subject, e.body AS body, e.timestamp AS timestamp
        ORDER BY timestamp DESC
        """
        result = session.run(query, keyword=keyword)
        emails = [{"id": record["email_id"], "subject": record["subject"], "body": record["body"], "timestamp": record["timestamp"]} for record in result]

        return jsonify({"keyword": keyword, "emails": emails})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)