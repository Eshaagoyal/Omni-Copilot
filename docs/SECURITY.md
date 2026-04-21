# Security Guide

## What stays on your computer
- All Gmail, Drive, Notion data
- All OAuth tokens (encrypted in config/tokens/)
- Your config/.env keys

## What goes to the internet
- Your question + small data snippet → Groq API
- Token refresh requests → Google/Notion servers

## Token encryption
- Algorithm: AES-128 (Fernet)
- Location: config/tokens/*.enc
- Permission: 600 (owner read/write only)
- Unreadable without your TOKEN_ENCRYPTION_KEY

## To disconnect everything
Run in terminal:
curl -X DELETE http://localhost:8000/auth/revoke-all

## Scopes (read-only by default)
- Gmail: gmail.readonly, gmail.labels
- Drive: drive.readonly, drive.metadata.readonly
- Notion: read workspace pages