# Make a test download of a chapter to check if the API works and the data is in the expected format.

from quranai.quran.corpus import download_ch

if __name__ == "__main__":
    ch = 1
    data = download_ch(ch)
    print("Download successful")
