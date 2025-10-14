"""
This is the entrypoint for the backend server which serves the React Frontend.

    python -m quranai.server
"""

from argparse import ArgumentParser
from quranai.agent import CustomBaseAgent
from quranai.quran.agent import CustomQuranAgent


def make_server():
    # Create a server with a chat endpoint
    # The server maintains session state
    # Endpoints:
    # - /chat: The main chat endpoint. Takes a string, returns a string.
    # - /reset: Reset the chat session
    # - /refs: The references mentioned so far in the chat. Returns a dict[str, str] mapping ref to content.
    pass


if __name__ == "__main__":
    server = make_server()
    # run server
