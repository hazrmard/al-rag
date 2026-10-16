"""Functions to load Quran corpus data.

Schema from API.

```
chapter_name: str
chapter_name_ur: str
ch: int
intro_en: str
intro_ur: str
verses: list of dict:
  ch: int
  v: int
  v_: int
  topics: list of dict:
    id: int
    topic: str
    verses: str
  ar: str
  words: list of dict:
    t: str
  tq:
    ch: int
    v: int
    url: str
  tafaseer: list of str
  v5:
    text: str
    notes: list of dict:
      ref: str
      note: str
  citations: list of dict:
    title: str
    slug: str
    language: str
  hadiths: list of dict:
    slug: str       # id of hadith (collectionId-hadithNumber, see hadith/corpus.py)
    title: str
```
"""

import json
import time
from datetime import datetime
import re
from collections import defaultdict
from typing import Any, Generator, Literal

import chromadb
from chromadb.api import ClientAPI
import requests
from tqdm import tqdm, trange
from google.genai.errors import ClientError as GoogleClientError

from quranai.utils import (
    SingletonMeta,
    get_data_file_path,
    embed_chunks,
    CustomEmbeddingFunction,
)

url = "https://api.openquran.com"
intro_url = "/express/chapter/intro/{ch}"
verses_url = "/express/chapter/{ch}:{start}-{end}"
chapters = 114
corpus_json = "quran.json"
vector_db = "quranai.chroma"


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
    if not path.is_file():
        raise FileNotFoundError(
            f"Corpus JSON file not found at {path}. Please run download_quran.py in scripts/."
        )
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


def get_local_vector_db(_allow_empty: bool = False) -> ClientAPI:
    path = get_data_file_path(vector_db)
    if not _allow_empty and not (path.is_file() or path.is_dir()):
        raise FileNotFoundError(
            f"Vector database not found at {path}. Please run quran indexing scripts in scripts/."
        )
    client = chromadb.PersistentClient(path)
    return client


def get_verses_collection(db: ClientAPI) -> chromadb.Collection:
    return db.get_or_create_collection(
        name="verses", embedding_function=CustomEmbeddingFunction()
    )


def get_topics_collection(db: ClientAPI) -> chromadb.Collection:
    return db.get_or_create_collection(
        name="topics", embedding_function=CustomEmbeddingFunction()
    )


def get_chapter_intros_collection(db: ClientAPI) -> chromadb.Collection:
    return db.get_or_create_collection(
        name="chapter_intros", embedding_function=CustomEmbeddingFunction()
    )


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

    def __init__(
        self,
        mode: Literal["local", "remote"] = "local",
        _allow_empty: bool = False,
    ):
        self.quran = load_corpus_into_memory()
        self.topics, self.references = get_topics(self.quran)
        if mode == "local":
            self.vector_db = get_local_vector_db(_allow_empty=_allow_empty)
            self.verses_collection = get_verses_collection(self.vector_db)
            self.topics_collection = get_topics_collection(self.vector_db)
            self.chapter_intros_collection = get_chapter_intros_collection(
                self.vector_db
            )
            if not _allow_empty and (
                self.verses_collection.count() == 0
                or self.topics_collection.count() == 0
                or self.chapter_intros_collection.count() == 0
            ):
                raise ValueError(
                    "Vector database is empty. Please run quran download/indexing scripts in quranai/scripts/."
                )
        elif mode == "remote":
            raise NotImplementedError("Remote mode is not implemented yet")
        else:
            raise ValueError("Invalid mode. Use 'local' or 'remote'.")


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
    footnotes = "Footnotes:\n" + "\n".join(
        f"[{n['ref']}]: {n['note']}" for n in verse["v5"]["notes"]
    )
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


