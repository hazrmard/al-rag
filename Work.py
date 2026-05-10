# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: quranai (3.13.12)
#     language: python
#     name: python3
# ---

# %%
# %reload_ext autoreload
# %autoreload 2
import os
import re
from pathlib import Path
import requests
import json
from tqdm.autonotebook import trange, tqdm
from dotenv import load_dotenv

import quranai
from quranai.utils import schema, list_data_files, get_data_file_path
from quranai.quran.corpus import corpus_json

load_dotenv("./.env", override=True);

# %% [markdown]
# # Quran

# %% [markdown] jp-MarkdownHeadingCollapsed=true
# ## Download

# %%
from quranai.quran.corpus import download_ch
from quranai.utils import schema

ch1 = download_ch(1)
print(schema(ch1))

# %%
quran = {}
for i in trange(1, 115, leave=False):
    quran[i] = download_ch(i)

# %%
with open(get_data_file_path(corpus_json), "w") as f:
    json.dump(quran, f)

# %% [markdown] jp-MarkdownHeadingCollapsed=true
# ## Parsing

# %%
from quranai.quran.corpus import (
    sanitize_topic,
    sanitize_verse,
    load_corpus_into_memory,
    get_referenced_verses_in_corpus,
)

# %%
quran = load_corpus_into_memory()

# %%
print(schema(quran))

# %%
from quranai.quran.corpus import get_topics

t, r = get_topics(quran)

# %%
print(schema(quran[0]["verses"][4]))

# %%
quran[0]["verses"][4]

# %%
verses = get_referenced_verses_in_corpus()

# %%
messages = [
    dict(
        role="system",
        content=(
            "You are an assistant expert in retrieving verses in context from "
            "the Quran based on user query. You find excerpts that convey an idea. The "
            "excerpts should be relevant to the query and provide a comprehensive understanding "
            "of the topic at hand. Here is the entire Quran in `chapter:verse translation` format. "
            " IMPORTANT: Only return references in chapter:verse or chapter:verse-verse format. "
            " For example: `2:255,1:1-5`:\n\n"
            "<Quran>\n"
            + "\n".join(f"{ref} {text}" for ref, text in tuple(verses.items())[:3150])
            + "\n\n</Quran>\n\n"
        ),
    ),
    dict(
        role="user",
        content=("Mercy and forgiveness"),
    ),
]

# %%
token_counter(messages=messages)

# %% [markdown]
# ### DB

# %% [markdown]
# #### Verses

# %%
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

chroma_client = chromadb.PersistentClient()
collection = chroma_client.get_or_create_collection(name="quran")

# %%
embed_fn = DefaultEmbeddingFunction()
for c in trange(1, 115, leave=False):
    ch = get_verses(quran[c])
    meta = get_metadata(quran[c])

    embed_strs = []
    for (i, v), (j, m) in zip(ch.items(), meta.items()):
        assert i == j
        embed_str = f"{v}\n\nTOPICS:\n\n{m['topics']}"
        embed_strs.append(embed_str)
    embeddings = embed_fn(embed_strs)

    collection.upsert(
        ids=["%d:%d" % (c, i) for i in ch.keys()],
        embeddings=embeddings,
        documents=list(ch.values()),
        metadatas=list(meta.values()),
    )

# %%
r = collection.query(
    query_texts="actions of the people that disobeyed God", n_results=5
)

# %%
r["metadatas"][0][0]

# %%
collection.get("53:53")

# %% [markdown]
# #### Topics

# %%
import chromadb

chroma_client = chromadb.PersistentClient()
topics_collection = chroma_client.get_or_create_collection(name="quran_topics")


# %%
# Prompt --vectorDB--> topic --table lookup--> verses
# Prompt --vectorDB--> verses

# %%
def topic_metadata_to_database(topics, collection):
    collection.upsert(ids=topics, documents=topics)


topics, reverse_topics = get_topics(quran)
topic_metadata_to_database(topics, topics_collection)

# %%
r = c["quran_topics"].query(query_texts="repentence, forgiveness", n_results=10)

# %%
r["documents"][0]

# %% [markdown]
# ### Querying

# %%
from framework import get_collections, find, themes

c = get_collections()

# %%
print(themes("forgiveness", c["quran_topics"]))

# %%
print(find("What is forgiveness?", c["quran"]))

# %% [markdown]
# ## Tools

# %%
from quranai.quran import tools, corpus

tools.search_verses_semantically("god")

# %%
col = corpus.Corpus().topics_collection

# %%
emb = corpus.embed_chunks(["attributes of allah"], mode="RETRIEVAL_QUERY")

# %%
import numpy as np

col.query(np.asarray(emb))

# %%
col.count()

# %% [markdown]
# # Hadith

# %% [markdown]
# ## Download

# %%
from quranai.utils import schema
import requests
import json

HADITH_API_BASE = "https://api.readhadith.app/ahadith/"


# %%
def download_page(page: int = 1) -> dict:
    url = HADITH_API_BASE + "?page={page}"
    try:
        response = requests.get(url.format(page=page))
        content = response.content
        data = json.loads(content)
    except Exception as exc:
        raise exc
    return data


# %%
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.autonotebook import tqdm


def download_all_pages() -> list:
    pg1 = download_page(1)
    hadiths = [*pg1["data"]]
    # total_pages = pg1["pagination"]["totalPages"]
    total_pages = 5
    concurrency = 16
    with ThreadPoolExecutor(concurrency) as pool:
        futures = [pool.submit(download_page, pg) for pg in range(2, total_pages + 1)]
        for future in tqdm(as_completed(futures), total=total_pages - 1, leave=False):
            hadiths.extend(future.result()["data"])
    return hadiths


# %%
pages = download_all_pages()

# %%
from quranai.hadith.corpus import load_corpus_into_memory

hadith = load_corpus_into_memory()

# %%
from quranai.hadith.corpus import _prepare_hadith_for_embedding

print(_prepare_hadith_for_embedding(hadith[0]))

# %%
from quranai.utils import count_tokens
from quranai.hadith.corpus import chunks, Corpus

ids, chunks_, metadata = zip(*chunks(Corpus()))

tokens = map(count_tokens, chunks_)

# %%
for i, t in enumerate(chunks_):
    print(i, count_tokens(t), t.split("\n")[0])
    if i >= 4:
        break

# %%
for i, t in enumerate(tokens):
    print(i, t)
    if i > 12:
        break
