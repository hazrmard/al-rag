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
- Before making changes, write a plan and ask for approval.
- Write testable, documented (numpy docstrings) code. Uses pytest, and define tests under `src/tests/`.
- Use `uv` for package management.
- Use google-adk for AI agent development. The skeleton is defined in `src/quranai/agents/`.
- Ignore legacy modules: `src/quranai/agent.py` and `src/quranai/llm.py`.

## Agent engine

The Agent is the main engine for executing LLM calls and tools. Agents are defined in `src/quranai/agents/`.

Library: https://google.github.io/adk-docs/

The agent has tools available for simple questions. It also has sub-agents to do complex retrieval, planning, and summarization.

The agent framework is connected to tools defined for various agents. For example, tools for Quranic research are defined in `src/quranai/quran/tools.py`.

### API Server

The agents can be exposed by an API server. Documentation is at https://google.github.io/adk-docs/runtime/api-server/

When the API server is running, the Swagger UI docs are available at http://localhost:$QURANAI_API_PORT/doc

### CLI

The agent can run in a cli. See https://google.github.io/adk-docs/runtime/command-line/

## TODOs

