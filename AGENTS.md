# QuranAI app

This repository contains the **backend** for QuranAI. The web UI is a separate sibling project at `../ask-quran-react/`.

```
[ask-quran-react]   --- HTTP --->   [ADK API Server]   ----- [AI Agent]
[Client Apps / MCP] --- HTTP --->                       |
                                       [CLI] ----------|
```

The AI Agent is a combination of an Agentic framework (Google ADK) and custom tools for the corpus.


## Development rules

- Always maintain a TODO list of completed and unfinished work in this file.
- Update README.md with installation, development, deployment, and testing instructions.
- Before making changes, write the proposed plan in a PLAN.md document. Only write code once the plan is approved. Remove PLAN.md after making code changes.

### Backend

- Write testable code. Python backend uses pytest, and defines tests under `src/tests/`.
- Use `uv` for package management.
- `./Work.py` contains example code using various functions. This is the playground.
- Use google-adk for AI agent development. The skeleton is defined in `src/quranai/agents/`.
- Ignore legacy modules: `src/quranai/agent.py` and `src/quranai/llm.py`.

#### Agent

The Agent is the main engine for executing LLM calls and tools. Agents are defined in `src/quranai/agents/`.

Library: https://google.github.io/adk-docs/

The agent has tools available for simple questions. It also has sub-agents to do complex retrieval, planning, and summarization.

#### API Server

The agents can be exposed by an API server. Documentation is at https://google.github.io/adk-docs/runtime/api-server/

When the API server is running, the Swagger UI docs are available at http://localhost:$QURANAI_API_PORT/doc

#### CLI

The agent can run in a cli. See https://google.github.io/adk-docs/runtime/command-line/

### Web UI

The web UI is **not** in this repo. It is a Vite + React + TypeScript + MUI 9 app at `../ask-quran-react/`.

It calls this backend via the ADK API server endpoints (`POST /apps/{appName}/users/{userId}/sessions`, `POST /run`).

### MCP Server

Use FastMCP library. The MCP server exposes:

- The tools in `quranai.quran.tools`
- The AI agent as a callable endpoint. See `src/quranai/agents/adk_runner.py` for an example of running an agent.

## TODOs

- [x] Add "About" modal to the web app with extension links and first-time user logic.
- [x] Create a Dockerfile and docker-compose.yaml for the backend and web app.
- [x] Strip Svelte web UI and Firefox extension; the React UI lives in the sibling `ask-quran-react` project.
- [ ] Re-port the Firefox / Chrome extension to React (deferred).
- [ ] Implement the MCP server.
- [ ] Implement the CLI entry point.
