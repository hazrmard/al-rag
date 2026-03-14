"""Build indices.

Usage:

    python build_verse_index.py  # builds topic and verse indices
    python build_verse_index.py topic  # builds topic index
    python build_verse_index.py verse  # builds verse index
"""

from dotenv import load_dotenv
from quranai.quran.corpus import _build_topic_index, _build_verse_index
import sys

if __name__ == "__main__":

    load_dotenv()
    if len(sys.argv) > 1 and sys.argv[1] == "topic" or len(sys.argv) == 1:
        _build_topic_index()
        print("Topic index built successfully.")
    if len(sys.argv) > 1 and sys.argv[1] == "verse" or len(sys.argv) == 1:
        _build_verse_index()
        print("Verse index built successfully.")
