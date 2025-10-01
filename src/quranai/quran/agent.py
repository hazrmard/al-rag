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


def get_verses(ch, start, end) -> dict:
    return corpus.quran[ch - 1]["verses"][start - 1 : end]


def get_chapter_intro(ch) -> dict:
    return corpus.quran[ch - 1]["intro_en"]


def get_verse_footnotes(ch, verse) -> dict:
    return corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["notes"]


def get_specific_footnote(ch, verse, ref) -> dict:
    notes = get_verse_footnotes(ch, verse)
    return {"ref": ref, "note": notes.get(ref, "Footnote not found.")}


def get_topics(ch, verse) -> dict:
    return corpus.quran[ch - 1]["verses"][verse - 1]["topics"]


def get_cross_references(ch, verse) -> dict:
    return corpus.quran[ch - 1]["verses"][verse - 1]["v5"]["cross_references"]


def get_verses_for_query(query: str) -> list[dict]:
    return [v for ch in corpus.quran for v in ch["verses"] if query in v["v5"]["text"]]


def get_verses_for_topic(topic: str) -> list[dict]:
    return [v for ch in corpus.quran for v in ch["verses"] if topic in v["topics"]]


def get_topics_for_query(query: str) -> list[dict]:
    pass


class QuranAgent(BaseAgent):
    def __init__(self, **kwargs):
        prompt = get_data_file_path(_TEMPLATE)
        with prompt.open("r") as f:
            prompt_templates = yaml.safe_load(f)
        super().__init__(tools=[], prompt_templates=prompt_templates, **kwargs)
