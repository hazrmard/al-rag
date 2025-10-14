# QuranAI app

This is a python+react chat application. The backend implements a chat agent using various tools and retrieval augmented generation. The frontend exposes a chat interface, where the cited references can be viewed along with the agent responses.

## Development rules:

The entire app is deployed with a Dockerfile/docker-compose.yml.
README files describe features and user guides.

### Backend

- Write testable code. Python backend uses pytest, and defines tests under src/tests/
- Python uses `uv` for package management.
- ./Work.py contains example code using various functions. This is the playground.

### Frontend

- Frontend uses `vite`
- You can use tailwind for styling
- Write modular, documented components.