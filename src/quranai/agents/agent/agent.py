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

        IMPORTANT:
        - Verse numbers always count the first verse.
        - Long-form responses should be in markdown format. Do not use top-level headings.
        - Do not write a summary / conclusion section. Answer factually once.
    """,
    tools=[
        tools.get_chapter_intro,
        tools.get_verses,
        tools.get_verse_footnotes,
        tools.get_verses_for_query,
        tools.get_topics_for_query,
        tools.get_verses_for_topic,
        agent_tool.AgentTool(agent=deepdive_agent, skip_summarization=False),
    ],
    # sub_agents=[
    #     planner_agent
    # ],
    # DeepDive is exposed as an AgentTool to avoid double-parenting issues
)
