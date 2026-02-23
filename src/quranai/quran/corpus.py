"""Functions to load Quran corpus data."""

from typing import Generator
import json
import re
from collections import defaultdict

import requests
import chromadb

from quranai.utils import SingletonMeta, list_data_files, get_data_file_path

url = "https://api.openquran.com"
intro_url = "/express/chapter/intro/{ch}"
verses_url = "/express/chapter/{ch}:{start}-{end}"
chapters = 114
corpus_json = "quran.json"
vector_db = "quranai.chroma"
chunk_embed_dimension = 1024


payload = {
    "en": False,
    "zk": False,
    "sc": False,
    "v5": True,
    "cn": False,
    "sp_en": False,
    "sp_ur": False,
    "ur": False,
    "ts": False,
    "fr": False,
    "es": False,
    "de": False,
    "it": False,
    "my": False,
    "f": 1,
    "hover": 0,
}


def load_corpus_into_memory() -> list[dict]:
    """Load the entire Quran corpus into memory."""
    path = get_data_file_path(corpus_json)
    with open(path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        return list(corpus.values())


def download_ch(n=1, start=1, end=300) -> dict:
    vdata = []
    for s in range(start, end, 10):
        res = requests.post(
            (url + verses_url).format(ch=n, start=s, end=s + 10), json=payload
        )
        data = json.loads(res.content)
        if data == {"message": "invalid request"}:
            break
        vdata.extend(data)
    res = requests.get((url + intro_url).format(ch=n))
    intro_data = json.loads(res.content)
    return dict(**intro_data, verses=vdata)


def download_all_chapters(start=1, end=chapters + 1) -> list[dict]:
    return [download_ch(n, 1, 300) for n in range(start, end)]


def get_local_vector_db():
    path = get_data_file_path(vector_db)
    client = chromadb.PersistentClient(path)


# Processing functions for text elements
def sanitize_verse(s: str):
    """Remove [ ] footnote markers and <> tags from text"""
    square_brackets_pattern = r"\[[^\]]*\]"  # Matches anything inside square brackets
    angle_brackets_pattern = r"<[^>]*>"  # Matches anything inside angle brackets
    # Remove content inside square brackets
    result = re.sub(square_brackets_pattern, "", s)
    # Remove content inside angle brackets
    result = re.sub(angle_brackets_pattern, "", result)
    # Remove any extra spaces that may have been introduced
    result = re.sub(r"\s+", " ", result).strip()
    return result


def get_verses_in_chapter(ch: dict, sanitize: bool = False) -> dict[int, str]:
    v = {}
    for d in ch["verses"]:
        # v[d['v']] = sanitize_verse(' '.join(w['t'] for w in d['words'] if w['t'] is not None))
        v[d["v"]] = sanitize_verse(d["v5"]["text"]) if sanitize else d["v5"]["text"]
    return v


def get_referenced_verses_in_corpus() -> dict[str, str]:
    """Return a mapping of "ch:verse" to verse text for the entire corpus."""
    verses = {}
    for i, ch in enumerate(Corpus().quran):
        verses.update(
            {f"{i+1}:{v}": text for v, text in get_verses_in_chapter(ch).items()}
        )
    return verses


def sanitize_topic(s: str):
    return sanitize_verse(",".join(s.split(":")))


def get_topics(q: list[dict]) -> tuple[list[str], dict[str, list[str]]]:
    """Extract topics and a mapping of references from the Quran corpus.
    The topics is a sorted list of strings.
    The references are a mapping of topics to their occurrences in the format "ch:verse".
    For example:
        "faith": ["1:1", "2:2"],
        "prayer": ["2:3", "2:4"]

    Args:
        q (list[dict]): The Quran corpus data.

    Returns:
        tuple[list[str], dict[str, list[str]]]: A tuple containing a
        list of unique topics and a mapping of topics to their references.
    """
    reverse = defaultdict(list, {})
    t = set()
    for ch in q:
        for v in ch["verses"]:
            for topic in v["topics"]:
                t_ = sanitize_topic(topic["topic"])
                t.add(t_)
                reverse[t_].append("%d:%d" % (v["ch"], v["v"]))
    return sorted(list(t)), reverse


class Corpus(metaclass=SingletonMeta):
    """This is a singleton class to hold the Quran corpus in memory."""

    def __init__(self):
        self.quran = load_corpus_into_memory()
        self.topics, self.references = get_topics(self.quran)
        self.vector_db = None


def _prepare_verse_for_embedding(verse: dict) -> str:
    """Prepare a verse for embedding by concatenating the chapter and verse number with the sanitized verse text.

    Args:
        verse (dict): A dictionary containing the verse data, including chapter number, verse number, and verse text.

    Returns:
        str: A string in the format "ch:verse: sanitized_verse_text" ready for embedding.
    """
    ch = verse["ch"]
    v = verse["v"]
    text = sanitize_verse(verse["v5"]["text"])
    footnotes = "\n".join(f"[{n['ref']}]: {n['note']}" for n in verse["v5"]["notes"])
    if footnotes:
        text += "\n" + footnotes
    return f"{ch}:{v}: {text}"


def _prepare_verse_for_display(verse: dict) -> str:
    """Prepare a verse for display by concatenating the chapter and verse number with the original verse text.

    Args:
        verse (dict): A dictionary containing the verse data, including chapter number, verse number, and verse text.

    Returns:
        str: A string in the format "ch:verse: original_verse_text" ready for display.
    """
    ch = verse["ch"]
    v = verse["v"]
    text = verse["v5"]["text"]
    return f"{ch}:{v}: {text}"


def chunks(corpus: Corpus, chunk_size: int = 2) -> Generator[list[str]]:
    iterator = (
        _prepare_verse_for_display(v)
        for chapter in corpus.quran
        for v in chapter["verses"]
    )
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) == chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    from google.genai.types import EmbedContentConfig
    from google.genai import Client
    import os

    client = Client(api_key=os.getenv("GOOGLE_API_KEY"))
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=chunks,
        config=EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT", output_dimensionality=chunk_embed_dimension
        ),
    )
    if result.embeddings is None or result.embeddings[0].values:
        raise ValueError("Embedding failed: no embeddings returned")
    return [result.embeddings[i].values for i in range(len(chunks))]  # type: ignore


def _build():
    """This function builds an index of the corpus.

    Steps:
    1. Generate chunks from the corpus.
    2. Generate metadata for each chunk (topics, cross-references etc.)
    3. Generate embeddings for each chunk.
    4. Store the chunks and their embeddings in a vector database."""
    pass


if __name__ == "__main__":
    _build()
