import asyncio
from backend.agents.orchestrator import app, msgs, run_copilot

async def t():
    async for c in run_copilot('Look in the backend folder and find my mcp_server file and explain what it says', 't5', []):
        print(repr(c))

if __name__ == "__main__":
    asyncio.run(t())
