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

### Frontend

- The frontend is a web app.
- The app should support:
    - A chat interface
    - Scrolling through the corpus
    - Selecting and pinning parts of the corpus which get added to the context

### MCP Server

The MCP server exposes:

- The tools in `quranai.quran.tools`
- The AI agent as a callable endpoint

## TODOs