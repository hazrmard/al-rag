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
from quranai.quran.corpus import (
    sanitize_topic,
    sanitize_verse,
    load_corpus_into_memory,
    get_referenced_verses_in_corpus,
)
from litellm import token_counter

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
# ## LLM

# %%
from quranai.agent import Agent
from quranai.quran.agent import QuranAgent, _TEMPLATE
from quranai.llm import LLM, tool_annotator
import cProfile, pstats, io, os

print(os.getenv("OPENAI_MODEL_NAME"), _TEMPLATE)

# %%
from typing import Literal


def calculator(
    x: float, y: float, op: Literal["add", "subtract", "multiply", "divide"]
) -> float | str:
    """Performs basic arithmetic operations.

    Args:
        x (float): The first operand.
        y (float): The second operand.
        op (str): The operation to perform.

    Returns:
        float: The result of the arithmetic operation.
    """
    x, y = float(x), float(y)
    if op == "add":
        return x + y
    elif op == "subtract":
        return x - y
    elif op == "multiply":
        return x * y
    elif op == "divide":
        return x / y
    else:
        return f"Unknown operation: {op}"


# %%
# llm = LLM(model_name="gpt-4.1-nano")
resp = llm.complete(messages, max_tokens=100)

# %%
print(llm.llm_responses(resp)[0]["content"])

# %%
from quranai.quran.agent import get_verses

get_verses(4, 62, 63)

# %%
resp.usage

# %%
llm = LLM(tools=(calculator,))
llm.run_once("What is 10.765 times 100.5?")

# %%
from pprint import pprint

pprint(tool_annotator(calculator)["function"])

# %%
agent = Agent(tools=[])

# %%
qagent = QuranAgent()

# %%
with cProfile.Profile() as pr:
    res = qagent.run("What does 1:1 say?", max_steps=3, return_full_result=True)
s = io.StringIO()
sortby = pstats.SortKey.CUMULATIVE
ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
ps.print_stats()
print(s.getvalue())

# %%
len(res.steps)

# %%
res.steps
