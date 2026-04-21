🤖 Omni-Copilot
Your Personal AI Copilot for Gmail, Google Drive, Google Calendar & Notion
Ask anything about your personal data — in plain English.
Omni-Copilot connects your Gmail, Drive, Calendar, and Notion into one privacy-first AI assistant

🎯 What is Omni-Copilot?
Omni-Copilot is a locally-run AI assistant that gives you natural language access to your personal productivity data. Instead of manually searching across Gmail, Drive, and Notion, just ask:

"Summarize my unread emails from this week"
"What files did I work on yesterday in Drive?"
"List my upcoming calendar events"
"Find the meeting notes in my Notion workspace"

Readme · MDCopy<div align="center">
🤖 Omni-Copilot
Your Personal AI Copilot for Gmail, Google Drive, Google Calendar & Notion
Show Image
Show Image
Show Image
Show Image
Show Image

Ask anything about your personal data — in plain English.
Omni-Copilot connects your Gmail, Drive, Calendar, and Notion into one privacy-first AI assistant, powered by Groq's blazing-fast LLM inference.

Features · Architecture · Quick Start · Security · API Reference
</div>

🎯 What is Omni-Copilot?
Omni-Copilot is a locally-run AI assistant that gives you natural language access to your personal productivity data. Instead of manually searching across Gmail, Drive, and Notion, just ask:

"Summarize my unread emails from this week"
"What files did I work on yesterday in Drive?"
"List my upcoming calendar events"
"Find the meeting notes in my Notion workspace"

All powered by Llama 3.1 via Groq with LangChain tool orchestration — and your raw data never leaves your machine.

✨ Features
📧 Gmail Search -- Query inbox, unread mail, labels and send emails
📁 Google Drive -- Browse, search, and read file contents from your Drive
📅 NotionRead pages and content from your Notion workspace
⚡ Groq LLMUltra-fast inference with llama-3.1-8b-instant
🔗 LangChain AgentsTool-calling orchestration for multi-step querie
s🔐 Encrypted TokensOAuth tokens stored locally with AES-128 encryption
🖥️ Web UIClean JavaScript/CSS frontend to interact with your copilot

🏗️ Architecture
┌─────────────────────────────────────────────────────┐
│                  User (Browser UI)                   │
│               frontend/ (JS + CSS + HTML)            │
└────────────────────────┬────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────┐
│              FastAPI Backend (Python)                │
│                   backend/                           │
│  ┌─────────────┐   ┌──────────────────────────────┐ │
│  │  Orchestrator│   │   Auth Layer (OAuth2)        │ │
│  │  (LangChain) │   │   Google + Notion            │ │
│  └──────┬──────┘   └──────────────────────────────┘ │
│         │ Tool Calls                                  │
│  ┌──────▼───────────────────────────────────────┐   │
│  │              Tool Registry                    │   │
│  │  Gmail | Drive | Calendar | Notion | Local FS │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────┘
                         │ Question + Snippet Only
┌────────────────────────▼────────────────────────────┐
│                 Groq API (Cloud)                     │
│            llama-3.1-8b-instant                      │
└─────────────────────────────────────────────────────┘
📁 Project Structure

Omni-Copilot/
├── backend/
│   ├── auth/
│   │   └── google_auth.py       # Gmail, Drive, Calendar OAuth + API calls
│   ├── orchestrator.py          # LangChain agent + tool definitions
│   └── main.py                  # FastAPI app entry point
├── frontend/
│   ├── index.html               # Chat UI
│   ├── style.css                # Styling
│   └── app.js                   # Frontend logic
├── docs/                        # Setup guides and documentation
├── scripts/                     # Utility and setup scripts
├── config/
│   ├── .env                     # API keys (gitignored)
│   └── tokens/                  # Encrypted OAuth tokens (gitignored)
├── requirements.txt
├── test_groq.py                 # LangChain + Groq integration test
├── test_gmail.py                # Gmail API integration test
└── .gitignore

⚡ Configure Environment Variables
Create a config/.env file:
env# Groq LLM
GROQ_API_KEY=your_groq_api_key_here

# Token encryption (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
TOKEN_ENCRYPTION_KEY=your_fernet_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Notion (optional)
NOTION_TOKEN=your_notion_integration_token
