"""An agent implementing tools to query the Quran corpus.

The corpus is available as a dict with the following structure:

```
list of dict:
  chapter_name: str
  ch: int
  intro_en: str
  verses: list of dict:
    ch: int
    v: int
    v_: int
    topics: list of dict:
      id: int
      topic: str
      verses: str
    ar: str                 # Arabic text of the verse
    v5: dict:               # This is the translation + commentary
      text: str
      notes: list of dict:
        ref: str
        note: str
```
"""

from quranai.agent import Agent as BaseAgent
from quranai.utils import list_data_files, get_data_file_path
import yaml


_TEMPLATE = "prompt_quran.yaml"


def get_verses(ch, start, end) -> dict:
    pass


def get_chapter_intro(ch) -> dict:
    pass


def get_verse_commentary(ch, verse) -> dict:
    pass


def get_topics(ch, verse) -> dict:
    pass


def get_cross_references(ch, verse) -> dict:
    pass


def get_verses_for_query(query: str) -> list[dict]:
    pass


def get_verses_for_topic(topic: str) -> list[dict]:
    pass


def get_topics_for_query(query: str) -> list[dict]:
    pass


class QuranAgent(BaseAgent):
    def __init__(self, **kwargs):
        prompt = get_data_file_path(_TEMPLATE)
        with prompt.open("r") as f:
            prompt_templates = yaml.safe_load(f)
        super().__init__(tools=[], prompt_templates=prompt_templates, **kwargs)
