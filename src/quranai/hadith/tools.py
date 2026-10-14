"""Tools that can be used by an LLM agent to query the Hadith corpus."""

from typing import Optional

from quranai.hadith.corpus import Corpus
from quranai.utils import embed_chunks

corpus = Corpus()


def _format_hadith(hadith: dict) -> dict:
    """Format a raw hadith record from `hadith.json` for LLM tool output.

    Handles fallback from missing English translation (`english` is empty string
    in ~88% of records) to Arabic text prefixed with `[Arabic text]:`, while
    always including the English `theme` summary.

    Returns:
        dict: Standardized card containing:
            - id (str): Hadith ID in "{collectionId}-{hadithNumber}" format (e.g. "bukhari-1").
            - collection (str): Collection name (e.g. "bukhari", "sahih-muslim").
            - hadith_number (str): Number within collection.
            - book_name (str): Arabic book title (e.g. "كتاب بدء الوحى").
            - chapter_name (str): Chapter heading if present.
            - theme (str): Natural language summary in English.
            - text (str): English translation if available, else Arabic text.
            - arabic (str): Original Arabic narration.
            - linked_hadiths (list[str]): Related Hadith IDs from `linkedHadithIds`.
            - quranic_references (str): Comma-separated verse references (e.g. "96:2,96:3").
    """
    english_text = (hadith.get("english") or "").strip()
    arabic_text = (hadith.get("arabic") or "").strip()
    if english_text:
        text = english_text
    elif arabic_text:
        text = f"[Arabic text]: {arabic_text}"
    else:
        text = ""

    return {
        "id": hadith["id"],
        "collection": hadith.get("collectionId", ""),
        "hadith_number": hadith.get("hadithNumber", ""),
        "book_name": hadith.get("bookName", ""),
        "chapter_name": hadith.get("chapterName", ""),
        "theme": hadith.get("theme", ""),
        "text": text,
        "arabic": arabic_text,
        "linked_hadiths": hadith.get("linkedHadithIds", []),
        "quranic_references": hadith.get("quranicReferences", ""),
    }


def get_hadith_by_id(id: str) -> dict:
    """Return a hadith by its ID.

    Hadiths are referenced by collection and number, e.g. "bukhari-1" or "sahih-muslim-224".

    Args:
        id: Hadith identifier in the format collection-number (e.g. "bukhari-1").

    Returns:
        A dictionary containing the hadith's ID, collection, theme, text, Arabic text,
        and cross-references. Returns an error message if not found.
    """
    clean_id = id.strip().strip("[]").lower()
    hadith = corpus.by_id.get(clean_id)
    if not hadith:
        return {"error": f"Hadith '{id}' not found in the corpus."}
    return _format_hadith(hadith)


def search_hadith_semantically(query: str, num_results: int = 5) -> list[dict]:
    """Search for hadiths semantically matching a conceptual query or topic.

    The query should describe the topic, moral lesson, or narration content (e.g.
    "sincerity in actions", "respect for parents", "rules of trade").

    Args:
        query: The search phrase or topic to semantically match.
        num_results: Maximum number of relevant hadiths to return (default: 5).

    Returns:
        A list of matching hadith dictionaries with their ID, collection, theme, text,
        and distance score.
    """
    query_embedding = embed_chunks([query], mode="RETRIEVAL_QUERY")[0]
    results = corpus.hadith_collection.query(
        query_embeddings=[query_embedding],
        n_results=num_results,
    )
    ids = results["ids"][0] if results.get("ids") else []
    distances = results["distances"][0] if results.get("distances") else []

    matches = []
    for hadith_id, dist in zip(ids, distances):
        raw = corpus.by_id.get(hadith_id)
        if raw:
            card = _format_hadith(raw)
            card["distance"] = round(dist, 4)
            matches.append(card)
    return matches


def get_linked_hadith(id: str, num_results: int = 3) -> list[dict]:
    """Get other hadiths linked to or thematic variants of a given hadith ID.

    Args:
        id: Hadith identifier in the format collection-number (e.g. "bukhari-1").
        num_results: Maximum number of related hadiths to return (default: 3).

    Returns:
        A list of related hadith dictionaries.
    """
    clean_id = id.strip().strip("[]").lower()
    hadith = corpus.by_id.get(clean_id)
    if not hadith:
        return [{"error": f"Hadith '{id}' not found in the corpus."}]
    linked_ids = hadith.get("linkedHadithIds", [])[:num_results]
    results = []
    for lid in linked_ids:
        raw = corpus.by_id.get(lid)
        if raw:
            results.append(_format_hadith(raw))
        else:
            results.append({"id": lid, "error": f"Linked hadith '{lid}' not found in local corpus."})
    return results


get_related_hadith = get_linked_hadith


def get_hadith_for_verse(ch: int, verse: int, num_results: int = 5) -> list[dict]:
    """Get hadiths citing or commenting on a specific Quranic verse.

    Args:
        ch: The chapter number (1-indexed).
        verse: The verse number (1-indexed).
        num_results: Maximum number of hadiths to return (default: 5).

    Returns:
        A list of hadith dictionaries citing or associated with the specified verse.
    """
    verse_key = f"{int(ch)}:{int(verse)}"
    hadith_ids = corpus.by_verse.get(verse_key, [])
    seen = set()
    unique_ids = []
    for hid in hadith_ids:
        if hid not in seen:
            seen.add(hid)
            unique_ids.append(hid)
    results = []
    for hid in unique_ids[:num_results]:
        raw = corpus.by_id.get(hid)
        if raw:
            results.append(_format_hadith(raw))
    return results
