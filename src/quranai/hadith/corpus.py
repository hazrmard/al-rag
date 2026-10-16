"""Functions to process Hadith corpus.

Schema from API (hadith.json):

```yaml
data: list of dict:
  collectionId: str                 # Collection identifier (e.g. "bukhari", "sahih-muslim", "gardens-of-righteous", "hadiqatus-saliheen", "ibn-e-maja")
  slug: str                         # URL slug for hadith (e.g. "bukhari-1")
  printPageNum: str                 # Printed edition page number (e.g. "۲")
  pdfPageNum: int                   # PDF page number in digital scan
  id: str                           # Primary key, format "{collectionId}-{hadithNumber}" (e.g. "bukhari-1", "sahih-muslim-224")
  hadithNumber: str                 # Hadith number within collection (e.g. "1", "4922")
  bookName: str                     # Arabic book title (e.g. "كتاب بدء الوحى")
  bookNameTr: str                   # Transliterated/translated book title (e.g. "Kitab Bad-il-Wahi")
  bookSlug: str                     # URL slug for book (e.g. "kitab-bad-il-wahi")
  bookNum: int                      # Sequential book index within collection (e.g. 1)
  chapterNumber: int                # Sequential chapter index within book (e.g. 1)
  chapterName: str                  # Chapter title in English/Urdu (e.g. "On Sincerity and the Importance of Motive...", empty string if none)
  arabic: str                       # Full Arabic text, often with bracketed narrator names: "[الحميدي] حدثنا..."
  narratorIds: list of str          # IDs of narrators in the transmission chain (isnad)
  urduOriginal: str                 # Original Urdu translation text
  urdu: str                         # Formatted Urdu translation of the hadith
  english: str                      # English translation text (present for 2,486 records; empty string "" for 14,959 records)
  tashrih: str                      # Extended commentary or explanation in Urdu
  quranicReferences: str            # Comma-separated Quran verse references in "ch:verse" format (e.g. "96:2,96:3,96:4" or "3:65", empty string "" if none)
  linkedQuranicReferences: list     # Structured Quranic references (empty list in current dataset)
  reference: str                    # Traditional Urdu citation string (e.g. "صحیح البخاری, كتاب بدء الوحى, باب نمبر ۱...")
  hadithReference: str              # Cross-reference citation string (e.g. "(بخاری کتاب الایمان  باب کیف کان بدء الوحی 1)")
  theme: str                        # Natural language English summary/moral of the hadith (present for all 16,855 records)
  linkedHadithIds: list of str      # Related/thematic parallel hadith IDs (e.g. ["bukhari-395", "bukhari-73", "sahih-muslim-3516"])
  nextHadithId: str                 # ID of next sequential hadith (e.g. "bukhari-2")
count: int
pagination:
  page: int
  pageSize: int
  totalPages: int
  total: int
```
"""

from collections import defaultdict
from typing import Generator, Literal
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import time

import chromadb
from chromadb.api import ClientAPI
from tqdm.autonotebook import tqdm, trange
from google.genai.errors import ClientError as GoogleClientError

from quranai.utils import (
    get_data_file_path,
    CustomEmbeddingFunction,
    SingletonMeta,
    embed_chunks,
)

HADITH_API_BASE = "https://api.readhadith.app/ahadith/"
corpus_json = "hadith.json"
vector_db = "quranai.chroma"
max_chunk_length = 2048


def download_page(page: int = 1) -> dict:
    url = HADITH_API_BASE + "?page={page}"
    try:
        response = requests.get(url.format(page=page))
        content = response.content
        data = json.loads(content)
    except Exception as exc:
        raise exc
    return data


def download_all_pages() -> list[dict]:
    pg1 = download_page(1)
    hadiths = [*pg1["data"]]
    total_pages = pg1["pagination"]["totalPages"]
    # total_pages = 5
    concurrency = 16
    with ThreadPoolExecutor(concurrency) as pool:
        futures = [pool.submit(download_page, pg) for pg in range(2, total_pages + 1)]
        for future in tqdm(as_completed(futures), total=total_pages - 1, leave=False):
            hadiths.extend(future.result()["data"])
    return hadiths


