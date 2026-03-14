"""Tools that can be used by an LLM agent to query the Quran corpus.

The Quran corpus is a database with the following structure:

```
# Corpus.quran:
list of dict:               # chapters can be indexed by (chapter number - 1)
  chapter_name: str
  ch: int
  intro_en: str            # English introduction to the chapter
  verses: list of dict:    # list of verses in the chapter
    ch: int
    v: int                 # verse number
    v_: int
    topics: list of dict:
      id: int
      topic: str
      verses: str
    ar: str                 # Arabic text of the verse
    v5: dict:               # This is the translation + footnotes.
      text: str             # English translation of the verse with inline footnote references like [1], [a], etc.
      notes: list of dict:
        ref: str            # reference number in the text, "ref"
        note: str

# Corpus.topics:
list of str:               # sorted list of unique topics in the Quran

# Corpus.references:
dict:                      # mapping of topic to list of verse references in the format "ch:verse"
  topic: list of str
```
"""

import re
from typing import Optional

from quranai.llm import LLM
from quranai.utils import list_data_files, get_data_file_path
from quranai.quran.corpus import Corpus, sanitize_topic, embed_chunks
import yaml


corpus = Corpus()


def get_verses(ch: int, start: int, end: int) -> list[str]:
    """Return a list of verses for a chapter between start and end.

    Verses are typically referenced in the format "ch:verse" or "ch:verse-verse".
    For example, "2:255" refers to chapter 2, verse 255. "2:255-257"
    refers to chapter 2, verses 255 through 257 inclusive.

    Args:
        ch: Chapter number (1-indexed).
        start: Starting verse number (1-indexed).
        end: Ending verse number (1-indexed, inclusive).

    Returns:
        A list of verses from the corpus.
    """
    verses = corpus.quran[ch - 1]["verses"][start - 1 : end]
    return [f"{v['ch']}:{v['v']}: {v['v5']['text']}" for v in verses]


def get_chapter_intro(ch: int) -> str:
    """Return the English introduction for a given chapter.

    Args:
        ch: Chapter number (1-indexed).

    Returns:
        The chapter introduction in English.
    """
    return corpus.quran[ch - 1]["intro_en"]


def get_chapter_intros_by_query(query: str, num_results: int = 5) -> list[dict]:
    """Search for chapter introductions relevant to a query.

    Args:
        query: The query string/keywords to semantically to search for.
        num_results: The number of relevant chapter intros to return.
    Returns:
        A list of chapter numbers, names, and introductions.
    """
    query_embedding = embed_chunks([query], mode="RETRIEVAL_QUERY")[0]
    intros_collection = corpus.chapter_intros_collection
    results = intros_collection.query(
        query_embeddings=[query_embedding], n_results=num_results
    )
    chapters = [int(id.split(":")[0]) for id in results["ids"][0]]  # ids of form "ch"
    intros = []
    for ch in chapters:
        chapter_name = corpus.quran[ch]["chapter_name"]
        intro_en = corpus.quran[ch]["intro_en"]
        intros.append({"ch": ch, "chapter_name": chapter_name, "intro_en": intro_en})
    return intros


def get_verse_footnotes(ch: int, verse: int) -> list[str]:
    """Return the list of footnotes for a specific verse, referenced as `[ref]` in the verse text.
    For example, `[1]`, `[a]`, etc.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).

    Returns:
        A list of footnote strings for the verse.
    """
    notes = corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["notes"]
    return [f"[{n['ref']}]: {n['note']}" for n in notes]


def get_specific_footnote(ch: int, verse: int, ref: str) -> str:
    """Return a specific footnote by reference for a verse, , referenced as `[ref]` in the verse text.
    For example, `[1]`, `[a]`, etc.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).
        ref: Footnote reference identifier as found in the verse text (e.g. '1', 'a').

    Returns:
        A dict with keys 'ref' and 'note'. If not found, note contains a not-found message.
    """
    notes = corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["notes"]
    # strip any surrounding brackets from ref
    ref = ref.strip("[]")
    if ref in notes:
        return f"{ref}: {notes[ref]}"
    return f"{ref}: Footnote [{ref}] not found for {ch}:{verse}."


