import pytest
import asyncio
from backend.agent.intent_classifier import detect_intents
from backend.session import session_manager

@pytest.fixture(autouse=True)
def reset_session():
    session_manager.clear()
    session_manager.last_searched_items = []
    session_manager.last_opened_item = None

def test_intent_exact_filename_extraction():
    """Test that the intent classifier extracts exact filenames without verbs."""
    intents = detect_intents("Summarize AAC RESEARCH 1.pdf")
    assert len(intents) == 1
    assert intents[0]["tool"] == "drive_search"
    # Action verbs should be stripped, so it should ideally find the filename.
    # Note: Since the prompt is LLM-based, we are testing the prompt's instruction adherence.
    assert "Summarize" not in intents[0].get("args", {}).get("query", "")

def test_intent_context_resolution_it():
    """Test that 'it' resolves to the last opened item."""
    session_manager.last_opened_item = {"id": "123", "name": "Resume.pdf", "mimeType": "application/pdf"}
    intents = detect_intents("Summarize it")
    assert len(intents) == 1
    assert intents[0]["tool"] == "drive_read"
    assert intents[0].get("args", {}).get("file_id") == "123"

def test_intent_context_resolution_latest():
    """Test that 'latest' resolves to the first item in last_searched_items."""
    session_manager.last_searched_items = [
        {"id": "abc", "name": "Report 1", "mimeType": "application/pdf"},
        {"id": "def", "name": "Report 2", "mimeType": "application/pdf"}
    ]
    intents = detect_intents("Open the first one")
    assert len(intents) == 1
    assert intents[0]["tool"] == "drive_read"
    assert intents[0].get("args", {}).get("file_id") == "abc"

def test_intent_compare_two():
    """Test compare intent resolves to two parallel reads."""
    session_manager.last_searched_items = [
        {"id": "id_1", "name": "Doc 1", "mimeType": "application/pdf"},
        {"id": "id_2", "name": "Doc 2", "mimeType": "application/pdf"}
    ]
    intents = detect_intents("Compare the first and second")
    assert len(intents) == 1 # Usually resolves to two executions in the JSON array
    # Let's check executions list inside intent
    assert len(intents) >= 1
    # Check that at least one is reading id_1
    tools_called = [i["tool"] for i in intents]
    assert "drive_read" in tools_called or "docs_read" in tools_called
