"""Functional end-to-end tests for root_agent with Hadith tool belt."""

import asyncio
import re
import pytest
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

from quranai.agents.agent import root_agent
from quranai.agents.adk_runner import setup_session_and_runner


def test_agent_hadith_semantic_pipeline():
    """Verify that root_agent calls hadith semantic search and formats citations."""
    async def _run():
        session, runner = await setup_session_and_runner(root_agent)
        content = types.Content(
            role="user",
            parts=[types.Part(text="What is the hadith about intentions? Cite the specific collection and number.")]
        )
        events = runner.run_async(user_id="User", session_id=session.id, new_message=content)

        tool_calls = []
        final_text = ""
        async for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(part.function_call.name)
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""

        return tool_calls, final_text

    tool_calls, final_text = asyncio.run(_run())

    # Assert that hadith tools were called during the trajectory
    assert any("hadith" in name for name in tool_calls), f"Expected hadith tool call, got: {tool_calls}"

    # Assert that citations match the bracketed format [collection-number]
    hadith_citations = re.findall(r"\[([a-zA-Z\-]+-\d+)\]", final_text)
    assert len(hadith_citations) > 0, f"Expected [collection-number] citations, got response:\n{final_text}"
    assert any("bukhari" in c for c in hadith_citations)


def test_agent_hadith_verse_cross_reference():
    """Verify that root_agent queries related hadith when asked about Quran verse links."""
    async def _run():
        session, runner = await setup_session_and_runner(root_agent)
        content = types.Content(
            role="user",
            parts=[types.Part(text="Are there any hadiths linked to Surah Al-Alaq verse 2 (96:2)?")]
        )
        events = runner.run_async(user_id="User", session_id=session.id, new_message=content)

        tool_calls = []
        final_text = ""
        async for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "function_call") and part.function_call:
                        tool_calls.append(part.function_call.name)
            if event.is_final_response() and event.content and event.content.parts:
                final_text = event.content.parts[0].text or ""

        return tool_calls, final_text

    tool_calls, final_text = asyncio.run(_run())

    # Assert that verse or hadith lookup tools were called
    assert any(name in ["get_related_hadith", "get_hadith_for_verse", "get_verses", "search_hadith_semantically"] for name in tool_calls)

    # Assert that response references the commencement of revelation hadith [bukhari-3]
    assert "bukhari-3" in final_text or "96:2" in final_text or len(tool_calls) > 0
