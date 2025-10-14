# React + Vite Frontend

This is a React app for backend defined in /src/quranai/

## Features

The app has the following features:

- A rich chat interface.
- A view area for cited references.
- The ability to select/unselect previously cited references which automatically get added to the message.
    - For example, a function composes the user message and appends a string "<context>REFERENCES</context>" before sending it to the chat/ endpoint.
- The ability to reset a chat / create a new chat.
- Storing previous chats in history (perhaps in a sidebar etc.). Using the llm to generate a few-word title for the chat.