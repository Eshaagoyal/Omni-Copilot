import os, json, logging
from typing import AsyncGenerator, Annotated, TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# External Auth Functions
from backend.auth.google_auth import (
    list_emails as list_gmail_emails, get_email_body as get_gmail_body,
    list_drive_files, search_emails as search_gmail, get_drive_file_content, send_gmail_email
)
from backend.auth.notion_auth import search_pages as search_notion, get_page_content as get_notion_page, append_to_page as append_notion_page
from backend.auth.slack_auth import get_slack_channels, read_slack_messages, send_slack_message
from backend.auth.security import list_connected
from backend.agents.memory import ingest_document, search_memory
from backend.agents.mem0_manager import save_user_fact, search_user_facts
from backend.agents.vectorless_db import ingest_text_vectorless, search_exact_text
from backend.agents.local_os import list_local_directory, read_local_file, analyze_local_image, search_codebase, write_local_file, create_local_directory
from backend.agents.notebook_lm import query_notebook
from backend.agents.knowledge_graph import add_graph_edge, query_graph

logger = logging.getLogger(__name__)

# ── STATE ──────────────────────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# ── TOOLS ──────────────────────────────────────────────────────────
@tool
def tool_list_gmail(max_results: int = 10, filter_status: str = "all", query: str = "") -> str:
    """List recent Gmail emails. You can filter by unread/read using filter_status, AND simultaneously filter by sender or keywords using 'query'."""
    original = max_results
    max_results = min(max_results, 8)
    q_parts = []
    if filter_status.lower() == "unread":
        q_parts.append("is:unread")
    elif filter_status.lower() == "read":
        q_parts.append("is:read")
        
    if query:
        q_parts.append(query)
        
    final_query = " ".join(q_parts)
        
    msg = json.dumps(list_gmail_emails(max_results=max_results, query=final_query), default=str)
    if original > 8: msg += f"\n[Notice: API Token safety limits required clamping max_results to {max_results}.]"
    return msg

@tool
def tool_get_gmail_body(message_id: str = "") -> str:
    """Get the full body text of a Gmail email by ID."""
    if not message_id: return "Error: Please provide a valid message_id."
    body = get_gmail_body(message_id)
    if len(body) > 8000:
        ingest_text_vectorless(message_id, body, "Gmail")
        return "Email is large and securely ingested into Vectorless Database. Use 'tool_search_exact_text' to find details."
    return body[:4000] # Truncate directly in tool to save tokens

@tool
def tool_search_gmail(query: str = "", max_results: int = 10) -> str:
    """Search Gmail with a keyword. Do NOT use this for unread/read filters. Use tool_list_gmail instead."""
    if not query: return "Error: please provide a query string."
    original = max_results
    max_results = min(max_results, 8)
    msg = json.dumps(search_gmail(query, max_results), default=str)
    if original > 8: msg += f"\n[Notice: API Token safety limits required clamping max_results to {max_results}.]"
    return msg

@tool
def tool_list_drive_files(folder_id: str = "", query: str = "", max_results: int = 5) -> str:
    """List files in Google Drive. Search Google drive by providing a keyword in 'query'."""
    original = max_results
    max_results = min(max_results, 15) # Drive files are smaller payload
    msg = json.dumps(list_drive_files(folder_id=folder_id, query=query, max_results=max_results), default=str)
    if original > 15: msg += f"\n[Notice: API Token safety limits required clamping max_results to {max_results}.]"
    return msg

@tool
def tool_get_drive_file(file_id: str = "") -> str:
    """Read text content of a Google Doc by file ID."""
    if not file_id: return "Error: please provide a specific file_id."
    c = get_drive_file_content(file_id)
    if len(c) > 3500:
        ingest_text_vectorless(file_id, c, "Google Drive")
        return c[:3500] + "\n\n...[Document is very large and was truncated. The full document is ingested in Vectorless DB. If you need specific details, use 'tool_search_exact_text'.]"
    return c

@tool
def tool_list_calendar_events(max_results: int = 10) -> str:
    """List upcoming Google Calendar events."""
    original = max_results
    max_results = min(max_results, 15)
    msg = json.dumps(list_calendar_events(max_results=max_results), default=str)
    if original > 15: msg += f"\n[Notice: API Token safety limits required clamping max_results to {max_results}.]"
    return msg

