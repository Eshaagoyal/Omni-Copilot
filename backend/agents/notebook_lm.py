import os
import logging
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

def query_notebook(context_documents: list[str], query: str) -> str:
    """
    Simulates Google's NotebookLM architecture using Groq LLM context window.
    Takes an array of raw document contents and queries them all simultaneously.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return "Error: GROQ_API_KEY is not set in config/.env. Notebook LM requires Groq."
        
    try:
        # We use ChatGroq for reasoning over documents
        llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            api_key=api_key,
            temperature=0.0
        )
        
        # Concat all source materials into the prompt context
        combined_context = "\n\n=== SOURCE BOUNDARY ===\n\n".join(context_documents)
        
        prompt = (
            "You are an expert document-analysis AI, mirroring the functionality of NotebookLM. "
            "Base your entire answer strictly on the provided SOURCE MATERIAL below. "
            "Do not use outside knowledge. If the answer is not in the text, explicitly state that you cannot find the answer in the provided sources. "
            "Use markdown formatting to structure your response cleanly.\n\n"
            "SOURCE MATERIAL:\n" 
            + combined_context
        )
        
        system = SystemMessage(content=prompt)
        human = HumanMessage(content=query)
        
        response = llm.invoke([system, human])
        return response.content
        
    except Exception as e:
        logger.error(f"Error querying Notebook LM mimic: {e}")
        return f"Groq API Error: {str(e)}"
