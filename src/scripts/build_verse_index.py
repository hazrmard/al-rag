from dotenv import load_dotenv
from quranai.quran.corpus import _build

if __name__ == "__main__":
    load_dotenv()
    _build()
    print("Verse index built successfully.")