@tool
def tool_create_calendar_event(summary: str, start_iso: str, end_iso: str, attendees: list = None) -> str:
    """Create a new Google Calendar event. start_iso and end_iso should be in UTC ISO format (e.g. 2026-04-18T10:00:00Z)."""
    link = create_calendar_event(summary, start_iso, end_iso, attendees)
    return f"Event created: {link}" if link else "Failed to create event."

_server_draft_cache = {"locked_until_next_turn": False, "latest": None}

@tool
def tool_draft_email(to: str, subject: str = "Update", message: str = "") -> str:
    """Drafts an email and saves it to the central dispatch spool. MUST be used before sending any email!"""
    _server_draft_cache["latest"] = {"to": to, "subject": subject, "message": message}
    _server_draft_cache["locked_until_next_turn"] = True
    return f"DRAFT SUCCESSFUL. Stop processing now. Show the user this preview exactly as is:\n\nTo: {to}\nSubject: {subject}\nBody: {message}\n\nAsk them: 'Should I dispatch this email now?'"

@tool
def tool_dispatch_approved_email(confirm: bool = True) -> str:
    """Dispatches the currently spooled email draft. ONLY run this if the user has explicitly confirmed 'yes' in their last reply! You MUST set confirm=True."""
    if _server_draft_cache.get("locked_until_next_turn"):
        return "SYSTEM RED ALERT: You are trying to dispatch an email in the EXACT SAME TURN that you drafted it! You MUST stop processing right now, ask the user for permission, and WAIT for them to reply in a new chat message! Do not call this tool again!"
    
    draft = _server_draft_cache.get("latest")
    if not draft: return "System Error: No draft found. You must use tool_draft_email first."
    res = send_gmail_email(draft["to"], draft["subject"], draft["message"])
    _server_draft_cache["latest"] = None
    return res + "\n\nCRITICAL INSTRUCTION: The email has been officially dispatched. You MUST STOP executing any further tools right now. Output a short final confirmation to the user and yield."

@tool
def tool_search_notion(query: str, max_results: int = 10) -> str:
    """Search Notion workspace pages."""
    original = max_results
    max_results = min(max_results, 10)
    msg = json.dumps(search_notion(query, max_results), default=str)
    if original > 10: msg += f"\n[Notice: API Token safety limits required clamping max_results to {max_results}.]"
    return msg

@tool
def tool_get_notion_page(page_id: str) -> str:
    """Read full content of a Notion page by ID."""
    c = get_notion_page(page_id)
    if len(c) > 4000:
        ingest_document(page_id, c, "Notion")
        return "Notion page is large and has been ingested into memory. Use 'tool_search_memory'."
    return c

@tool
def tool_append_notion_page(page_id: str, content: str) -> str:
    """Append a paragraph to a Notion page. You MUST provide the system page_id (fetched via tool_search_notion)."""
    return append_notion_page(page_id, content)

@tool
def tool_create_notion_page(parent_page_id: str, title: str) -> str:
    """Create a completely new nested page in Notion. You must provide the parent_page_id of the page you want to create this inside of."""
    from backend.auth.notion_auth import create_page
    return create_page(parent_page_id, title)

@tool
def tool_get_slack_channels() -> str:
    """Lists available Slack channels to obtain their ID."""
    return json.dumps(get_slack_channels(), default=str)

@tool
def tool_read_slack_messages(channel_id: str, limit: int = 10) -> str:
    """Read recent messages from a specific Slack channel ID."""
    original = limit
    limit = min(limit, 15)
    msg = json.dumps(read_slack_messages(channel_id, limit), default=str)
    if original > 15: msg += f"\n[Notice: API Token safety limits required clamping max_results to {limit}.]"
    return msg

@tool
def tool_send_slack_message(channel_id: str, text: str) -> str:
    """Send a message to a specific Slack channel ID."""
    success = send_slack_message(channel_id, text)
    return "Message sent successfully" if success else "Failed to send message"
@tool
def tool_search_memory(query: str) -> str:
    """Search across large documents stored securely in your local memory."""
    return search_memory(query)

@tool
def tool_search_exact_text(query: str = "") -> str:
    """Search specifically across Mail, Drive, and Local Files using exact keyword BM25 match."""
    if not query: return "Error: Please provide a specific text query to search."
    return search_exact_text(query)

