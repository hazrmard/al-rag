from google.adk.agents.llm_agent import Agent

from quranai.quran import tools

root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for user questions.",
    instruction="Answer user questions to the best of your knowledge",
    tools=[
        tools.get_chapter_intro,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.extract_verse_references,
        tools.get_cross_references,
    ],
)
