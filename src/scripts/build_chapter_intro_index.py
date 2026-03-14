from dotenv import load_dotenv
from quranai.quran.corpus import _build_chapter_intro_index

if __name__ == "__main__":
    load_dotenv()
    _build_chapter_intro_index()
