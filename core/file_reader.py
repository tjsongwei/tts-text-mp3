"""txt/epub ファイルの読み込みとチャプター抽出"""

import re
from dataclasses import dataclass

import chardet


@dataclass
class Chapter:
    index: int
    title: str
    text: str


def sanitize_filename(name: str, max_len: int = 60) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip(" ._")
    if not name:
        name = "untitled"
    return name[:max_len]


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_text_file(path: str) -> list[Chapter]:
    with open(path, "rb") as f:
        raw = f.read()
    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"
    if encoding.lower() in ("shift_jis", "windows-1252"):
        for enc in ("utf-8", "cp932", encoding):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            text = raw.decode(encoding, errors="replace")
    else:
        try:
            text = raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            text = raw.decode("utf-8", errors="replace")

    title = path.replace("\\", "/").rsplit("/", 1)[-1]
    title = title.rsplit(".", 1)[0]
    return [Chapter(index=1, title=title, text=_clean_text(text))]


def _html_to_text(html_content: bytes | str) -> str:
    from bs4 import BeautifulSoup

    if isinstance(html_content, bytes):
        html_content = html_content.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html_content, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return _clean_text(soup.get_text("\n"))


def read_epub_file(path: str) -> list[Chapter]:
    from ebooklib import epub, ITEM_DOCUMENT

    book = epub.read_epub(path)
    chapters: list[Chapter] = []
    idx = 0
    spine_ids = [item_id for item_id, _linear in book.spine]
    for item_id in spine_ids:
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ITEM_DOCUMENT:
            continue
        text = _html_to_text(item.get_content())
        if len(text.strip()) < 50:
            continue
        idx += 1
        title = getattr(item, "title", None)
        if not title:
            first_line = text.split("\n", 1)[0].strip()
            title = first_line if 0 < len(first_line) <= 80 else f"Chapter {idx}"
        chapters.append(Chapter(index=idx, title=title, text=text))
    return chapters


def load_chapters(path: str) -> list[Chapter]:
    lower = path.lower()
    if lower.endswith(".epub"):
        chapters = read_epub_file(path)
    elif lower.endswith(".txt"):
        chapters = read_text_file(path)
    else:
        raise ValueError(f"未対応のファイル形式です: {path}")
    if not chapters:
        raise ValueError(f"テキストが見つかりませんでした: {path}")
    return chapters
