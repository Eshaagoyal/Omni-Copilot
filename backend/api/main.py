import os, logging, json
from fastapi import FastAPI, HTTPException
from fastapi.responses import (
    RedirectResponse, StreamingResponse,
    JSONResponse, HTMLResponse,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv("config/.env", override=True)

from backend.auth.google_auth import (
    get_auth_url as google_url,
    handle_callback as google_cb,
)
from backend.auth.notion_auth import (
    get_auth_url as notion_url,
    handle_callback as notion_cb,
)
from backend.auth.security import (
    list_connected, revoke_all, delete_token
)
from backend.agents.orchestrator import run_copilot
from backend.auth.slack_auth import is_slack_connected

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Omni Copilot", version="1.0.0")

allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501")
allowed_origins = [o.strip() for o in allowed_origins_str.split(",")]

app.add_middleware(CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_histories: dict[str, list[dict]] = {}


@app.get("/health")
def health():
    return {"status": "ok",
            "connected": list_connected(),
            "model": os.getenv("GROQ_MODEL")}


@app.get("/auth/google")
def auth_google():
    return RedirectResponse(google_url())


@app.get("/auth/notion")
def auth_notion():
    return RedirectResponse(notion_url())


@app.get("/auth/google/callback")
def google_callback(code: str):
    try:
        google_cb(code)
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;
        padding:40px;text-align:center">
        <h2 style="color:green">✅ Google Connected!</h2>
        <p>Gmail and Drive are connected. Close this tab.</p>
        </body></html>""")
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/auth/notion/callback")
def notion_callback(code: str):
    try:
        result = notion_cb(code)
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;
        padding:40px;text-align:center">
        <h2 style="color:green">✅ Notion Connected!</h2>
        <p>Workspace: {result.get('workspace')}. Close this tab.</p>
        </body></html>""")
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/auth/status")
def auth_status():
    c = list_connected()
    return {"connected_providers": c,
            "google": "google" in c,
            "notion": "notion" in c,
            "slack": is_slack_connected()}


@app.delete("/auth/revoke-all")
def revoke():
    revoke_all()
    return {"message": "All tokens deleted."}


@app.delete("/auth/revoke/{provider}")
def revoke_one(provider: str):
    if delete_token(provider):
        return {"message": f"{provider} disconnected."}
    raise HTTPException(404, f"No token for {provider}")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    use_history: bool = True


@app.post("/chat")
async def chat(body: ChatRequest):
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(500,
            "GROQ_API_KEY not set. Get free key at console.groq.com")

    history = (_histories.get(body.session_id, [])
               if body.use_history else [])
    collected = []

    async def stream():
        try:
            async for chunk in run_copilot(
                body.message, body.session_id, history
            ):
                collected.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: ⚠️ Error: {e}\n\n"
        finally:
            if body.use_history:
                full = "".join(collected)
                clean = "\n".join(
                    l for l in full.split("\n")
                    if not l.startswith("> Using **")
                ).strip()
                history.append(
                    {"role": "user", "content": body.message})
                history.append(
                    {"role": "assistant", "content": clean})
                _histories[body.session_id] = history[-40:]
            yield "data: [DONE]\n\n"

    return StreamingResponse(stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no"})


@app.delete("/chat/history/{session_id}")
def clear_history(session_id: str):
    _histories.pop(session_id, None)
    return {"message": "History cleared."}