def get_topics_in_verse(ch: int, start: int, end: int) -> list[str]:
    """Return the list of topics associated with a specific verse.

    Args:
        ch: Chapter number (1-indexed).
        start: Starting verse number (1-indexed).
        end: Ending verse number (1-indexed, inclusive).

    Returns:
        A list of topic strings for the verse.
    """
    topics = []
    for verse in corpus.quran[ch - 1]["verses"][start - 1 : end]:
        topics.extend(verse["topics"])
    return sorted(list(set([sanitize_topic(t["topic"]) for t in topics])))


def get_topics_for_query(query: str, num_results: int = 10) -> list[str]:
    """Search for topics relevant to a query.

    Args:
        query: The query string/keywords to semantically to search for.
        num_results: The number of relevant topics to return.

    Returns:
        A list of topic strings relevant to the query.
    """
    query_embedding = embed_chunks([query], mode="RETRIEVAL_QUERY")[0]
    topics_collection = corpus.topics_collection
    results = topics_collection.query(
        query_embeddings=[query_embedding], n_results=num_results
    )
    ids = results["ids"][0]  # ids of form ch:verse-verse
    return ids


def get_cross_references(ch: int, start: int, end: int) -> list[dict]:
    """Return cross-references for a given verse.

    Args:
        ch: Chapter number (1-indexed).
        start: Starting verse number (1-indexed).
        end: Ending verse number (1-indexed, inclusive).

    Returns:
        A list of cross-reference entries associated with the verse.
    """
    pass


def get_verses_for_query(
    query: str, ch: Optional[int] = None, num_results: int = 3
) -> list[dict]:
    """Search for verses and their commentary that match a query.

    The query string can be natural language.

    Args:
        query: The query string to semantically search for in the corpus.
        ch: The chapter number to search in. By default, searches the entire Quran.
        num_results: The number of results to return. A result is an excerpt of multiple
            verses.


    Returns:
        Excerpts of verses matching the query.
    """
    query_embedding = embed_chunks([query], mode="RETRIEVAL_QUERY")[0]
    verses_collection = corpus.verses_collection
    results = verses_collection.query(
        query_embeddings=[query_embedding],
        n_results=num_results,
        where={"ch": {"$eq": int(ch)}} if ch else None,
    )
    ids = results["ids"][0]  # ids of form ch:verse-verse
    get_verses_args = []
    for id_ in ids:
        ch_str, verses_str = id_.split(":")
        ch_ = int(ch_str)
        if "-" in verses_str:
            start_str, end_str = verses_str.split("-")
            start = int(start_str)
            end = int(end_str)
        else:
            start = int(verses_str)
            end = start
        get_verses_args.append((ch_, start, end))
    verses = []
    for ch_, start, end in get_verses_args:
        verses.extend(get_verses(ch_, start, end))
    return verses


def get_verses_for_topic(topic: str) -> list[str]:
    """Return verses associated with a given topic.

    Args:
        topic: Topic string to match.

    Returns:
        A list of verse strings that include the topic.
    """
    references = corpus.references.get(sanitize_topic(topic), [])  # list of "ch:verse"
    tuples = [(int(r.split(":")[0]), int(r.split(":")[1])) for r in references]
    # return verses in ascending order of chapter and verse
    tuples = sorted(tuples, key=lambda x: (x[0], x[1]))
    verses = []
    for ch, v in tuples:
        verses.extend(get_verses(ch, v, v))
    return verses


def extract_verse_references(text: str) -> list[str]:
    """Extract verse references in the following formats from a given text:

    - "ch:verse" (e.g., "2:255")
    - "ch:verse-verse" (e.g., "2:255-257")
    - "ch:verse,verse" (e.g., "2:255,257")

    Args:
        text: Input text potentially containing verse references.

    Returns:
        A list of verse references in the format "ch:verse".
    """
    pattern = r"(\d+):(\d+(?:-\d+)?(?:,\d+)*)"
    matches = re.findall(pattern, text)
    result = []
    for ch_str, verses_str in matches:
        ch = int(ch_str)
        if "-" in verses_str:
            start, end = verses_str.split("-")
            start = int(start)
            end = int(end)
            for v in range(start, end + 1):
                result.append(f"{ch}:{v}")
        elif "," in verses_str:
            verse_nums = verses_str.split(",")
            for v_str in verse_nums:
                v = int(v_str)
                result.append(f"{ch}:{v}")
        else:
            v = int(verses_str)
            result.append(f"{ch}:{v}")
    return result
