import os, base64, logging, requests
from .security import save_token, load_token

logger = logging.getLogger(__name__)
API = "https://api.notion.com/v1"
VER = "2022-06-28"


def get_auth_url() -> str:
    return (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={os.getenv('NOTION_CLIENT_ID')}"
        f"&response_type=code&owner=user"
        f"&redirect_uri={os.getenv('NOTION_REDIRECT_URI')}"
    )


def handle_callback(code: str) -> dict:
    cred = base64.b64encode(
        f"{os.getenv('NOTION_CLIENT_ID')}:"
        f"{os.getenv('NOTION_CLIENT_SECRET')}".encode()
    ).decode()
    r = requests.post(f"{API}/oauth/token",
        headers={"Authorization": f"Basic {cred}",
                 "Content-Type": "application/json",
                 "Notion-Version": VER},
        json={"grant_type": "authorization_code",
              "code": code,
              "redirect_uri": os.getenv("NOTION_REDIRECT_URI")},
        timeout=15)
    r.raise_for_status()
    data = r.json()
    save_token("notion", {
        "access_token": data["access_token"],
        "workspace_name": data.get("workspace_name"),
    })
    return {"status": "connected",
            "workspace": data.get("workspace_name")}


def _headers():
    t = load_token("notion")
    if not t:
        raise RuntimeError("Notion not connected")
    return {"Authorization": f"Bearer {t['access_token']}",
            "Content-Type": "application/json",
            "Notion-Version": VER}


def search_pages(query="", max_results=10) -> list:
    r = requests.post(f"{API}/search", headers=_headers(),
        json={"query": query,
              "filter": {"value": "page", "property": "object"},
              "page_size": max_results}, timeout=15)
    r.raise_for_status()
    out = []
    for p in r.json().get("results", []):
        title_parts = (p.get("properties", {})
                       .get("title", {}).get("title", []))
        title = "".join(t.get("plain_text", "")
                        for t in title_parts)
        out.append({"id": p["id"], "title": title,
                    "url": p.get("url"),
                    "edited": p.get("last_edited_time")})
    return out


def get_page_content(page_id: str) -> str:
    r = requests.get(
        f"{API}/blocks/{page_id}/children?page_size=100",
        headers=_headers(), timeout=15)
    r.raise_for_status()
    lines = []
    for b in r.json().get("results", []):
        bt = b.get("type", "")
        rt = b.get(bt, {}).get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in rt)
        if text:
            lines.append(text)
    return "\n".join(lines)


def append_to_page(page_id: str, content: str) -> str:
    """Appends a new paragraph block to an existing Notion page."""
    r = requests.patch(
        f"{API}/blocks/{page_id}/children",
        headers=_headers(),
        json={
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        },
        timeout=15
    )
    r.raise_for_status()
    return "Successfully appended content to Notion page."

def create_page(parent_page_id: str, title: str) -> str:
    """Creates a new Notion page as a child of the specified parent page."""
    r = requests.post(
        f"{API}/pages",
        headers=_headers(),
        json={
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        },
        timeout=15
    )
    r.raise_for_status()
    return f"Success! New page created: {title} (ID: {r.json().get('id')})"