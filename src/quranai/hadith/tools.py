from quranai.hadith.corpus import Corpus
from quranai.utils import embed_chunks


def get_hadith_by_id(id: str) -> dict:
    """Return a hadith by its ID.

    Args:
        id (str): ID in the form collection-number for e.g. bukhari-1.

    Returns:
        str: The text and theme of the hadith.
    """
    pass


def get_related_hadith(id: str, max_results=3) -> list[dict]:
    pass


def search_hadith_semantically(query: str, max_results=3) -> list[dict]:
    pass