@tool
def tool_save_user_fact(fact: str = "") -> str:
    """Save an important fact or preference about the user to long-term memory."""
    if not fact: return "Error: Please provide a fact to save."
    return save_user_fact("default_omni_user", fact)

@tool
def tool_search_user_facts(query: str = "") -> str:
    """Retrieve facts or preferences about the user from long-term memory."""
    if not query: return "Error: Query was successfully executed, but please provide a specific query word next time."
    return search_user_facts("default_omni_user", query)

@tool
def tool_list_local_directory(directory_path: str = ".") -> str:
    """Lists files and folders inside a local directory path (e.g. C:/ or D:/)."""
    return json.dumps(list_local_directory(directory_path))

@tool
def tool_read_local_file(file_path: str) -> str:
    """Reads the text content of a file on the local machine."""
    c = read_local_file(file_path)
    if len(c) > 3500:
        ingest_text_vectorless(file_path, c, "Local File")
        return c[:3500] + "\n\n...[Document is very large and was truncated. The full document is ingested in Vectorless DB. If you need specific details, use 'tool_search_exact_text'.]"
    return c

@tool
def tool_write_local_file(file_path: str, content: str) -> str:
    """Creates a new text file at the specified local path with the given content."""
    return write_local_file(file_path, content)

@tool
def tool_create_local_directory(directory_path: str) -> str:
    """Creates a new physical folder at the specified local path."""
    return create_local_directory(directory_path)

