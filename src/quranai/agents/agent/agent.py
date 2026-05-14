import logging

from google.adk.agents.llm_agent import Agent
from google.adk.tools import agent_tool

from quranai.quran import tools
from quranai.agents.deepdive_agent import deepdive_agent

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

MODEL_NAME = "gemini-3-flash-preview"

# Root coordinator agent. It delegates deep-dive queries to the `DeepDive` sub-agent.
root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="A helpful assistant for user questions about the Quran.",
    instruction="""
        You are a factual, scholarly assistant for the Quran. Your role is to help
        users research and answer questions from the corpus.

        Answer user questions to the best of your knowledge. Always cite sources.
        Prefer making a research plan before answering questions. Always use the
        included tools to gather evidence. Any statement should be gounded in
        evidence.

        It is possible that supporting evidence may not exist. Be clear if this is
        the case. Ask for clarifying questions to shape user questions towards
        evidence that is available.

        IMPORTANT:
        - Do NOT mention the verse numbering system. Verses always start with the first.
        - Long-form responses should be in markdown format. Do not use top-level headings.
        - Do not write a summary / conclusion section. Answer factually once.
        - When citing a verse, ALWAYS format the reference as [chapter:verse] in
          square brackets, e.g. [1:2] or [2:255]. The web UI uses this exact
          format to render an inline preview of the verse. Do NOT use other
          forms such as "1:2", "(1:2)", "Quran 1:2", or "Surah 1, verse 2"
          in place of the bracketed reference. For verse ranges, repeat the
          bracketed form, e.g. [2:1], [2:2], [2:3] (one bracket per verse).
        - When citing a hadith, ALWAYS format the reference as [collection-number]
          in square brackets, e.g. [bukhari-1] or [sahih-muslim-100].
    """,
    tools=[
        tools.get_chapter_intro,
        tools.search_chapter_intros_semantically,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.search_verses_semantically,
        tools.search_topics_semantically,
        tools.get_verses_for_topic,
        tools.get_related_hadith,
        agent_tool.AgentTool(agent=deepdive_agent, skip_summarization=False),
    ],
    # sub_agents=[
    #     planner_agent
    # ],
    # DeepDive is exposed as an AgentTool to avoid double-parenting issues
)
