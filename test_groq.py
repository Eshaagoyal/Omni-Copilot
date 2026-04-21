import os
import asyncio
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

load_dotenv("config/.env")

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.environ.get("GROQ_API_KEY"),
    max_tokens=2048,
    temperature=0.3
)

from orchestrator import tool_list_local_directory, tool_read_local_file

llm_with_tools = llm.bind_tools([tool_list_local_directory, tool_read_local_file])

async def test():
    messages = [
        SystemMessage("You are a helpful assistant."),
        HumanMessage("Read the document 'Financial Analytics' in my GDrive."),
        AIMessage(content="", tool_calls=[{"name": "tool_get_drive_file", "args": {"file_id": "123"}, "id": "call_abc"}]),
        ToolMessage(content="Esha Goyal Financial Analytics with Python", name="tool_get_drive_file", tool_call_id="call_abc"),
        AIMessage(content="The document contains: Esha Goyal Financial Analytics with Python"),
        HumanMessage("Wait, forget that PDF. Please list all the files currently inside my local C:\ directory instead")
    ]
    
    response = await llm_with_tools.ainvoke(messages)
    print("CONTENT:", repr(response.content))
    print("TOOL CALLS:", response.tool_calls)

if __name__ == "__main__":
    asyncio.run(test())
