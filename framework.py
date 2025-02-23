from pathlib import Path
import re
import os
from dotenv import load_dotenv
import chromadb

load_dotenv(override=False)

filepath = Path(__file__).parent.resolve()
chromapath = (filepath / os.environ["CHROMA_PATH"]).resolve()

assert chromapath.exists(), "%s does not exist" % chromapath

system_prompt = f"""\
You are a scholarly assistant, with expertise in objectively analyzing historical and religious texts.
The texts are comprised of chapters and verses. You are to look up excerpts of verses from the Quran 
and related themes. The excerpts are tagged with themes which you may examine. Your job is to use the 
excerpts, and only the excerpts, to answer a user's question. The user may ask follow-up questions.
"""


def get_collections() -> dict[str, chromadb.Collection]:
    chroma_client = chromadb.PersistentClient(path=chromapath)
    collections = {"quran": None, "quran_topics": None}
    for cname in collections.keys():
        collection = chroma_client.get_or_create_collection(name=cname)
        collections[cname] = collection
    return collections


def find(question: str, collection: chromadb.Collection, n=10) -> list[str]:
    res = collection.query(query_texts=question, n_results=n)
    res_strs = [
        "%s:%s" % (res["ids"][0][i], res["documents"][0][i])
        for i in range(len(res["ids"][0]))
    ]
    context = list(set(res_strs))
    return context


def themes(question: str, collection: chromadb.Collection, n=10) -> list[str]:
    res = collection.query(query_texts=question, n_results=n)
    themes = res["documents"][0]
    context = list(sorted(set(themes)))
    return context


def _process_answer(ans: str, collection: chromadb.Collection) -> str:
    pattern = r"(\d+:\d+)"
    matches = re.findall(pattern=pattern, string=ans)
    vdata = collection.get(ids=list(set(matches)))
    res = "\n\n".join(
        "[%s]: %s" % (loc, verse)
        for loc, verse in zip(vdata["ids"], vdata["documents"])
    )
    return ans + (("\n\nReferences:\n\n" + res) if len(res) else "")
