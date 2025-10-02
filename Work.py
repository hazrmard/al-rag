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
#     display_name: quranai
#     language: python
#     name: python3
# ---

# %%
# %reload_ext autoreload
# %autoreload 2
import os
import re
from pathlib import Path
import requests, json
# import numpy as np
# from litellm import embedding, completion, completion_cost
import json
from tqdm.autonotebook import trange, tqdm
from dotenv import load_dotenv

import quranai
from quranai.utils import schema, list_data_files, get_data_file_path
from quranai.quran.corpus import corpus_json

load_dotenv("./.env", override=True);

# %% [markdown] jp-MarkdownHeadingCollapsed=true
# ## Download

# %%
from quranai.quran.corpus import download_ch
from quranai.utils import schema

ch1 = download_ch(1)
print(schema(ch1))

# %%
quran = {}
for i in range(1, 115):
    quran[i] = get_ch(i)

# %%
with open(get_data_file_path(corpus_json), "w") as f:
    json.dump(corpus_json, f)

# %% [markdown]
# ## Parsing

# %%
from quranai.quran.corpus import sanitize_topic, sanitize_verse, load_corpus_into_memory

# %%
with open(get_data_file_path(corpus_json), "r") as f:
    data = json.load(f)
quran = [v for k, v in data.items()]

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
def get_metadata(ch: dict) -> dict[int, dict[str, str]]:
    m = {}
    for d in ch["verses"]:
        m_ = dict(
            ch=d["ch"],
            v=d["v"],
            topics="\n".join(sanitize_topic(t["topic"]) for t in d["topics"]),
            notes="\n".join(n["note"] for n in d["v5"]["notes"]),
        )
        m[d["v"]] = m_
    return m


# %%
get_metadata(quran[1])

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
# ## LLM

# %%
from quranai.agent import Agent
from quranai.quran.agent import QuranAgent
import cProfile, pstats, io, os

os.getenv("OPENAI_MODEL_NAME")

# %%
agent = Agent(tools=[])

# %%
qagent = QuranAgent()

# %%
with cProfile.Profile() as pr:
    qagent.run("What themes are present in 1:1-7?")
s = io.StringIO()
sortby = pstats.SortKey.CUMULATIVE
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())
