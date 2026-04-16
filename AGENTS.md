# QuranAI app

This app is structured as follows. The core AI agent logic is exposed via a Frontend, CLI, and MCP server.

```
[Web Frontend] --- [Backend Server] ----- [AI Agent]
                   [CLI] --------------|
[Client Apps] ---- [MCP Server] -------|
```

The AI Agent is a combination of an Agentic framework and custom tools for the corpus.


## Development rules:

- Aways maintain a TODO list of completed and unfinished work in AGENTS.md
- Update README.md with installation, development, deployment, and testing instructions.
- Before making changes, write the proposed plan in a PLAN.md document. Only write code once I approve the plan. Remove PLAN.md after making code changes.

### Backend

- Write testable code. Python backend uses pytest, and defines tests under src/tests/
- Use `uv` for package management.
- ./Work.py contains example code using various functions. This is the playground.
- Use google-adk for AI agent development. The skeleton is defined in src/quranai/agent/
- Ignore legacy modules: src/quranai/agent.py and src/quranai/llm.py

#### Agent

The Agent is the main engine for executing LLM calls and tools. Agents are defined in src/quranai/agents/.

Library: https://google.github.io/adk-docs/

The agent has tools available for simple questions. It also has sub-agents to do complex retrieval, planning, summarization of questions.

#### API Server

The agents can be exposed by an API server. Documentation is at https://google.github.io/adk-docs/runtime/api-server/

When the API server is running, the Swagger UI docs are available @ http://localhost:8000/doc

#### CLI

The agent can run in a cli. See https://google.github.io/adk-docs/runtime/command-line/

### Frontend

Develop frontend code in src/frontend/

Put shared code in src/frontend/shared/

Use Rollup to bundle shared dependencies.

#### Firefox Extension

The extension runs only on alislam.org/quran/app.

The extension sends POST requests to the API server.

The extension creates a sidebar for chat.

It also makes buttons on hover on verses on the website. The buttons trigger a POST call to the API server to explain that verse. There are two buttons:

1. Explain the verse.
2. Add the verse to the chat context.

#### Web app

- The frontend is a web app.
- The app should support:
    - A chat interface
    - Scrolling through the corpus
    - Selecting and pinning parts of the corpus which get added to the context

### MCP Server

Use FastMCP library. The MCP server exposes:

- The tools in `quranai.quran.tools`
- The AI agent as a callable endpoint. See src/quranai/agents/adk_runner.py for an example of running an agent.

## TODOs

- [x] Add "About" modal to the web app with extension links and first-time user logic.
- [x] Create a Dockerfile and docker-compose.yaml for the backend and web app.
