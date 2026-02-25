from google.adk.agents.llm_agent import Agent

from quranai.quran import tools

root_agent = Agent(
    model="gemini-2.5-flash",
    name="root_agent",
    description="A helpful assistant for user questions about the Quran.",
    instruction="Answer user questions to the best of your knowledge. Always cite sources. Make a best effort plan to investigate sources to answer the question.",
    tools=[
        tools.get_chapter_intro,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
    ],
)
