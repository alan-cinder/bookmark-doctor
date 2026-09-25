"""Parsing and link-checking logic for Netscape-format bookmark exports."""
from __future__ import annotations

import socket
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Optional

USER_AGENT = "bookmark-doctor/0.1 (+https://github.com/)"


@dataclass(frozen=True)
class Bookmark:
    title: str
    url: str
    add_date: Optional[str]
    folder: str


class _NetscapeBookmarkParser(HTMLParser):
    """Walks the <DL>/<DT>/<H3>/<A> soup that browsers export as "bookmarks.html".

    The format predates HTML5 and is never closed properly (<DT> and <p> have
    no end tags), so folder nesting is tracked through <DL> depth instead of
    trying to validate the markup as a tree.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[Bookmark] = []
        self._folder_stack: list[str] = []
        self._pending_folder: Optional[str] = None
        self._in_h3 = False
        self._in_a = False
        self._current_href: Optional[str] = None
        self._current_add_date: Optional[str] = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "h3":
            self._in_h3 = True
            self._text = []
        elif tag == "a":
            self._in_a = True
            self._text = []
            self._current_href = attrs_dict.get("href")
            self._current_add_date = attrs_dict.get("add_date")
        elif tag == "dl":
            # the <DL> right after a folder's <H3> holds that folder's contents
            self._folder_stack.append(self._pending_folder or "")
            self._pending_folder = None

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3":
            self._in_h3 = False
            self._pending_folder = "".join(self._text).strip()
        elif tag == "a":
            self._in_a = False
            title = "".join(self._text).strip()
            if self._current_href:
                folder = "/".join(part for part in self._folder_stack if part)
                self.entries.append(
                    Bookmark(
                        title=title or self._current_href,
                        url=self._current_href,
                        add_date=self._current_add_date,
                        folder=folder,
                    )
                )
            self._current_href = None
            self._current_add_date = None
        elif tag == "dl":
            if self._folder_stack:
                self._folder_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_h3 or self._in_a:
            self._text.append(data)


def parse_bookmarks(html: str) -> list[Bookmark]:
    parser = _NetscapeBookmarkParser()
    parser.feed(html)
    return parser.entries


def find_duplicates(entries: list[Bookmark]) -> dict[str, list[Bookmark]]:
    by_url: dict[str, list[Bookmark]] = {}
    for entry in entries:
        by_url.setdefault(entry.url, []).append(entry)
    return {url: group for url, group in by_url.items() if len(group) > 1}


def is_ok(status: object) -> bool:
    return isinstance(status, int) and 200 <= status < 400


def _check_one(url: str, timeout: float):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        if exc.code != 405:
            return exc.code
        # some servers reject HEAD outright; fall back to a real GET
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as exc2:
            return exc2.code
        except (urllib.error.URLError, socket.timeout) as exc2:
            return str(getattr(exc2, "reason", exc2))
    except socket.timeout:
        return "timeout"
    except urllib.error.URLError as exc:
        return str(exc.reason)


def check_links(urls: list[str], timeout: float, workers: int) -> dict[str, object]:
    results: dict[str, object] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        future_to_url = {pool.submit(_check_one, url, timeout): url for url in urls}
        for future in as_completed(future_to_url):
            results[future_to_url[future]] = future.result()
    return results
