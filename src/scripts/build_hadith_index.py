"""Build vector DB of hadith"""

from dotenv import load_dotenv
from quranai.hadith.corpus import _build_hadith_index

if __name__ == "__main__":
    load_dotenv()
    _build_hadith_index()
