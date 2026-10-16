"""Unit tests for Hadith tool belt and agent integration."""

import pytest
from dotenv import load_dotenv

load_dotenv()

from quranai.hadith import tools as hadith_tools
from quranai.quran import tools as quran_tools
from quranai.agents.agent import root_agent
from quranai.ui_status import status_for_tool


def test_get_hadith_by_id_valid():
    hadith = hadith_tools.get_hadith_by_id("bukhari-1")
    assert hadith["id"] == "bukhari-1"
    assert hadith["collection"] == "bukhari"
    assert "intentions" in hadith["theme"].lower()
    assert len(hadith["text"]) > 0
    assert isinstance(hadith["linked_hadiths"], list)


def test_get_hadith_by_id_brackets_and_case():
    hadith = hadith_tools.get_hadith_by_id("[BUKHARI-1]")
    assert hadith["id"] == "bukhari-1"
    assert hadith["collection"] == "bukhari"


def test_get_hadith_by_id_not_found():
    result = hadith_tools.get_hadith_by_id("nonexistent-99999")
    assert "error" in result
    assert "not found" in result["error"].lower()


def test_get_hadith_arabic_fallback():
    # bukhari-411 has no English translation in hadith.json
    hadith = hadith_tools.get_hadith_by_id("bukhari-411")
    assert hadith["id"] == "bukhari-411"
    assert hadith["theme"] != ""
    assert "[Arabic text]" in hadith["text"]
    assert hadith["arabic"] != ""


def test_get_related_hadith():
    related = hadith_tools.get_related_hadith("bukhari-1", num_results=3)
    assert len(related) > 0
    assert related[0]["id"] == "bukhari-395"
    assert "theme" in related[0]


def test_get_hadith_for_verse():
    verse_hadiths = hadith_tools.get_hadith_for_verse(96, 2, num_results=3)
    assert len(verse_hadiths) > 0
    ids = [h["id"] for h in verse_hadiths]
    assert "bukhari-3" in ids


def test_search_hadith_semantically():
    results = hadith_tools.search_hadith_semantically("intention behind actions", num_results=3)
    assert len(results) > 0
    assert "distance" in results[0]
    # Verify that intention-related hadiths are retrieved
    themes = " ".join([h["theme"].lower() for h in results])
    assert "intention" in themes


def test_quran_tools_get_related_hadith_delegation():
    results = quran_tools.get_related_hadith(ch=96, verse=2, num_results=2)
    assert len(results) > 0
    ids = [h.get("id") or h.get("hadith_id") for h in results]
    assert any("bukhari" in i for i in ids if i)


def test_root_agent_has_hadith_tools():
    tool_names = []
    for t in root_agent.tools:
        if hasattr(t, "name"):
            tool_names.append(t.name)
        elif hasattr(t, "__name__"):
            tool_names.append(t.__name__)

    assert "get_hadith_by_id" in tool_names
    assert "search_hadith_semantically" in tool_names
    assert "get_related_hadith" in tool_names
    assert "When citing a hadith" in root_agent.instruction


def test_root_agent_hadith_tools_disabled(monkeypatch):
    import importlib
    from quranai.agents.agent import agent as agent_module

    monkeypatch.setenv("ENABLE_HADITH_TOOLS", "false")
    importlib.reload(agent_module)
    try:
        tool_names = []
        for t in agent_module.root_agent.tools:
            if hasattr(t, "name"):
                tool_names.append(t.name)
            elif hasattr(t, "__name__"):
                tool_names.append(t.__name__)

        assert "get_hadith_by_id" not in tool_names
        assert "search_hadith_semantically" not in tool_names
        assert "get_related_hadith" not in tool_names
        assert "When citing a hadith" not in agent_module.root_agent.instruction
    finally:
        monkeypatch.delenv("ENABLE_HADITH_TOOLS", raising=False)
        importlib.reload(agent_module)


def test_ui_status_hadith_tools():
    assert status_for_tool("get_hadith_by_id") == "Retrieving Hadith"
    assert status_for_tool("search_hadith_semantically") == "Searching the Hadith corpus"
    assert status_for_tool("get_related_hadith") == "Finding related Hadith"
    assert status_for_tool("get_hadith_for_verse") == "Finding Hadith related to this verse"