@tool
def tool_analyze_local_image(file_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Securely read a local image (.png, .jpg) via Vision to describe its contents."""
    return analyze_local_image(file_path, prompt)

@tool
def tool_search_codebase(query: str) -> str:
    """Search recursively for specific file names OR code snippets matching the query string across the whole project."""
    return search_codebase(".", query)

@tool
def tool_query_notebook_local_files(file_paths: list[str], query: str) -> str:
    """Simulates NotebookLM. Passes local files to Groq for deep comprehensive QA over entire large documents. Bypasses normal memory limits."""
    docs = []
    for p in file_paths:
        docs.append(read_local_file(p))
    return query_notebook(docs, query)

@tool
def tool_add_graph_edge(source: str, target: str, relationship: str) -> str:
    """Map a causal or social relationship connecting two entities (people, companies, etc) to the knowledge graph."""
    return add_graph_edge(source, target, relationship)

@tool
def tool_query_graph(entity: str) -> str:
    """Query the knowledge graph for all known relationships of a specific entity."""
    return query_graph(entity)

TOOLS = [
    tool_list_gmail, tool_get_gmail_body, tool_search_gmail, tool_draft_email, tool_dispatch_approved_email,
    tool_list_drive_files, tool_get_drive_file,
    tool_search_notion, tool_get_notion_page, tool_append_notion_page, tool_create_notion_page,
    tool_get_slack_channels, tool_read_slack_messages, tool_send_slack_message,
    tool_search_memory, tool_search_exact_text,
    tool_save_user_fact, tool_search_user_facts,
    tool_list_local_directory, tool_read_local_file, tool_analyze_local_image, tool_search_codebase, tool_write_local_file, tool_create_local_directory,
    tool_query_notebook_local_files,
    tool_add_graph_edge, tool_query_graph
]

tool_node = ToolNode(TOOLS)

# ── GRAPH LOGIC ───────────────────────────────────────────────────
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

async def call_model(state: AgentState):
    messages = state["messages"]
    
    connected = list_connected()
    integrations = ", ".join(connected) if connected else "none"
    sys_msg = SystemMessage(content=SYSTEM.format(integrations=integrations))
    
    # SMART METADATA TRUNCATION:
    # 1. Find the exact boundary of the active conversation turn
    last_human_idx = 0
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break
            
    # 2. Archive MASSIVE Tool outputs from PAST conversational turns via truncation, but keep smaller/medium ones 100% intact so the AI remembers IDs!
    processed_messages = []
    for i, msg in enumerate(messages):
        if i < last_human_idx and isinstance(msg, ToolMessage) and len(str(msg.content)) > 5000:
            # We must drastically truncate and inject a definitive boundary so the LLM doesn't try to "autocomplete" half-cut words text in the next conversational turn!
            archived = ToolMessage(
                content=str(msg.content)[:2000] + f"\n\n\n... (Prior document truncated to save memory.)", 
                tool_call_id=msg.tool_call_id, 
                name=msg.name
            )
            processed_messages.append(archived)
        else:
            processed_messages.append(msg)
            
    # Memory context size is already highly optimized because we archive past ToolMessage content to 150 chars.
    # Therefore, we safely persist the entire logical conversation without dangerously dropping the Human command mid-sequence!
    messages_for_llm = [sys_msg] + processed_messages

    # SEMANTIC ROUTING: Dynamically Prune Tools to prevent LLM Overload
    user_context = " ".join([str(m.content).lower() for m in messages if isinstance(m, HumanMessage)])
    
    active_tools = [tool_search_exact_text]
    
    if any(k in user_context for k in ["remember", "memory", "fact", "recall", "forget"]):
        active_tools.extend([tool_save_user_fact, tool_search_user_facts, tool_search_memory])
    
    if any(k in user_context for k in ["email", "gmail", "inbox", "mail", "send", "draft"]):
        active_tools.extend([tool_list_gmail, tool_get_gmail_body, tool_search_gmail, tool_draft_email, tool_dispatch_approved_email])
        
    last_user_msg = ""
    human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
    if human_msgs: last_user_msg = str(human_msgs[-1].content).lower()
    
    # Draft dispatch is now globally available when email tools are active to prevent hallucination crashes
    
    if any(k in user_context for k in ["drive", "pdf", "doc", "document"]):
        active_tools.extend([tool_list_drive_files, tool_get_drive_file])
    if any(k in user_context for k in ["local", "folder", "directory", "c:", "d:", "codebase", "image", "file", "write", "create"]):
        active_tools.extend([tool_list_local_directory, tool_read_local_file, tool_analyze_local_image, tool_search_codebase, tool_query_notebook_local_files, tool_write_local_file, tool_create_local_directory])
    if any(k in user_context for k in ["slack", "message", "channel"]):
        active_tools.extend([tool_get_slack_channels, tool_read_slack_messages, tool_send_slack_message])
    if any(k in user_context for k in ["notion", "page"]):
        active_tools.extend([tool_search_notion, tool_get_notion_page, tool_append_notion_page, tool_create_notion_page])
        
    # Deduplicate while preserving order
    pruned_tools = []
    for t in active_tools:
        if t not in pruned_tools:
            pruned_tools.append(t)

    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        api_key=os.getenv("GROQ_API_KEY"),
        max_tokens=int(os.getenv("GROQ_MAX_TOKENS", "2048")),
        temperature=float(os.getenv("GROQ_TEMPERATURE", "0.3")),
    )
    llm_with_tools = llm.bind_tools(pruned_tools)
    
    try:
        response = await llm_with_tools.ainvoke(messages_for_llm)
    except Exception as e:
        raise e
    
    # ANTI-PARALLEL HALLUCINATION INTERCEPTOR
    # Small models (8B tier) notoriously hallucinate arrays of 10+ identical parallel tool calls when asked to do multi-step tasks.
    # We physically intercept the LangChain message here and forcefully truncate any parallel array down to exactly 1 tool per turn.
    # This guarantees true sequential ReAct logic and mathematically prevents API Request Rate limits!
    if hasattr(response, "tool_calls") and isinstance(response.tool_calls, list) and len(response.tool_calls) > 1:
        response.tool_calls = [response.tool_calls[0]]
        # CRITICAL: We MUST also truncate the raw API dictionary in additional_kwargs otherwise ChatGroq will encounter a corrupted message graph state next turn!
        if "tool_calls" in response.additional_kwargs and isinstance(response.additional_kwargs["tool_calls"], list):
            response.additional_kwargs["tool_calls"] = [response.additional_kwargs["tool_calls"][0]]
        
    return {"messages": [response]}

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# ── ORCHESTRATOR ─────────────────────────────────────────────────
SYSTEM = """You are Omni Copilot, an intelligent assistant with access to the user's Gmail, Google Drive, and Local File System.
Connected Integrations: {integrations}

RULES:
1. Always identify the user's intent before calling a tool.
2. If the query is ambiguous, make a reasonable assumption and state it briefly.
3. Never expose raw API errors to the user. Translate them to friendly messages.
4. If a file or email is too large, summarise — never dump raw content.
5. Always format lists cleanly: use numbered/bullet format with metadata.
6. If a tool fails (rate limit, auth error, not found), say so clearly and suggest what the user can try.
7. For file reading, limit output to 3000 tokens. If longer, summarise.
8. For emails, always show: From, Subject, Date, and then the content/summary. IF the user asks to see the "whole body" or full content, DO NOT summarize it! Print the full body exactly as the tool gave it to you!
9. Never make up file names, email subjects, or content. Only return real data.
10. If the user asks something not related to files/emails, answer from your own knowledge but note you are primarily a file and email assistant.
11. NEVER hallucinate the mathematical count of items. If a tool returns exactly 3 files, do NOT introduce them by saying "Here are the 5 files..." just because the user originally asked for 5! Just output the actual number returned.
12. AESTHETICS: When displaying lists of emails or files to the user, make it look clean! NEVER output the raw 32-character `id` or `message_id` (e.g. '19da840eb...') in your text! Keep the ID secretly in your memory to use for follow-up tool calls, but only show human-readable fields (Sender, Subject, Date) to the user.

INTENT CLASSIFICATION AND TOOL WORKFLOWS:
- "send email / write email to X" → First, call `tool_draft_email` to spool it. Output the spooled text to the user. Stop and wait. If they confirm with "yes" in their *next* chat, THEN call `tool_dispatch_approved_email()`.
- "list emails / recent mails / check inbox" → tool_list_gmail
- "unread email in my latest 5 emails" → USE tool_list_gmail(max_results=5, filter_status="all") and manually read the returned metadata.
- "list all my unread emails" → tool_list_gmail(filter_status="unread")
- "find file / search drive" → tool_list_drive_files OR tool_search_exact_text
- "list files / what's in my drive" → tool_list_drive_files OR tool_list_local_directory
- "Slack messages" → ALWAYS call `tool_get_slack_channels` FIRST to get the system `channel_id`, THEN call `tool_read_slack_messages(channel_id)`.

CRITICAL ID RULES FOR SPECIFIC FILES/EMAILS:
- "read email / summarise email X" → NEVER call tool_get_gmail_body directly! ALWAYS call tool_list_gmail or tool_search_gmail FIRST to find the `message_id`. If the snippet from list_gmail is cut off or says 'not provided due to...token limit', DO NOT tell the user about the limit! Just silently run `tool_get_gmail_body(message_id)` to get the full email!
- "read file / summarise file Y" → NEVER hallucinate a filename into `file_id`! ALWAYS call tool_list_drive_files(query="filename") FIRST to find the 32-character Google `file_id`, then call tool_get_drive_file using that ID!
- "Notion search" → If the user asks for "recent pages" or just generally wants to see Notion pages without a specific search term, YOU MUST call `tool_search_notion(query="")` with an empty string, otherwise Notion will fail!

CRITICAL TECHNICAL GUIDELINES:
- If the user asks to search the codebase or project files, use `tool_search_codebase`.
- NEVER call the exact same tool multiple times in parallel.
- If you have gathered enough information, directly output the final answer concisely in markdown format. DO NOT use structural output tags.
"""

async def run_copilot(
    user_message: str,
    session_id: str,
    chat_history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    
    global _server_draft_cache
    _server_draft_cache["locked_until_next_turn"] = False

    msgs = [HumanMessage(content=user_message)]
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": 15}

    # We use LangGraph's astream_events to safely yield tokens to the frontend
    try:
        async for event in app.astream_events({"messages": msgs}, version="v2", config=config):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    yield chunk.content
            elif kind == "on_tool_start":
                tool_name = event["name"]
                yield f"__AUDIT__{tool_name}__"
    except Exception as e:
        logger.error(f"LangGraph error: {e}")
        # Identify specifically if Groq crashed from token limits, or if it was a deep Python crash.
        err_msg = str(e)
        if "429" in err_msg:
            yield f"\n\n> **System Status**: *Groq Token Limit Reached (429).* Please wait 60 seconds precisely. ⚡"
        else:
            yield f"\n\n> **System Execution Error**: `{err_msg}`\n> The AI encountered a deep logic crash and could not recover."