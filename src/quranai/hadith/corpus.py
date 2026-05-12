"""Functions to process Hadith corpus.

Schema from API:

```
data: list of dict:
  collectionId: str     # name of the collection (bukhari etc.)
  slug: str
  printPageNum: str
  pdfPageNum: int
  id: str               # primary key (collectionId-hadithNumber)
  hadithNumber: str
  bookName: str
  bookNameTr: str
  bookSlug: str
  bookNum: int
  chapterNumber: int
  chapterName: str
  arabic: str
  narratorIds: list of str
  urduOriginal: str
  urdu: str             # Actual urdu text of hadith
  english: str          # Actual english text of hadith
  tashrih: str
  quranicReferences: str
  linkedQuranicReferences: list of unknown
  reference: str
  hadithReference: str
  theme: str            # Brief natural language summary of hadith.
  linkedHadithIds: list of str      # list of hadithIds relevant to this one
  nextHadithId: str
count: int
pagination:
  page: int
  pageSize: int
  totalPages: int
  total: int
```

"""

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
    with open(path, "r", encoding="utf-8") as f:
        corpus = json.load(f)
        return corpus


def get_local_vector_db() -> ClientAPI:
    path = get_data_file_path(vector_db)
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

    def __init__(self, mode: Literal["local", "remote"] = "local"):
        self.hadith = load_corpus_into_memory()
        if mode == "local":
            self.vector_db = get_local_vector_db()
            self.hadith_collection = get_hadith_collection(self.vector_db)
        elif mode == "remote":
            raise NotImplementedError("Remote mode is not implemented yet")
        else:
            raise ValueError("Invalid mode. Use 'local' or 'remote'.")


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
    corpus = Corpus()
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
