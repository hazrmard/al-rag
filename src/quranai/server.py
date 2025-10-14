"""
This is the entrypoint for the backend server which serves the React Frontend.

    python -m quranai.server

The server creates a CustomBaseAgent with a CustomQuranAgent sub-agent inside.
The server maintains session state, containing the AgentState.
The server can store multiple AgentStates for a single user (chat history).
"""

from argparse import ArgumentParser
from typing import Optional
from quranai.llm import LLM
from quranai.agent import CustomBaseAgent
from quranai.quran.agent import CustomQuranAgent
from quranai.utils import extract_tool_results_from_state, AgentState
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uuid
import os


def make_agent(llm: Optional[LLM] = None) -> CustomBaseAgent:
    """Create the main agent with a Quran sub-agent.
    The agent has a __call__ method which is pure, and operates on AgentState.

        agent_state = agent(task, agent_state)

    Returns:
        CustomBaseAgent: The main agent with a Quran sub-agent.
    """
    llm = llm or LLM(model_name="gpt-4.1-mini")
    quran_assistant = CustomQuranAgent(name="quran_assistant")
    agent = CustomBaseAgent(
        model=llm,
        tools=[],
        agents=[quran_assistant],
    )
    return agent


# In-memory session storage
sessions = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ResetRequest(BaseModel):
    session_id: str


def make_server():
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    agent = make_agent()

    @app.post("/api/chat")
    async def chat(request: ChatRequest):
        session_id = request.session_id
        if not session_id or session_id not in sessions:
            session_id = str(uuid.uuid4())
            sessions[session_id] = AgentState(messages=(), agent_states=())

        agent_state = sessions[session_id]

        # Call the agent
        agent_state = agent(request.message, agent_state)
        response_message = agent_state["messages"][-1]["content"]

        sessions[session_id] = agent_state

        return JSONResponse(
            content={"response": response_message, "session_id": session_id}
        )

    @app.post("/api/reset")
    async def reset(request: ResetRequest):
        session_id = request.session_id
        if session_id and session_id in sessions:
            del sessions[session_id]
            return JSONResponse(content={"status": "ok"})
        return JSONResponse(content={"status": "session not found"}, status_code=404)

    @app.get("/api/refs")
    async def get_refs(session_id: str):
        # agent_state = sessions.get(session_id)
        # if agent_state:
        #     tool_results = extract_tool_results_from_state(agent_state)
        #     return JSONResponse(content=tool_results)
        return JSONResponse(content={})  # For now, as requested

    @app.get("/api/state")
    async def get_state(session_id: str):
        agent_state = sessions.get(session_id)
        if agent_state:
            return JSONResponse(content=dict(agent_state))
        return JSONResponse(content={"status": "session not found"}, status_code=404)

    # Serve the frontend
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    if os.path.exists(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")

    return app


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the server on")
    parser.add_argument(
        "--port", default=8000, type=int, help="Port to run the server on"
    )
    args = parser.parse_args()

    app = make_server()
    uvicorn.run(app, host=args.host, port=args.port)
