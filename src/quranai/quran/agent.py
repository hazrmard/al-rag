"""An agent implementing tools to query the Quran corpus.

The corpus is a database with the following structure:

```
# Corpus.quran:
list of dict:               # chapters can be indexed by chapter number - 1
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
dict:                      # mapping of topic to list of references in the format "ch:verse"
  topic: list of str
```
"""

from quranai.agent import Agent as BaseAgent
from quranai.utils import list_data_files, get_data_file_path
from quranai.quran.corpus import Corpus
import yaml


_TEMPLATE = "prompt_quran.yaml"
corpus = Corpus()


def get_verses(ch: int, start: int, end: int) -> list[dict]:
    """Return a list of verses for a chapter between start and
    end (inclusive of start, exclusive of end). Does not include
    any footnotes or topics. Only the arabic text and translation.

    Args:
        ch: Chapter number (1-indexed).
        start: Starting verse number (1-indexed).
        end: Ending verse number (1-indexed, exclusive).

    Returns:
        A list of verse dictionaries from the corpus slice.
    """
    verses = corpus.quran[ch - 1]["verses"][start - 1 : end]
    return [
        {
            "ch": v["ch"],
            "v": v["v"],
            "ar": v["ar"],
            "v5": v["v5"],
        }
        for v in verses
    ]


def get_chapter_intro(ch: int) -> str:
    """Return the English introduction for a given chapter.

    Args:
        ch: Chapter number (1-indexed).

    Returns:
        The chapter introduction in English.
    """
    return corpus.quran[ch - 1]["intro_en"]


def get_verse_footnotes(ch: int, verse: int) -> list[dict]:
    """Return the list of footnotes for a specific verse.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).

    Returns:
        A list of footnote dictionaries for the verse.
    """
    return corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["notes"]


def get_specific_footnote(ch: int, verse: int, ref: str) -> dict:
    """Return a specific footnote by reference for a verse.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).
        ref: Footnote reference identifier as found in the verse text (e.g. '1', 'a').

    Returns:
        A dict with keys 'ref' and 'note'. If not found, note contains a not-found message.
    """
    notes = get_verse_footnotes(ch, verse)
    for n in notes:
        if n.get("ref") == ref:
            return n
    return {"ref": ref, "note": "Footnote not found."}


def get_topics(ch: int, verse: int) -> list[dict]:
    """Return the list of topics associated with a specific verse.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).

    Returns:
        A list of topic dictionaries for the verse.
    """
    return corpus.quran[ch - 1]["verses"][verse - 1]["topics"]


def get_cross_references(ch: int, verse: int) -> list[dict]:
    """Return cross-references for a given verse.

    Args:
        ch: Chapter number (1-indexed).
        verse: Verse number (1-indexed).

    Returns:
        A list of cross-reference entries associated with the verse.
    """
    return corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["cross_references"]


def get_verses_for_query(query: str) -> list[dict]:
    """Return verses whose translation text contains a query substring.

    Args:
        query: Substring to search for in verse translations.

    Returns:
        A list of verse dicts that match the query.
    """
    return [v for ch in corpus.quran for v in ch["verses"] if query in v["v5"]["text"]]


def get_verses_for_topic(topic: str) -> list[dict]:
    """Return verses associated with a given topic.

    Args:
        topic: Topic string to match.

    Returns:
        A list of verse dicts that include the topic.
    """
    return [v for ch in corpus.quran for v in ch["verses"] if topic in v["topics"]]


def get_topics_for_query(query: str) -> list[dict]:
    """Return topics relevant to a query.

    This tool is intended to map a free-text query to topics found in the corpus.

    Args:
        query: Free-text query string.

    Returns:
        A list of topic dictionaries relevant to the query. Each dict contains at least the
        'topic' key.
    """
    # Match topics by simple substring match on the corpus topics list.
    return [{"topic": t} for t in getattr(corpus, "topics", []) if query in t]


class QuranAgent(BaseAgent):
    def __init__(self, **kwargs) -> None:
        """Initialize the QuranAgent with tool bindings and prompt templates.

        Args:
            **kwargs: Passed through to the BaseAgent initializer.
        """
        prompt = get_data_file_path(_TEMPLATE)
        with prompt.open("r") as f:
            prompt_templates = yaml.safe_load(f)
        super().__init__(
            tools=list(
                map(
                    self.__class__.tool,
                    [
                        get_verses,
                        get_chapter_intro,
                        get_verse_footnotes,
                        get_specific_footnote,
                        get_topics,
                        get_cross_references,
                        get_verses_for_query,
                        get_verses_for_topic,
                        # get_topics_for_query,
                    ],
                ),
            ),
            prompt_templates=prompt_templates,
            **kwargs,
        )


if __name__ == "__main__":
    agent = QuranAgent()
    from smolagents import GradioUI

    GradioUI(agent).launch()
