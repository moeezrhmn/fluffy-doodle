import random, string, os, redis, imapclient
from email import message_from_bytes
from email.header import decode_header


TEMP_MAIL_DOMAIN = os.getenv("TEMP_MAIL_DOMAIN")
TEMP_MAIL_USERNAME = os.getenv("TEMP_MAIL_USERNAME")
TEMP_MAIL_PASSWORD = os.getenv("TEMP_MAIL_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
EMAIL_EXPIRY = int(os.getenv("EMAIL_EXPIRY", "600"))  # 10 minutes in seconds


redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def generate_random_email(length: int = 7):
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}@{TEMP_MAIL_DOMAIN}"

def get_new_email():
    email = generate_random_email()
    # Store email in Redis with TTL
    redis_client.setex(email, EMAIL_EXPIRY, "1")
    return email

def is_email_valids(email: str) -> bool:
    """Check if the email exists in Redis and hasn't expired""" 
    return bool(redis_client.exists(email))

def get_email_ttl(email: str) -> int:
    """Get remaining time to live for the email in seconds"""
    return redis_client.ttl(email)




def fetch_emails(email: str):
    """Fetch emails from the inbox of the provided email address"""
    try:
        imap_server = imapclient.IMAPClient('imap.hostinger.com', ssl=True)
        imap_server.login(TEMP_MAIL_USERNAME, TEMP_MAIL_PASSWORD)

        # Select the inbox folder
        select_info = imap_server.select_folder('INBOX')
        print('%d messages in INBOX' % select_info[b'EXISTS'])
        
        # Search for all emails
        messages = imap_server.search(['TO', email])
        print("%d messages from our best friend" % len(messages))
        emails = []
        
        for msgid, data in imap_server.fetch(messages, ['ENVELOPE', 'BODY[]']).items():
            envelope = data[b'ENVELOPE']
            raw_body = data[b'BODY[]']

            # Parse the raw email message
            msg = message_from_bytes(raw_body)

            # Get the email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    # Look for the plain text part
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode(errors='replace')
            else:
                body = msg.get_payload(decode=True).decode(errors='replace')

            emails.append({
                "id": msgid,
                "subject": envelope.subject.decode() if envelope.subject else '',
                "from": envelope.from_,
                "sender": envelope.sender,
                "to": envelope.to,
                "cc": envelope.cc,
                "bcc": envelope.bcc,
                "date": envelope.date,
                "body": body
            })


        imap_server.logout()
        return emails
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return []