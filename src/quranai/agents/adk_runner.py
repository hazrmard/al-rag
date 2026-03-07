"""
Runs an ADK agent in a loop, printing out events and final response.
"""

from uuid import uuid4

from google.adk.agents import BaseAgent
from google.adk.runners import Runner
from google.genai import types
from google.adk.sessions import InMemorySessionService


async def setup_session_and_runner(agent: BaseAgent):
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=agent.name,
        user_id="User",
    )
    runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
    return session, runner


# Agent Interaction
async def call_agent_async(agent: BaseAgent, query: str):
    content = types.Content(role="user", parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner(agent=agent)
    events = runner.run_async(
        user_id="User", session_id=str(uuid4()), new_message=content
    )
    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Response: ", final_response)
