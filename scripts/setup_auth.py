import os, sys, webbrowser, time, requests
from dotenv import load_dotenv

load_dotenv("config/.env")

print("\n" + "="*45)
print("   Omni Copilot — Account Setup")
print("="*45 + "\n")

def chk(label, key):
    v = os.getenv(key, "")
    ok = bool(v) and not v.startswith("paste_") and not v.startswith("gsk_paste")
    print(f"  {'✓' if ok else '✗'} {label}")
    return ok

ok  = chk("GROQ_API_KEY", "GROQ_API_KEY")
ok &= chk("TOKEN_ENCRYPTION_KEY", "TOKEN_ENCRYPTION_KEY")
has_google = (chk("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_ID") and
              chk("GOOGLE_CLIENT_SECRET", "GOOGLE_CLIENT_SECRET"))
has_notion = (chk("NOTION_CLIENT_ID", "NOTION_CLIENT_ID") and
              chk("NOTION_CLIENT_SECRET", "NOTION_CLIENT_SECRET"))
print()

if not ok:
    print("❌ Fix missing values in config/.env first.\n")
    sys.exit(1)

try:
    requests.get("http://localhost:8000/health", timeout=3)
    print("✓ API server is running\n")
except Exception:
    print("✗ API server not running!")
    print("Start it first:")
    print("  uvicorn backend.api.main:app --reload --port 8000\n")
    input("Press Enter once it's running...")

if has_google:
    print("Opening Google login...")
    webbrowser.open("http://localhost:8000/auth/google")
    time.sleep(2)
    input("Press Enter AFTER approving Google in browser... ")

if has_notion:
    print("Opening Notion login...")
    webbrowser.open("http://localhost:8000/auth/notion")
    time.sleep(2)
    input("Press Enter AFTER approving Notion in browser... ")

try:
    r = requests.get(
        "http://localhost:8000/auth/status", timeout=5)
    print(f"\n✓ Connected: {r.json().get('connected_providers')}")
except Exception:
    pass

print("\n✅ Done! Now run:")
print("  streamlit run frontend/app.py")
print("  → open http://localhost:8501\n")