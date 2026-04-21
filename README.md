

# 🤖 Omni-Copilot

### Your Personal AI Copilot for Gmail, Google Drive, Google Calendar & Notion

> **Ask anything about your personal data — in plain English.**  
> Omni-Copilot connects your Gmail, Drive, Calendar, and Notion into one privacy-first AI assistant, powered by Groq's blazing-fast LLM inference.


## 🎯 What is Omni-Copilot?

Omni-Copilot is a **locally-run AI assistant** that gives you natural language access to your personal productivity data. Instead of manually searching across Gmail, Drive, and Notion, just ask:

- *"Summarize my unread emails from this week"*
- *"What files did I work on yesterday in Drive?"*
- *"List my upcoming calendar events"*
- *"Find the meeting notes in my Notion workspace"*

All powered by **Llama 3.1 via Groq** with **LangChain tool orchestration** — and your raw data never leaves your machine.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📧 **Gmail Search** | Query inbox, unread mail, labels, and threads in natural language |
| 📁 **Google Drive** | Browse, search, and read file contents from your Drive |
| 📅 **Google Calendar** | List and query upcoming and past events |
| 📝 **Notion** | Read pages and content from your Notion workspace |
| ⚡ **Groq LLM** | Ultra-fast inference with `llama-3.1-8b-instant` |
| 🔗 **LangChain Agents** | Tool-calling orchestration for multi-step queries |
| 🔐 **Encrypted Tokens** | OAuth tokens stored locally with AES-128 encryption |
| 🖥️ **Web UI** | Clean JavaScript/CSS frontend to interact with your copilot |

---

## 📁 Project Structure
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