def chunks(
    corpus: Corpus, chunk_size: int = 2, overlap: int = 0
) -> Generator[tuple[str, str, dict[str, Any]], None, None]:
    assert chunk_size > 0, "Chunk size must be greater than 0"
    assert 0 <= overlap < chunk_size, "Overlap must be between 0 and chunk size"
    for chapter in corpus.quran:
        iterator = (v for v in chapter["verses"])
        batch = []
        ch_ = chapter["ch"]
        for verse in iterator:
            batch.append(_prepare_verse_for_embedding(verse))
            if len(batch) == chunk_size:
                id_ = f"{ch_}:{verse['v']-chunk_size+1}-{verse['v']}"
                metadata = dict(ch=ch_)
                yield id_, "\n\n".join(batch), metadata
                batch = batch[-overlap:]
        if batch:
            id_ = f"{ch_}:{verse['v']-len(batch)+1}-{verse['v']}"  # type: ignore
            yield id_, "\n\n".join(batch), dict(ch=ch_)


def _build_verse_index(batches_per_request=20):
    """This function builds an index of the corpus.

    Steps:
    1. Generate chunks from the corpus.
    2. Generate metadata for each chunk (topics, cross-references etc.)
    3. Generate embeddings for each chunk.
    4. Store the chunks and their embeddings in a vector database."""
    corpus = Corpus(_allow_empty=True)
    ids, chunks_, metadata = zip(*chunks(corpus, chunk_size=10, overlap=2))
    start = datetime.now()
    for i in trange(0, len(chunks_), batches_per_request, leave=False):
        batch_chunks = list(chunks_[i : i + batches_per_request])
        batch_ids = list(ids[i : i + batches_per_request])
        batch_metadata = list(metadata[i : i + batches_per_request])
        try:
            embeddings = embed_chunks(batch_chunks)
        except GoogleClientError as e:
            delay = 60 - (datetime.now() - start).seconds
            print(f"Google API error: {e}. Retrying after a delay of {delay} seconds.")
            time.sleep(delay)  # wait for the minute to pass
            start = datetime.now()
            embeddings = embed_chunks(batch_chunks)
        collection = corpus.verses_collection
        collection.upsert(
            embeddings=embeddings, ids=batch_ids, metadatas=batch_metadata
        )


def _build_topic_index(batches_per_request=100):
    """This function builds an index of the corpus.

    Steps:
    1. Generate topics from the corpus.
    2. Generate embeddings for each topic.
    3. Store the topics and their embeddings in a vector database."""
    corpus = Corpus(_allow_empty=True)
    topics = corpus.topics
    start = datetime.now()
    for i in trange(0, len(topics), batches_per_request, leave=False):
        batch_topics = list(topics[i : i + batches_per_request])
        batch_ids = topics[i : i + batches_per_request]
        try:
            embeddings = embed_chunks(batch_topics)
        except GoogleClientError as e:
            delay = 60 - (datetime.now() - start).seconds
            print(f"Google API error: {e}. Retrying after a delay of {delay} seconds.")
            time.sleep(delay)  # wait for the minute to pass
            start = datetime.now()
            embeddings = embed_chunks(batch_topics)
        collection = corpus.topics_collection
        collection.upsert(embeddings=embeddings, ids=batch_ids)


def _build_chapter_intro_index():
    """This function builds an index of chapter introductions in the corpus."""
    corpus = Corpus(_allow_empty=True)
    batches_per_request = 5

    def _chunks():
        batch, ids = [], []
        for ch in corpus.quran:
            intro = ch["intro_en"]
            if intro:
                id_ = f"{ch['ch']} - {ch['chapter_name']}"
                batch.append(intro)
                ids.append(id_)
                if len(batch) == batches_per_request:
                    yield ids, batch
                    batch, ids = [], []
        if batch:
            yield ids, batch

    start = datetime.now()
    for ids, chunks in tqdm(
        _chunks(),
        total=(
            len(corpus.quran) // batches_per_request
            + len(corpus.quran) % batches_per_request
        ),
        leave=False,
    ):
        try:
            embeddings = embed_chunks(chunks)
        except GoogleClientError as e:
            delay = 60 - (datetime.now() - start).seconds
            print(f"Google API error: {e}. Retrying after a delay of {delay} seconds.")
            time.sleep(delay)  # wait for the minute to pass
            start = datetime.now()
            embeddings = embed_chunks(chunks)
        collection = corpus.chapter_intros_collection
        collection.upsert(embeddings=embeddings, ids=ids)
