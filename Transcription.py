# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
# %reload_ext autoreload
# %autoreload 2

from io import BytesIO
import requests

from dotenv import load_dotenv
from litellm import completion, transcription


load_dotenv(override=True)

# %%
url = 'https://files.alislam.cloud/audio/fs/FSA20240913-UR.mp3'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}
response = requests.get(url, headers=headers)
data = response.content
file = BytesIO(data)

# %%
resp = transcription(model="openai/whisper-1", file=file)

# %%
