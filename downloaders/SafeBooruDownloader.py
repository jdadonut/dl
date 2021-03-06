from .DefaultDownloader import DefaultDownloader
from .DownloaderOptions import DownloaderOptions
from typing import List, Dict
from urllib.parse import quote
from requests import Session
from bs4 import BeautifulSoup as bs
from pathlib import Path
from os import getcwd
from .download import DownloadableFile
from urllib.request import urlretrieve
from threading import Thread

class SafeBooruDownloader(DefaultDownloader):
    base_uri: str = "https://safebooru.org/"
    http_client: Session = Session()
    base_headers: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko), Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self, tags_str: str, options: DownloaderOptions):
        self.l.log("Entering SafeBooruDownloader.__init__")
        DefaultDownloader.__init__(self, tags_str, options)
        self.doDownload()

    def processTags(self, tags_str: str) -> List[str]:
        self.l.log("Processing tags '" + tags_str + "'")
        tags = tags_str.split(" ")
        for i in range(len(tags)):

            try:
                self.l.log("Testing tag " + tags[i])
                if not self.getPosts(1, [tags[i]]):
                    self.l.log("Bad Tag: " + tags[i])
                    tags.remove(i)
                    i -= 1
            except Exception as e:
                self.l.log(e.__str__() + " ERROR")
                break
        return tags

    def getPosts(self, num: int = None, tags: List[str] = None):
        self.l.log("Getting", num, "posts for tags", str(tags))
        if num is None or tags is None:
            self.l.log("None Value in getPosts")
            return self.getPosts(self.options.numPosts, self.tags)
        posts: List[Dict[str, str]] = []
        iterable = self.postGenerator(tags)
        while len(posts) < num:
            posts.append(next(iterable))

        return posts

    def postGenerator(self, tags: List[str]):
        if tags is None and tags != self.tags:
            self.l.log("postGenerator called with None tags!")
            return self.postGenerator(self.tags)
        postsIterated = 0
        iterable = self.iterLinks(tags)
        if iterable is None:
            self.l.log("Iterable is NONE!")
            raise UnboundLocalError("Iterable is NONE!")
        while True:
            currUrl = next(iterable)
            cPostsIterated = postsIterated
            for post in self.getPostInformationByUri(currUrl):
                postsIterated += 1
                if self.isAllowed(self.parseRating(post["title"])):
                    self.l.log("Yielding image uri: " + self.getImageUriFromPostUri(self.base_uri + post["href"]))
                    yield {"uri": self.getImageUriFromPostUri(self.base_uri + post["href"]), "title": post["id"]}
            if cPostsIterated == postsIterated:
                break

    def iterLinks(self, tags: List[str] = []):
        index = 0
        uri_tags_piece = "+".join([quote(i) for i in tags])
        while True:
            currUri = self.base_uri + "index.php?page=post&s=list&tags=" + uri_tags_piece
            if index == 0:
                yield currUri
            else:
                yield currUri + "&pid=" + str(index)
            index += 40

    def getPostInformationByUri(self, uri: str):
        html = bs(self.get(uri).text, features="html5lib")
        self.l.log("Parsing information from post")
        if len(html.select("#content div h1")) != 0:
            self.l.log("Tag claims invalid, " + html.select("#content div h1")[0].text)
            return []
        for post in html.select("span.thumb[id] a[id][href*=\"s=view\"]"):
            self.l.log("Yielding attributes.")
            yield dict(**post.attrs, **post.select("img")[0].attrs)

    def getImageUriFromPostUri(self, postUri: str):
        html = bs(self.get(postUri).text, features="html5lib")
        # Check if is sample image.
        if "sample" in html.select("#image")[0].attrs["src"]:
            self.l.log("Sample image detected, parsing for better.")
            return html.select("a[href*=\"image\"]")[0].attrs["href"]
        return html.select("#image")[0].attrs["src"]

    def parseRating(self, containingString: str):
        return ""  # Unneeded, self is safebooru.

    def isAllowed(self, ratingString: str):
        return True  # Unneeded, self is safebooru.

    def doDownload(self):
        i = 0
        for post in self.postGenerator(self.tags):
            if not i < self.options.numPosts:
                break
            i+=1
            self.l.log("Downloading", post["title"])
            p = Path(getcwd()).joinpath(self.options.outputDirectory, post["title"][1:] + '.' + post["uri"].split(".")[-1].split("?")[0])
            if not p.parent.exists():
                p.parent.mkdir(parents=True)
            Thread(target=urlretrieve, args=(post["uri"], p)).start()