def load_corpus_into_memory() -> list[dict]:
    """Load the entire Hadith corpus into memory."""
    path = get_data_file_path(corpus_json)
    if not path.is_file():
        raise FileNotFoundError(
            f"Corpus JSON file not found at {path}. Please run download_hadith.py in scripts/."
        )
    with open(path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        return corpus


def get_local_vector_db(_allow_empty: bool = False) -> ClientAPI:
    path = get_data_file_path(vector_db)
    if not _allow_empty and not (path.is_file() or path.is_dir()):
        raise FileNotFoundError(
            f"Vector database not found at {path}. Please run hadith indexing scripts in scripts/."
        )
    client = chromadb.PersistentClient(path)
    return client


def get_hadith_collection(db: ClientAPI) -> chromadb.Collection:
    return db.get_or_create_collection(
        name="hadith", embedding_function=CustomEmbeddingFunction()
    )


def _prepare_hadith_for_embedding(hadith: dict) -> str:
    template = """
    Theme: {theme}

    Text: {hadith}
    """.strip()
    return template.format(theme=hadith["theme"], hadith=hadith["english"])[
        :max_chunk_length
    ]


class Corpus(metaclass=SingletonMeta):
    """This is a singleton class to hold the Hadith corpus in memory."""

    def __init__(self, mode: Literal["local", "remote"] = "local", _allow_empty: bool=False):
        self.hadith = load_corpus_into_memory()
        self.by_id: dict[str, dict] = {h["id"]: h for h in self.hadith}
        self.by_verse: dict[str, list[str]] = self._build_verse_index()
        if mode == "local":
            self.vector_db = get_local_vector_db(_allow_empty=_allow_empty)
            self.hadith_collection = get_hadith_collection(self.vector_db)
            if not _allow_empty and self.hadith_collection.count() == 0:
                raise ValueError("Vector database is empty. Please run hadith download/indexing scripts in quranai/scripts/.")
        elif mode == "remote":
            raise NotImplementedError("Remote mode is not implemented yet")
        else:
            raise ValueError("Invalid mode. Use 'local' or 'remote'.")

    def _build_verse_index(self) -> dict[str, list[str]]:
        """Build an inverted index mapping Quran verse references to Hadith IDs.

        Parses the `quranicReferences` field on each hadith in the corpus. In
        `hadith.json`, this field is stored as a comma-separated string of
        references in "ch:verse" format (e.g. "96:2,96:3,96:4" or "3:65").

        Returns:
            dict[str, list[str]]: Mapping from "ch:verse" string key (e.g. "96:2")
            to a list of hadith IDs (e.g. ["bukhari-3", "bukhari-4922", ...]).
        """
        index: dict[str, list[str]] = defaultdict(list)
        for h in self.hadith:
            refs = h.get("quranicReferences")
            if refs:
                for ref in refs.split(","):
                    ref = ref.strip()
                    if ref:
                        index[ref].append(h["id"])
        return dict(index)


def chunks(
    corpus: Corpus,
) -> Generator[tuple[str, str, dict[str, int | str]], None, None]:
    for hadith in corpus.hadith:
        id_ = hadith["id"]
        text = _prepare_hadith_for_embedding(hadith)
        metadata = dict(
            collectionId=hadith["collectionId"],
            hadithNumber=hadith["hadithNumber"],
            bookNum=hadith["bookNum"],
            chapterNumber=hadith["chapterNumber"],
        )
        yield id_, text, metadata


def _build_hadith_index(max_tokens_per_request=max_chunk_length, update_only=False):
    """This function builds an index of the corpus.

    Steps:
    1. Generate chunks from the corpus.
    2. Generate metadata for each chunk (topics, cross-references etc.)
    3. Generate embeddings for each chunk.
    4. Store the chunks and their embeddings in a vector database."""
    corpus = Corpus(_allow_empty=True)
    collection = corpus.hadith_collection
    ids, chunks_, metadata = zip(*chunks(corpus))
    tokens_in_batch = 0
    batch_chunks = []
    batch_ids = []
    batch_metadata = []
    for i in trange(0, len(chunks_), leave=False):
        if update_only:
            if collection.get(ids=[ids[i]])["ids"]:
                # skip if ID already exists
                continue
        tokens_in_batch += len(chunks_[i]) / 4
        if tokens_in_batch < max_chunk_length:
            batch_chunks.append(chunks_[i])
            batch_ids.append(ids[i])
            batch_metadata.append(metadata[i])
            continue
        try:
            embeddings = embed_chunks(batch_chunks)
        except GoogleClientError as e:
            delay = 60
            print(f"Google API error: {e}. Retrying after a delay of 60 seconds.")
            time.sleep(delay)  # wait for the minute to pass
            embeddings = embed_chunks(batch_chunks)
        collection.upsert(
            embeddings=embeddings, ids=batch_ids, metadatas=batch_metadata
        )
        tokens_in_batch = 0
        del batch_chunks[:]
        del batch_metadata[:]
        del batch_ids[:]
