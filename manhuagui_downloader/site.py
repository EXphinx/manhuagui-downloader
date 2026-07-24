from __future__ import annotations

import html as html_module
import json
import re
import threading
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .lzstring import LZStringError, decompress_from_base64
from .models import Book, Chapter


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

SITE_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,en;q=0.5",
    "Cookie": "country=CN; isAdult=1",
}

IMAGE_HOSTS = ("eu", "eu1", "eu2", "us", "us1", "us2", "us3", "i")


class ManhuaGuiError(RuntimeError):
    pass


class AntiRobotRequired(ManhuaGuiError):
    def __init__(self, url: str, message: str | None = None) -> None:
        super().__init__(
            message
            or "漫画站点要求完成人机验证。请在验证窗口完成操作后重试。"
        )
        self.url = url


class _BookHTMLParser(HTMLParser):
    def __init__(self, book_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.book_id = book_id
        self.title_parts: list[str] = []
        self._in_h1 = False
        self._chapter_depth = 0
        self._anchor: dict[str, str] | None = None
        self.chapter_rows: list[tuple[str, str]] = []
        self.viewstate: str | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = set(attrs.get("class", "").split())
        if tag == "h1":
            self._in_h1 = True
        if tag == "input" and attrs.get("id") == "__VIEWSTATE":
            self.viewstate = attrs.get("value")

        if tag == "div" and "chapter-list" in classes:
            self._chapter_depth = 1
        elif self._chapter_depth and tag == "div":
            self._chapter_depth += 1

        if self._chapter_depth and tag == "a":
            href = attrs.get("href", "")
            if re.search(rf"/comic/{re.escape(self.book_id)}/\d+\.html$", href):
                self._anchor = {
                    "href": href,
                    "title": attrs.get("title", ""),
                    "text": "",
                }

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        if tag == "a" and self._anchor is not None:
            title = _normalize_text(self._anchor["title"] or self._anchor["text"])
            if title:
                self.chapter_rows.append((self._anchor["href"], title))
            self._anchor = None
        if tag == "div" and self._chapter_depth:
            self._chapter_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.title_parts.append(data)
        if self._anchor is not None:
            self._anchor["text"] += data


class _ChapterFragmentParser(HTMLParser):
    def __init__(self, book_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.book_id = book_id
        self._anchor: dict[str, str] | None = None
        self.rows: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs = {key: value or "" for key, value in attrs_list}
        href = attrs.get("href", "")
        if re.search(rf"(?:^|/)comic/{re.escape(self.book_id)}/\d+\.html$", href):
            self._anchor = {
                "href": href,
                "title": attrs.get("title", ""),
                "text": "",
            }

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor is not None:
            title = _normalize_text(self._anchor["title"] or self._anchor["text"])
            if title:
                self.rows.append((self._anchor["href"], title))
            self._anchor = None

    def handle_data(self, data: str) -> None:
        if self._anchor is not None:
            self._anchor["text"] += data


_PACKED_COMPRESSED_RE = re.compile(
    r"function\(p,a,c,k,e,d\).*?\}\("
    r"'(?P<source>.*?)',(?P<radix>\d+),(?P<count>\d+),"
    r"'(?P<dictionary>.*?)'"
    r"\['\\x73\\x70\\x6c\\x69\\x63'\]\('\\x7c'\)",
    re.S,
)

_PACKED_PLAIN_RE = re.compile(
    r"function\(p,a,c,k,e,d\).*?\}\("
    r"'(?P<source>.*?)',(?P<radix>\d+),(?P<count>\d+),"
    r"'(?P<dictionary>.*?)'\.(?:split|splic)\('\|'\)",
    re.S,
)

_PAYLOAD_RE = re.compile(
    r"SMH\.(?:imgData|reader)\((?P<payload>\{.*\})\)\.(?:preInit|init)\(\);?",
    re.S,
)

_JS_ESCAPE_RE = re.compile(
    r"\\(?:x(?P<hex>[0-9a-fA-F]{2})|u(?P<unicode>[0-9a-fA-F]{4})|(?P<char>['\"\\/bfnrt]))"
)


def _normalize_text(value: str) -> str:
    return " ".join(html_module.unescape(value or "").split())


def normalize_book_url(value: str) -> tuple[str, str]:
    candidate = value.strip()
    if not candidate:
        raise ManhuaGuiError("链接不能为空")
    if "://" not in candidate:
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if host != "manhuagui.com" and not host.endswith(".manhuagui.com"):
        raise ManhuaGuiError("仅支持 manhuagui.com 的漫画链接")
    match = re.search(r"/comic/(\d+)(?:/|$)", parsed.path)
    if not match:
        raise ManhuaGuiError("链接中没有找到漫画 ID，应类似 /comic/1325/")
    book_id = match.group(1)
    return book_id, f"https://www.manhuagui.com/comic/{book_id}/"


def _decode_js_string(value: str) -> str:
    replacements = {
        "'": "'",
        '"': '"',
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }

    def replace(match: re.Match[str]) -> str:
        if match.group("hex"):
            return chr(int(match.group("hex"), 16))
        if match.group("unicode"):
            return chr(int(match.group("unicode"), 16))
        return replacements[match.group("char")]

    return _JS_ESCAPE_RE.sub(replace, value)


def _encode_unpack_token(index: int, radix: int) -> str:
    if index == 0:
        return "0"
    if not 2 <= radix <= 62:
        raise ManhuaGuiError(f"阅读页使用了不支持的编码基数: {radix}")
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    token = ""
    while index:
        index, remainder = divmod(index, radix)
        token = (chr(remainder + 29) if remainder > 35 else digits[remainder]) + token
    return token


def _unpack_reader_script(html_text: str) -> str:
    matches: list[tuple[re.Match[str], bool]] = [
        *((match, True) for match in _PACKED_COMPRESSED_RE.finditer(html_text)),
        *((match, False) for match in _PACKED_PLAIN_RE.finditer(html_text)),
    ]
    for match, compressed in matches:
        source = _decode_js_string(match.group("source"))
        dictionary_text = _decode_js_string(match.group("dictionary"))
        if compressed:
            try:
                dictionary_text = decompress_from_base64(dictionary_text)
            except LZStringError as exc:
                raise ManhuaGuiError("阅读页的压缩字典无法解析") from exc
        dictionary = dictionary_text.split("|")
        radix = int(match.group("radix"))
        count = int(match.group("count"))
        for index in range(count - 1, -1, -1):
            if index < len(dictionary) and dictionary[index]:
                token = _encode_unpack_token(index, radix)
                source = re.sub(r"\b" + re.escape(token) + r"\b", dictionary[index], source)
        if _PAYLOAD_RE.search(source):
            return source
    raise ManhuaGuiError("阅读页中没有找到图片数据，站点格式可能已经变化")


def parse_reader_image_urls(html_text: str, image_host: str = "eu") -> list[str]:
    unpacked = _unpack_reader_script(html_text)
    match = _PAYLOAD_RE.search(unpacked)
    if not match:
        raise ManhuaGuiError("阅读页图片数据解析失败")
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError as exc:
        raise ManhuaGuiError("阅读页图片数据不是有效 JSON") from exc

    files = payload.get("files")
    path = payload.get("path")
    signatures = payload.get("sl")
    declared_length = payload.get("len")
    if not isinstance(files, list) or not files:
        raise ManhuaGuiError("阅读页没有图片列表")
    if not isinstance(path, str) or not path.startswith("/"):
        raise ManhuaGuiError("阅读页图片路径无效")
    if not isinstance(signatures, dict):
        raise ManhuaGuiError("阅读页缺少图片签名")
    if declared_length != len(files):
        raise ManhuaGuiError(
            f"阅读页图片数量不一致: 声明 {declared_length!r}，实际 {len(files)}"
        )
    if image_host not in IMAGE_HOSTS:
        raise ManhuaGuiError(f"未知图片节点: {image_host}")
    query = urlencode(signatures)
    suffix = f"?{query}" if query else ""
    return [
        f"https://{image_host}.hamreus.com{path}{str(filename).strip()}{suffix}"
        for filename in files
    ]


class ManhuaGuiClient:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._cookie_header = SITE_HEADERS["Cookie"]
        self._cookie_lock = threading.Lock()

    def set_cookie_header(self, value: str) -> None:
        cookies: dict[str, str] = {"country": "CN", "isAdult": "1"}
        for part in value.split(";"):
            key, separator, cookie_value = part.strip().partition("=")
            if separator and key:
                cookies[key] = cookie_value
        with self._cookie_lock:
            self._cookie_header = "; ".join(
                f"{key}={cookie_value}" for key, cookie_value in cookies.items()
            )

    @staticmethod
    def _looks_like_challenge(html_text: str) -> bool:
        sample = html_text[:120_000].lower()
        markers = (
            "<title>just a moment",
            "cf-chl-",
            "challenge-platform",
            "人机验证",
            "验证码",
            "验证您是真人",
            "security check",
        )
        return any(marker in sample for marker in markers)

    def _get_text(self, url: str, *, referer: str | None = None) -> str:
        headers = dict(SITE_HEADERS)
        with self._cookie_lock:
            headers["Cookie"] = self._cookie_header
        if referer:
            headers["Referer"] = referer
        request = Request(url, headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                html_text = response.read().decode(charset, errors="replace")
                if self._looks_like_challenge(html_text):
                    raise AntiRobotRequired(url)
                return html_text
        except HTTPError as exc:
            if exc.code in {403, 429, 503}:
                raise AntiRobotRequired(url) from exc
            raise ManhuaGuiError(f"请求失败（HTTP {exc.code}）: {url}") from exc
        except URLError as exc:
            raise ManhuaGuiError(f"无法连接漫画站点: {exc.reason}") from exc

    def fetch_book(self, input_url: str) -> Book:
        book_id, book_url = normalize_book_url(input_url)
        html_text = self._get_text(book_url, referer="https://www.manhuagui.com/")
        parser = _BookHTMLParser(book_id)
        parser.feed(html_text)

        rows = parser.chapter_rows
        if not rows and parser.viewstate:
            try:
                fragment = decompress_from_base64(parser.viewstate)
            except LZStringError as exc:
                raise ManhuaGuiError("章节列表无法解压") from exc
            fragment_parser = _ChapterFragmentParser(book_id)
            fragment_parser.feed(fragment)
            rows = fragment_parser.rows

        if not rows:
            raise ManhuaGuiError("没有找到章节，漫画可能受地区限制或站点格式已经变化")

        title = _normalize_text("".join(parser.title_parts))
        if not title:
            title_match = re.search(r"<title>(.*?)</title>", html_text, re.S | re.I)
            title = _normalize_text(title_match.group(1).split("漫画", 1)[0]) if title_match else book_id

        unique_rows: list[tuple[str, str]] = []
        seen: set[str] = set()
        for href, chapter_title in rows:
            id_match = re.search(r"/(\d+)\.html$", href)
            if not id_match or id_match.group(1) in seen:
                continue
            seen.add(id_match.group(1))
            unique_rows.append((href, chapter_title))

        # ManhuaGui normally renders newest first. The interactive list uses
        # reading order so ranges such as 1-10 mean the first ten chapters.
        unique_rows.reverse()
        chapters = tuple(
            Chapter(
                index=index,
                chapter_id=re.search(r"/(\d+)\.html$", href).group(1),  # type: ignore[union-attr]
                title=chapter_title,
                url=f"https://www.manhuagui.com/comic/{book_id}/"
                f"{re.search(r'/(\d+)\.html$', href).group(1)}.html",  # type: ignore[union-attr]
            )
            for index, (href, chapter_title) in enumerate(unique_rows, start=1)
        )
        return Book(book_id=book_id, title=title, url=book_url, chapters=chapters)

    def fetch_chapter_images(self, chapter: Chapter, book_url: str) -> list[str]:
        html_text = self._get_text(chapter.url, referer=book_url)
        return parse_reader_image_urls(html_text)
