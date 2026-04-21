

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
---

## 🚀 Quick Start

### Prerequisites

- Python **3.9+**
- A [**Groq API key**](https://console.groq.com/) (free tier available)
- A **Google Cloud project** with OAuth 2.0 credentials
- A **Notion** integration token (optional)

---

### 1. Clone the Repository

```bash
git clone https://github.com/Eshaagoyal/Omni-Copilot.git
cd Omni-Copilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `config/.env` file:

```env
# Groq LLM
GROQ_API_KEY=your_groq_api_key_here

# Token encryption
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TOKEN_ENCRYPTION_KEY=your_fernet_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Notion (optional)
NOTION_TOKEN=your_notion_integration_token
```

### 5. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project → **APIs & Services** → **Credentials**
3. Create **OAuth 2.0 Client ID** (Desktop app)
4. Enable the following APIs:
   - Gmail API
   - Google Drive API
   - Google Calendar API
5. Download the credentials and place them in `config/`

### 6. Run the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 7. Open the Frontend

```bash
cd frontend
python -m http.server 3000
# Navigate to http://localhost:3000
```

---

## 🔧 Testing Individual Integrations

**Test Groq + LangChain tool calling:**
```bash
python test_groq.py
```

**Test Gmail API connection:**
```bash
python test_gmail.py
# Output saved to gmail_test.txt
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send a natural language query to the AI |
| `GET` | `/auth/google` | Initiate Google OAuth flow |
| `GET` | `/auth/notion` | Initiate Notion OAuth flow |
| `GET` | `/auth/status` | Check connection status for all services |
| `DELETE` | `/auth/revoke-all` | Revoke all tokens and disconnect everything |

Interactive API docs: **`http://localhost:8000/docs`**

---


## 👤 Author

**Eshaa Goyal** — [@Eshaagoyal](https://github.com/Eshaagoyal)

---
