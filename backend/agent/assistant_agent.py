"""
assistant_agent.py — Hybrid intelligent execution engine.

WHY:  Executes tools in parallel for maximum speed, handles caching,
      and chains dependencies (Search -> Pick -> Read -> Gemini).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List

from backend.session import session_manager
from backend.agent.intent_classifier import detect_intents
from backend.agent.tool_registry import execute_tool
from backend.agent.cache_manager import get_cached, set_cached
from backend.agent.context_builder import summarize_context
from backend.chatbot import ask_gemini

logger = logging.getLogger(__name__)

DEPENDENCIES = {
    "drive_search": "drive_read",
    "drive_list": "drive_read",
    "gmail_search": "gmail_read",
    "gmail_list": "gmail_read",
    "docs_list": "docs_read",
    "sheets_list": "sheets_read",
    "slides_list": "slides_read"
}

READ_INTENT_KEYWORDS = ["read", "summarize", "open", "analyze", "what does it say", "tell me about"]

ANSWERING_PROMPT = """You are a highly capable Google Workspace AI Assistant.
Answer the user's question beautifully using markdown (bolding, lists, cards) based ONLY on the provided Workspace context.
If the context is empty, simply tell the user you couldn't find the information.

WORKSPACE CONTEXT:
{context}

USER QUESTION:
{question}
"""

class WorkspaceAgent:
    """Hybrid fast-execution agent."""

    async def process(self, question: str, credentials) -> Dict[str, Any]:
        start_time = time.time()
        gemini_calls = 0
        cache_hits = 0
        tool_execution_times = {}
        tool_results = []
        tools_used = []
        
        logger.info("[Intent] Analyzing: %s", question)
        executions = detect_intents(question)
        gemini_calls += 1  # We assume intent classifier used Gemini for complex logic
        
        async def run_tool(exe_plan: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal cache_hits
            t_name = exe_plan["tool"]
            args = exe_plan.get("args", {})
            t_start = time.time()
            
            # Simple args check (if intent router didn't supply them, we fallback to question)
            if not args and t_name.endswith("_search"):
                args = {"query": question}
                
            logger.info("Executing tool: %s with args: %s", t_name, args)
            
            # Cache check
            # For caching, we need a unique key based on args
            cache_key = f"{t_name}_{str(args)}"
            cached_data = get_cached(cache_key)
            if cached_data is not None:
                cache_hits += 1
                tool_execution_times[t_name] = f"{time.time() - t_start:.2f}s"
                return {"success": True, "tool": t_name, "data": cached_data, "error": None, "cached": True}
            
            result = await asyncio.to_thread(execute_tool, t_name, credentials, **args)
            if result["success"]:
                set_cached(cache_key, result["data"])
                
                # Update Session Manager Context
                data = result["data"]
                if "search" in t_name or "list" in t_name:
                    if isinstance(data, list):
                        session_manager.last_searched_items = data
                elif "read" in t_name:
                    if isinstance(data, str):
                        # Construct a mock item
                        session_manager.last_opened_item = {"id": args.get("file_id", args.get("doc_id", "unknown")), "name": "Document", "mimeType": args.get("mime_type", "unknown")}
            
            result["cached"] = False
            tool_execution_times[t_name] = f"{time.time() - t_start:.2f}s"
            return result

        if executions:
            logger.info("[Search/Fetch] Executing parallel tools: %s", [e["tool"] for e in executions])
            tasks = [run_tool(e) for e in executions]
            results = await asyncio.gather(*tasks)
            
            for r in results:
                tool_results.append(r)
                tools_used.append(r["tool"])
                
            # Dependency Graph Chaining
            question_lower = question.lower()
            needs_read = any(kw in question_lower for kw in READ_INTENT_KEYWORDS)
            
            if needs_read:
                chained_executions = []
                for r in results:
                    if r["success"] and r["tool"] in DEPENDENCIES:
                        dep_tool = DEPENDENCIES[r["tool"]]
                        data = r["data"]
                        
                        if isinstance(data, list):
                            if len(data) == 0:
                                logger.info("[Pick] No results found for %s. Not chaining.", r["tool"])
                                continue
                                
                            items_to_read = []
                            query = ""
                            # find original query to do exact matching
                            for e in executions:
                                if e["tool"] == r["tool"]:
                                    query = e.get("args", {}).get("query", "").lower()
                                    break
                                    
                            if len(data) == 1:
                                logger.info("[Pick] Intercepted 1 result for %s. Auto-selecting.", r["tool"])
                                items_to_read.append(data[0])
                            elif len(data) > 1:
                                # Look for exact match
                                exact_match = None
                                for item in data:
                                    if query and query in item.get("name", "").lower():
                                        exact_match = item
                                        break
                                
                                if exact_match:
                                    logger.info("[Pick] Found exact match for '%s'. Auto-selecting.", query)
                                    items_to_read.append(exact_match)
                                else:
                                    logger.info("[Pick] %d results found, but no exact match. Returning list to user.", len(data))
                                    # We don't append to items_to_read, so no chained executions happen. 
                                    # The LLM will just summarize the list.
                                    pass

                            # If intent parser literally asked for multiple IDs (it wouldn't happen via search interception usually, 
                            # because if it asked for multiple IDs it would use docs_read directly).
                            # But if we did want to compare first and second via search intercept:
                            if "compare" in question_lower or ("first" in question_lower and "second" in question_lower):
                                if len(data) >= 2 and not items_to_read:
                                    logger.info("[Pick] Compare intent detected. Auto-selecting first two results.")
                                    items_to_read = data[:2]

                            for item in items_to_read:
                                item_id = item.get("id")
                                item_mime = item.get("mimeType", "text/plain")
                                item_name = item.get("name", "Unknown")
                                
                                if item_id and dep_tool not in tools_used:
                                    logger.info("[Pick] Intercepted %s. Selecting result: %s", r["tool"], item_name)
                                    kwargs = {}
                                    if "drive" in dep_tool:
                                        kwargs = {"file_id": item_id, "file_name": item_name, "mime_type": item_mime}
                                    elif "gmail" in dep_tool:
                                        kwargs = {"message_id": item_id}
                                    elif "docs" in dep_tool:
                                        kwargs = {"doc_id": item_id}
                                    elif "sheets" in dep_tool:
                                        kwargs = {"spreadsheet_id": item_id}
                                    elif "slides" in dep_tool:
                                        kwargs = {"presentation_id": item_id}
                                        
                                    chained_executions.append({"tool": dep_tool, "args": kwargs})
                
                if chained_executions:
                    logger.info("[Read] Executing chained dependencies: %s", [e["tool"] for e in chained_executions])
                    dep_tasks = [run_tool(e) for e in chained_executions]
                    dep_results = await asyncio.gather(*dep_tasks)
                    for r in dep_results:
                        tool_results.append(r)
                        tools_used.append(r["tool"])
        
        logger.info("[Extract] Summarizing tool results into context payload")
        context_str = summarize_context(tool_results)
        
        final_prompt = ANSWERING_PROMPT.format(context=context_str, question=question)
        
        logger.info("[Gemini] Synthesizing final answer")
        answer = ask_gemini(final_prompt)
        gemini_calls += 1
        
        execution_time = f"{time.time() - start_time:.2f}s"
        logger.info("[Response] Answer generated in %s", execution_time)
        
        if session_manager:
            session_manager.conversation_history.append({"user": question, "assistant": answer})
            
        return {
            "answer": answer,
            "tools_used": tools_used,
            "execution_time": execution_time,
            "gemini_calls": gemini_calls,
            "cache_hits": cache_hits,
            "tool_execution_times": tool_execution_times
        }

agent = WorkspaceAgent()
