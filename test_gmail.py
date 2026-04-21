import os
from dotenv import load_dotenv
load_dotenv('config/.env')
from backend.auth.google_auth import list_emails

with open("gmail_test.txt", "w", encoding="utf-8") as f:
    f.write(str(list_emails(max_results=10, query='')) + "\n")
    f.write(str(list_emails(max_results=10, query='is:unread')) + "\n")
