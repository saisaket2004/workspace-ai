"""
context_builder.py — Summarizes raw tool outputs to minimize Gemini prompt size.

WHY:  Sending raw Google API JSON burns tokens and slows down Gemini.
      This module converts JSON into a clean, LLM-friendly string.

WHERE: Used by assistant_agent.py.
"""

from typing import List, Dict, Any

def summarize_context(tool_outputs: List[Dict[str, Any]]) -> str:
    """
    Converts a list of tool result dictionaries into a compact markdown summary.
    """
    if not tool_outputs:
        return "No tools were executed."
        
    lines = []
    
    for out in tool_outputs:
        tool_name = out.get("tool", "unknown_tool")
        success = out.get("success", False)
        error = out.get("error")
        data = out.get("data")
        
        lines.append(f"\n### {tool_name.replace('_', ' ').title()}")
        
        if not success or error:
            lines.append(f"- Error: {error}")
            continue
            
        if not data:
            lines.append("- No data returned.")
            continue
            
        # Specific formatting based on data type
        if isinstance(data, list):
            for item in data[:10]: # Max 10 items
                if isinstance(item, dict):
                    # Try to extract useful keys
                    name = item.get("name") or item.get("subject") or item.get("summary") or item.get("title") or "Item"
                    snippet = item.get("snippet") or item.get("description") or ""
                    start_val = item.get("start")
                    start_date = ""
                    if isinstance(start_val, dict):
                        start_date = start_val.get("dateTime") or start_val.get("date") or ""
                    elif isinstance(start_val, str):
                        start_date = start_val
                        
                    date = item.get("date") or item.get("modifiedTime") or start_date or ""
                    
                    line = f"- **{name}**"
                    if date:
                        line += f" ({date})"
                    if snippet:
                        line += f": {snippet[:100]}..." # Truncate snippet
                    lines.append(line)
                else:
                    lines.append(f"- {str(item)[:100]}")
        elif isinstance(data, dict):
            # Print key-value pairs
            for k, v in data.items():
                if isinstance(v, (str, int, float, bool)):
                    lines.append(f"- {k}: {v}")
                elif isinstance(v, list) and v:
                    lines.append(f"- {k}: [Array of {len(v)} items]")
        elif isinstance(data, str):
            # Text content (e.g. read_file)
            lines.append(f"Content snippet: {data[:500]}...") # Limit text size
        else:
            lines.append(f"- {str(data)[:200]}")
            
    return "\n".join(lines)
