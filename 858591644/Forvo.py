import base64
import os
import re
import urllib.request
import urllib.parse
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import List, Union
from urllib.error import HTTPError

from aqt import AnkiQt
from bs4 import BeautifulSoup, Tag

from .Exceptions import NoResultsException

search_url = "https://forvo.com/word/"
download_url = "https://forvo.com/download/mp3/"


@dataclass
class Pronunciation:
    language: str
    user: str
    origin: str
    id: int
    votes: int
    download_url: str
    is_ogg: bool
    word: str
    mw: AnkiQt
    audio: Union[str, None] = None

    def download_pronunciation(self):
        """Downloads the pronunciation using the pronunciation url in the pronunciation object, adds the audio to Anki's DB and stores the media id in the pronunciation object."""
        from . import temp_dir
        req = urllib.request.Request(self.download_url)
        dl_path = os.path.join(temp_dir, "pronunciation_" + self.language + "_" + self.word + (
            ".ogg" if self.is_ogg else ".mp3"))
        with open(dl_path, "wb") as f:
            res: HTTPResponse = urllib.request.urlopen(req)
            f.write(res.read())
            res.close()

        media_name = self.mw.col.media.add_file(dl_path)
        self.audio = media_name

    def remove_pronunciation(self):
        """Removes the media file that was priorly downloaded"""
        self.mw.col.media.trash_files([self.audio])
        self.audio = None


class Forvo:
    def __init__(self, word: str, language: str, mw):
        self.html: BeautifulSoup
        self.language = language
        self.word = word.strip()  # trim whitespace
        self.pronunciations: List[Pronunciation] = []
        self.mw = mw

        # Set a user agent so that Forvo/CloudFlare lets us access the page
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36')]
        urllib.request.install_opener(opener)

    def load_search_query(self):
        """Loads the search result page on Forvo"""
        try:
            page = urllib.request.urlopen(url=search_url + urllib.parse.quote_plus(self.word)).read()
        except Exception as e:
            if isinstance(e, HTTPError):
                e: HTTPError
                if e.code == 404:
                    raise NoResultsException()  # Interpret 404 http error code as no results found
            else:
                raise e  # otherwise, raise the exception as usual
        self.html = BeautifulSoup(page, "html.parser")
        return self

    def get_pronunciations(self):
        """Creates pronunciation objects from the soup"""
        available_langs_el = self.html.find_all(id=re.compile(r"language-container-\w{2,4}"))
        available_langs = [re.findall(r"language-container-(\w{2,4})", el.attrs["id"])[0] for el in available_langs_el]
        if self.language not in available_langs:
            raise NoResultsException()
        lang_container = [lang for lang in available_langs_el if
                          re.findall(r"language-container-(\w{2,4})", lang.attrs["id"])[0] == self.language][0]
        pronunciations: Tag = lang_container.find_all(class_="pronunciations")[0].find_all(class_="show-all-pronunciations")[0].find_all("li")

        for pronunciation in pronunciations:
            if len(pronunciation.find_all(class_="more")) == 0:
                continue

            vote_count = pronunciation.find_all(class_="more")[0].find_all(
                class_="main_actions")[0].find_all(
                id=re.compile(r"word_rate_\d+"))[0].find_all(class_="num_votes")[0]

            vote_count_inner_span = vote_count.find_all("span")
            if len(vote_count_inner_span) == 0:
                vote_count = 0
            else:
                vote_count = int(str(re.findall(r"(-?\d+).*", vote_count_inner_span[0].contents[0])[0]))

            pronunciation_dls = re.findall(r"Play\(\d+,'.+','.+',\w+,'([^']+)", pronunciation.find_all(id=re.compile(r"play_\d+"))[0].attrs["onclick"])

            is_ogg = False
            if len(pronunciation_dls) == 0:
                """Fallback to .ogg file"""
                pronunciation_dl = re.findall(r"Play\(\d+,'[^']+','([^']+)", pronunciation.find_all(id=re.compile(r"play_\d+"))[0].attrs["onclick"])[0]
                dl_url = "https://audio00.forvo.com/ogg/" + str(base64.b64decode(pronunciation_dl), "utf-8")
                is_ogg = True
            else:
                pronunciation_dl = pronunciation_dls[0]
                dl_url = "https://audio00.forvo.com/audios/mp3/" + str(base64.b64decode(pronunciation_dl), "utf-8")

            username = pronunciation.find_all(class_="ofLink", recursive=False)
            if len(username) == 0:
                username = re.findall("Pronunciation by(.*)", pronunciation.contents[2], re.S)[0].strip()
            else:
                username = username[0].contents[0]
            self.pronunciations.append(
                Pronunciation(self.language,
                              username,
                              pronunciation.find_all(class_="from")[0].contents[0],
                              int(pronunciation.find_all(class_="more")[0].find_all(class_="main_actions")[0].find_all(
                                  class_="share")[0].attrs["data-id"]),
                              vote_count,
                              dl_url,
                              is_ogg,
                              self.word,
                              self.mw
                              ))

        return self

    def download_pronunciations(self):
        """Downloads all pronunciations that are stored in the Forvo class"""
        for pronunciation in self.pronunciations:
            pronunciation.download_pronunciation()

        return self


    def cleanup(self):
        """Removes any files in the /temp directory."""
        from . import temp_dir
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        return self
