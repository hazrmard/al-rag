"""
API Schema:

```
data: list of dict:
  collectionId: str     # name of the collection (bukhari etc.)
  slug: str
  printPageNum: str
  pdfPageNum: int
  id: str               # primary key (collectionId-hadithNumber)
  hadithNumber: str
  bookName: str
  bookNameTr: str
  bookSlug: str
  bookNum: int
  chapterNumber: int
  chapterName: str
  arabic: str
  narratorIds: list of str
  urduOriginal: str
  urdu: str             # Actual urdu text of hadith
  english: str          # Actual english text of hadith
  tashrih: str
  quranicReferences: str
  linkedQuranicReferences: list of unknown
  reference: str
  hadithReference: str
  theme: str            # Brief natural language summary of hadith.
  linkedHadithIds: list of str      # list of hadithIds relevant to this one
  nextHadithId: str
count: int
pagination:
  page: int
  pageSize: int
  totalPages: int
  total: int
```

"""

import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm.autonotebook import tqdm

HADITH_API_BASE = "https://api.readhadith.app/ahadith/"


def download_page(page: int = 1) -> dict:
    url = HADITH_API_BASE + "?page={page}"
    try:
        response = requests.get(url.format(page=page))
        content = response.content
        data = json.loads(content)
    except Exception as exc:
        raise exc
    return data


def download_all_pages() -> list:
    pages = [download_page(1)]
    total_pages = pages[0]["pagination"]["totalPages"]
    concurrency = 16
    with ThreadPoolExecutor(concurrency) as pool:
        futures = [pool.submit(download_page, pg) for pg in range(2, total_pages + 1)]
        for future in tqdm(as_completed(futures), total=total_pages - 1, leave=False):
            pages.append(future.result())
    return pages
