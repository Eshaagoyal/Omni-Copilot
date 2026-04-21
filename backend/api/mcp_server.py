import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from backend.agents.orchestrator import run_copilot

logger = logging.getLogger(__name__)

mcp = FastMCP("Omni Copilot Local Server")

@mcp.tool()
async def query_omni_copilot(query: str, session_id: str = "mcp_client") -> str:
    """Send a natural language query to Omni Copilot. The copilot has access to local files (Docs, Images, Code) and can autonomously search, read, and summarize them."""
    collected_response = []
    try:
        async for chunk in run_copilot(query, session_id):
            collected_response.append(chunk)
        return "".join(collected_response)
    except Exception as e:
        logger.error(f"MCP Copilot Error: {e}")
        return f"Error executing Omni Copilot: {e}"

# We can also explicitly expose the local_os tools directly to the MCP client
from backend.agents.local_os import list_local_directory, read_local_file, analyze_local_image, search_codebase

@mcp.tool()
async def mcp_list_local_directory(directory_path: str) -> str:
    """List files in a local directory securely."""
    import json
    return json.dumps(list_local_directory(directory_path))

@mcp.tool()
async def mcp_read_local_file(file_path: str) -> str:
    """Read the content of a local text or code file securely."""
    return read_local_file(file_path)

@mcp.tool()
async def mcp_analyze_local_image(file_path: str, prompt: str) -> str:
    """Read and describe a local image file using Vision modeling."""
    return analyze_local_image(file_path, prompt)

@mcp.tool()
async def mcp_search_codebase(directory: str, query: str) -> str:
    """Search for a specific code keyword across a local directory."""
    return search_codebase(directory, query)
