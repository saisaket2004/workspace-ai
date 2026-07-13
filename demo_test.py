import asyncio
import logging
import sys

# Configure logging to console
logging.basicConfig(level=logging.INFO, format="%(message)s")

from backend.agent.assistant_agent import agent
from backend.session import session_manager

# Mock credentials so we don't trigger real Google API calls,
# instead we will monkeypatch the tool execution to simulate results.
from backend.agent import tool_registry

async def run_demo():
    print("\n--- DEMO: Workspace AI Hybrid Dependency Engine ---")
    
    # 1. Test Exact Match Routing
    print("\n[Scenario 1] Summarizing exact filename")
    
    # Mocking Drive Search to return a list of files including the exact match
    original_execute_tool = tool_registry.execute_tool
    
    def mocked_execute(tool_name, credentials, **kwargs):
        if tool_name == "drive_search":
            return {
                "success": True, 
                "tool": "drive_search", 
                "data": [
                    {"id": "doc123", "name": "AAC RESEARCH 1.pdf", "mimeType": "application/pdf"},
                    {"id": "doc456", "name": "AAC RESEARCH 2.pdf", "mimeType": "application/pdf"}
                ]
            }
        elif tool_name == "drive_read":
            return {"success": True, "tool": "drive_read", "data": f"Extracted text from {kwargs.get('file_id')}"}
        return {"success": True, "tool": tool_name, "data": []}
        
    tool_registry.execute_tool = mocked_execute
    
    # The Intent Router uses Gemini, so we actually call Gemini. 
    # This requires GEMINI_API_KEY in the environment.
    res = await agent.process("Summarize AAC RESEARCH 1.pdf", credentials=None)
    print("\nResult Tools Used:", res["tools_used"])
    
    # 2. Test Context Resolution
    print("\n[Scenario 2] Context Resolution ('Compare first and second')")
    
    # We pretend the user already did a search
    session_manager.last_searched_items = [
        {"id": "docA", "name": "Report_Q1.pdf", "mimeType": "application/pdf"},
        {"id": "docB", "name": "Report_Q2.pdf", "mimeType": "application/pdf"}
    ]
    
    res2 = await agent.process("Compare the first and second ones", credentials=None)
    print("\nResult Tools Used:", res2["tools_used"])

if __name__ == "__main__":
    asyncio.run(run_demo())
