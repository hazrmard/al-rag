"""Functions to load Quran corpus data."""

import requests
import json
import re

from quranai.utils import SingletonMeta

url = "https://api.openquran.com"
intro_url = "/express/chapter/intro/{ch}"
verses_url = "/express/chapter/{ch}:{start}-{end}"
chapters = 114

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


def get_ch(n=1, start=1, end=300) -> dict:
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


def get_all_chapters(start=1, end=chapters + 1) -> list[dict]:
    return [get_ch(n, 1, 300) for n in range(start, end)]


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


def sanitize_topic(s: str):
    return sanitize_verse(",".join(s.split(":")))


def get_topics(q: list[dict]) -> tuple[list[str], dict[str, list[str]]]:
    from collections import defaultdict

    reverse = defaultdict(list, {})
    t = set()
    for ch in q:
        for v in ch["verses"]:
            for topic in v["topics"]:
                t_ = sanitize_topic(topic["topic"])
                t.add(t_)
                reverse[t_].append("%d:%d" % (v["ch"], v["v"]))
    return sorted(list(t)), reverse


class TopicIndex(metaclass=SingletonMeta):
    """This is a singleton class to hold the topic index."""

    def __init__(self, quran: list[dict]):
        self._topics, self._reverse = get_topics(quran)

    def get_references(self, topic: str) -> list[str]:
        return self._reverse.get(topic, [])
