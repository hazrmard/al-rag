"""User-facing status strings for the chat UI loading indicator.

These constants describe what the agent is doing while the user waits.
The web UI in ``../ask-quran-react`` mirrors these strings and may show
tool-specific messages once it consumes ``/run_sse`` events. Keep this
module as the canonical source for the wording.
"""

from __future__ import annotations


DEFAULT_LOADING_MESSAGE: str = "Searching in the Holy Quran and commentaries"

TOOL_STATUS_MESSAGES: dict[str, str] = {
    "get_chapter_intro": "Reading the chapter introduction",
    "search_chapter_intros_semantically": "Looking through chapter introductions",
    "get_verses": "Fetching verses",
    "get_verse_footnotes": "Reading verse commentaries",
    "search_verses_semantically": "Searching the Holy Quran",
    "search_topics_semantically": "Searching topics",
    "get_verses_for_topic": "Gathering verses for the topic",
    "deepdive_agent": "Performing a deep-dive analysis",
}


def status_for_tool(tool_name: str) -> str:
    """Return a user-friendly status message for a tool name.

    Falls back to :data:`DEFAULT_LOADING_MESSAGE` when the tool is not
    listed.
    """
    return TOOL_STATUS_MESSAGES.get(tool_name, DEFAULT_LOADING_MESSAGE)
