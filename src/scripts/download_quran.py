"""Download Quran into a json DB."""

import json
from quranai.quran.corpus import download_ch, corpus_json
from quranai.utils import get_data_file_path
from tqdm import trange

if __name__ == "__main__":
    quran = {}
    for i in trange(1, 115, leave=False):
        quran[i] = download_ch(i)
    with open(get_data_file_path(corpus_json), "w") as f:
        json.dump(quran, f)
