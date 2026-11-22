"""Download hadith into a JSON db."""

import json
from dotenv import load_dotenv
from quranai.hadith.corpus import download_all_pages, corpus_json
from quranai.utils import get_data_file_path

if __name__ == "__main__":
    load_dotenv()
    hadiths = download_all_pages()
    with open(get_data_file_path(corpus_json, ensure_dir=True), "w") as f:
        json.dump(hadiths, f)
