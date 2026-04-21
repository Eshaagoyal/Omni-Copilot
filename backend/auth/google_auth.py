import os, logging, base64
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from tenacity import retry, wait_exponential, stop_after_attempt
from cachetools import cached, TTLCache
from .security import save_token, load_token

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def _config():
    return {"web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI",
            "http://localhost:8000/auth/google/callback")],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }}


def get_auth_url() -> str:
    flow = Flow.from_client_config(_config(), scopes=SCOPES)
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    url, _ = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    return url


def handle_callback(code: str) -> dict:
    flow = Flow.from_client_config(_config(), scopes=SCOPES)
    flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    flow.fetch_token(code=code)
    c = flow.credentials
    save_token("google", {
        "access_token": c.token,
        "refresh_token": c.refresh_token,
        "token_uri": c.token_uri,
        "client_id": c.client_id,
        "client_secret": c.client_secret,
        "scopes": list(c.scopes or []),
        "expiry": c.expiry.isoformat() if c.expiry else None,
    })
    return {"status": "connected", "scopes": list(c.scopes or [])}


def get_credentials():
    data = load_token("google")
    if not data:
        return None
    creds = Credentials(
        token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=data["scopes"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data["access_token"] = creds.token
        save_token("google", data)
    return creds

    


@cached(cache=TTLCache(maxsize=100, ttl=60))
@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=10))
def list_emails(max_results=10, query="") -> list[dict]:
    creds = get_credentials()
    if not creds:
        return []
    svc = build("gmail", "v1", credentials=creds)
    msgs = svc.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute().get("messages", [])
    result = []
    for m in msgs:
        d = svc.users().messages().get(
            userId="me", id=m["id"], format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"]
        ).execute()
        hdrs = {h["name"]: h["value"]
                for h in d.get("payload", {}).get("headers", [])}
        result.append({
            "id": m["id"],
            "from": hdrs.get("From", ""),
            "subject": hdrs.get("Subject", ""),
            "date": hdrs.get("Date", ""),
            "status": "UNREAD" if "UNREAD" in d.get("labelIds", []) else "READ",
        })
    return result


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=10))
def get_email_body(message_id: str) -> str:
    creds = get_credentials()
    if not creds:
        return ""
    svc = build("gmail", "v1", credentials=creds)
    try:
        msg = svc.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        def extract(part):
            if part.get("mimeType") == "text/plain":
                raw = part.get("body", {}).get("data", "")
                return base64.urlsafe_b64decode(
                    raw + "==").decode("utf-8", errors="ignore")
            for p in part.get("parts", []):
                r = extract(p)
                if r:
                    return r
            return ""
        return extract(msg.get("payload", {}))
    except Exception as e:
        return f"Error fetching email (ID may be hallucinated/invalid): {e}"


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=10))
def search_emails(query: str, max_results=10) -> list[dict]:
    return list_emails(max_results=max_results, query=query)


@cached(cache=TTLCache(maxsize=100, ttl=60))
@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=10))
def list_drive_files(folder_id=None, query="", max_results=20) -> list:
    creds = get_credentials()
    if not creds:
        return []
    svc = build("drive", "v3", credentials=creds)
    q_parts = []
    if folder_id: q_parts.append(f"'{folder_id}' in parents")
    if query: q_parts.append(f"(fullText contains '{query}' or name contains '{query}')")
    q = " and ".join(q_parts) if q_parts else ""
    return svc.files().list(
        pageSize=max_results,
        fields="files(id,name,mimeType,modifiedTime,size)",
        q=q,
    ).execute().get("files", [])


@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=10))
def get_drive_file_content(file_id: str) -> str:
    creds = get_credentials()
    if not creds:
        return ""
    svc = build("drive", "v3", credentials=creds)
    try:
        # LLM Hallucination Interceptor: If AI passed a literal filename instead of an ID, auto-resolve it seamlessly.
        if ".pdf" in file_id.lower() or " " in file_id or len(file_id) < 20:
            clean_name = file_id.replace('.pdf', '').replace('.PDF', '').strip().replace("'", "")
            query = f"name contains '{clean_name}' and trashed = false"
            search_res = svc.files().list(q=query, fields="files(id)", pageSize=1).execute()
            files = search_res.get("files", [])
            if files:
                file_id = files[0]["id"]
            else:
                return f"Error: Could not find any document matching the name '{file_id}'. IMPORTANT: DO NOT LOOP! Please inform the user immediately that the file was not found."

        file_metadata = svc.files().get(fileId=file_id, fields="mimeType, name, size").execute()
        mime_type = file_metadata.get("mimeType", "")
        
        # OOM Protection: Do not download files larger than 20MB into RAM natively
        file_size = int(file_metadata.get("size", 0))
        if file_size > 20 * 1024 * 1024:
            return f"Error: File '{file_metadata.get('name')}' is too large ({file_size / 1024 / 1024:.1f} MB). Maximum allowed is 20MB."
        
        # Native Google Docs support dynamic text export
        if "vnd.google-apps" in mime_type:
            content = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
            return (content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content))
            
        # Binary PDFs require raw download and PyMuPDF (fitz) parsing
        elif mime_type == "application/pdf":
            import io
            import fitz
            from googleapiclient.http import MediaIoBaseDownload
            
            request = svc.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            fh.seek(0)
            doc = fitz.open("pdf", fh.read())
            text = "".join(page.get_text() for page in doc)
            
            if len(text.strip()) < 5:
                try:
                    from groq import Groq
                    fh.seek(0)
                    doc = fitz.open("pdf", fh.read())
                    if len(doc) > 0:
                        pix = doc[0].get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                        
                        import requests
                        payload = {
                            'apikey': 'helloworld',
                            'language': 'eng',
                            'isOverlayRequired': False,
                            'base64Image': f'data:image/png;base64,{img_b64}'
                        }
                        r = requests.post('https://api.ocr.space/parse/image', data=payload, timeout=25)
                        result = r.json()
                        vision_text = ""
                        if result.get("ParsedResults"):
                            vision_text = result["ParsedResults"][0].get("ParsedText", "").strip()
                            
                        if not vision_text:
                            vision_text = "[Notice: Image OCR found very little text in this scanned document.]"
                            
                        return f"--- PDF Document (Analyzed via Vision OCR): {file_metadata.get('name', 'Unknown')} ---\n" + vision_text
                except Exception as ve:
                    logger.error(f"Vision OCR Error: {ve}")
                    return f"System Error: The PDF is a scanned image, and OCR extraction failed: {ve}"
                
                return f"System Error: The PDF '{file_metadata.get('name', 'Unknown')}' appears to be a scanned image, and no text could be extracted."
                
            return f"--- PDF Document: {file_metadata.get('name', 'Unknown')} ---\n" + text
            
        else:
            return f"System Error: The Copilot currently cannot read the binary format: {mime_type}."
            
    except Exception as e:
        logger.error(f"Drive read error: {e}")
        return f"System Error: Failed to read file from Drive API - {str(e)}"


def send_gmail_email(to: str, subject: str, message_text: str) -> str:
    """Send an email from the user's Gmail account using MIME structure."""
    creds = get_credentials()
    if not creds: return "Error: Google account is not connected."
    
    from email.mime.text import MIMEText
    
    try:
        svc = build("gmail", "v1", credentials=creds)
        message = MIMEText(message_text)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = svc.users().messages().send(userId="me", body={'raw': raw_message}).execute()
        return f"Success! The email was securely sent. (Message ID: {sent_message.get('id')})"
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return f"System Error: Failed to send email - {str(e)}"