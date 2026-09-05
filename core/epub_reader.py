"""Read EPUB navigation ranges without treating storage files as chapters.

Keep the algorithm in sync with mobile/lib/services/epub_reader.dart.
Positions refer to uncleaned text, so anchor cuts cannot lose or repeat text.
"""

import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile
import warnings
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Comment, NavigableString, Tag, XMLParsedAsHTMLWarning


_BACK_TYPES = {"backmatter", "appendix", "endnotes", "footnotes", "bibliography",
               "glossary", "index", "colophon", "afterword", "acknowledgments"}
_BACK_TITLE = re.compile(
    r"^(?:補[註注]|注釈|脚注|巻末注|あとがき|後書き|奥付|著者紹介|訳者紹介|"
    r"参考文献|索引|付録|附録|謝辞|appendix|endnotes|footnotes|bibliography|"
    r"glossary|index|colophon|afterword|acknowledgments)$", re.I)


def _clean(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _resolve(base, href):
    try:
        url = urlsplit(href)
    except ValueError:
        return None
    if url.scheme or url.netloc:
        return None
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(url.path))) if url.path else base
    return path, unquote(url.fragment)


def _local(element):
    return element.tag.rsplit("}", 1)[-1]


def _html(content):
    # EPUB XHTML is intentionally parsed as HTML, matching the mobile DOM.
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        source = content.decode("utf-16")
    elif content.startswith(b"\x00<"):
        source = content.decode("utf-16-be")
    elif content.startswith(b"<\x00"):
        source = content.decode("utf-16-le")
    else:
        source = content.decode("utf-8-sig")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        return BeautifulSoup(source, "lxml")


@dataclass
class _Document:
    path: str
    text: str
    anchors: dict
    extras: dict
    links: list


def _document(path, content):
    soup = _html(content)
    body = soup.body or soup
    parts, anchors, extras, links = [], {}, {}, []
    length = 0

    def walk(node):
        nonlocal length
        if isinstance(node, Comment):
            return
        if isinstance(node, NavigableString):
            value = str(node)
            if value.strip():
                parts.append(value + "\n")
                length += len(value) + 1
            return
        # Ruby annotations are alternate readings, not additional body text.
        if not isinstance(node, Tag) or node.name in ("script", "style", "rt", "rp"):
            return
        for key in ("id", "name"):
            if node.get(key):
                anchors.setdefault(node[key], length)
        label = node.get_text("", strip=True)
        types = set(node.get("epub:type", "").split())
        roles = {x.removeprefix("doc-") for x in node.get("role", "").split()}
        if (types | roles) & _BACK_TYPES:
            heading = node.find(re.compile(r"^h[1-6]$"))
            extras[length] = heading.get_text("", strip=True) if heading else ""
        if re.fullmatch(r"h[1-6]", node.name) and _BACK_TITLE.fullmatch(re.sub(r"\s+", "", label)):
            extras[length] = label
        if node.name == "a" and node.get("href"):
            links.append((node["href"], label))
        for child in node.children:
            walk(child)

    walk(body)
    text = "".join(parts)
    first = _clean(text).split("\n", 1)[0]
    if _BACK_TITLE.fullmatch(re.sub(r"\s+", "", first)):
        extras[0] = first
    return _Document(path, text, anchors, extras, links)


def read_epub_sections(path):
    """Return (title, text) pairs in reading order, including untitled matter."""
    with zipfile.ZipFile(path) as archive:
        container = ET.fromstring(archive.read("META-INF/container.xml"))
        opf_path = next(e.attrib["full-path"] for e in container.iter() if _local(e) == "rootfile")
        package = ET.fromstring(archive.read(opf_path))
        manifest = {e.attrib["id"]: e.attrib for e in package.iter() if _local(e) == "item"}
        spine = next(e for e in package if _local(e) == "spine")
        docs = []
        for ref in spine:
            item = manifest.get(ref.get("idref"), {})
            if item.get("media-type") not in ("application/xhtml+xml", "text/html"):
                continue
            resolved = _resolve(opf_path, item["href"])
            if resolved:
                docs.append(_document(resolved[0], archive.read(resolved[0])))

        # First-level navigation only: nested sections belong to their parent.
        entries, child_targets = [], []
        nav = next((x for x in manifest.values() if "nav" in x.get("properties", "").split()), None)
        nav_target = _resolve(opf_path, nav.get("href", "")) if nav else None
        if nav_target is None or nav_target[0] not in archive.namelist():
            nav = None
        if nav:
            nav_path = nav_target[0]
            soup = _html(archive.read(nav_path))
            toc = next((n for n in soup.find_all("nav") if "toc" in n.get("epub:type", "").split() or n.get("role") == "doc-toc"), None)
            ol = toc.find("ol") if toc else None
            if ol:
                for li in ol.find_all("li", recursive=False):
                    link = li.find("a", href=True)
                    label = li.find(["a", "span"], recursive=False)
                    if link:
                        entries.append((_resolve(nav_path, link["href"]), (label or link).get_text("", strip=True)))
                        child_targets.extend(_resolve(nav_path, a["href"]) for a in li.find_all("a", href=True) if a is not link)
        if not entries:
            ncx = manifest.get(spine.get("toc")) or next((x for x in manifest.values() if x.get("media-type") == "application/x-dtbncx+xml"), None)
            if ncx:
                ncx_target = _resolve(opf_path, ncx.get("href", ""))
                ncx_path = ncx_target[0] if ncx_target else ""
                try:
                    root = ET.fromstring(archive.read(ncx_path))
                except (KeyError, ET.ParseError):
                    root = ET.Element("empty")
                nav_map = next((e for e in root.iter() if _local(e) == "navMap"), [])
                for point in nav_map:
                    if _local(point) != "navPoint":
                        continue
                    content = next((e for e in point.iter() if _local(e) == "content"), None)
                    label = next((e for e in point.iter() if _local(e) == "navLabel"), None)
                    if content is not None:
                        entries.append((_resolve(ncx_path, content.get("src", "")), "".join(label.itertext()).strip() if label is not None else ""))
                        child_targets.extend(_resolve(ncx_path, e.get("src", "")) for e in point.iter() if _local(e) == "content" and e is not content)

        by_path = {d.path: i for i, d in enumerate(docs)}

        def position(target):
            if target is None or target[0] not in by_path:
                return None
            i = by_path[target[0]]
            offset = docs[i].anchors.get(target[1]) if target[1] else 0
            return (i, offset) if offset is not None else None

        boundaries = {}
        missing_anchor_docs = set()
        for target, title in entries:
            pos = position(target)
            if pos is not None:
                boundaries.setdefault(pos, _clean(title))
            elif target is not None and target[0] in by_path:
                missing_anchor_docs.add(by_path[target[0]])
        toc_positions = set(boundaries)
        first = min(boundaries) if boundaries else (len(docs), 0)
        # Resolve failures locally. An unlisted cover must not split every chapter.
        valid_docs = {i for i, _ in toc_positions}
        for i in missing_anchor_docs - valid_docs:
            boundaries[(i, 0)] = ""
        protected = {position(target) for target in child_targets} - toc_positions

        # Explicit guide/landmark information and backmatter links in body TOCs.
        extras = {(i, offset): title for i, d in enumerate(docs) for offset, title in d.extras.items()}
        for i, doc in enumerate(docs):
            for href, title in doc.links:
                if _BACK_TITLE.fullmatch(re.sub(r"\s+", "", title)):
                    pos = position(_resolve(doc.path, href))
                    if pos is not None and (not toc_positions or pos >= first):
                        extras.setdefault(pos, title)
        for ref in package.iter():
            if _local(ref) == "reference" and set(ref.get("type", "").split()) & _BACK_TYPES:
                pos = position(_resolve(opf_path, ref.get("href", "")))
                if pos is not None:
                    extras.setdefault(pos, ref.get("title", ""))
        if nav:
            for landmark in soup.find_all("a", href=True):
                if set(landmark.get("epub:type", "").split()) & _BACK_TYPES:
                    pos = position(_resolve(nav_path, landmark["href"]))
                    if pos is not None:
                        extras.setdefault(pos, landmark.get_text("", strip=True))
        extras = {pos: title for pos, title in extras.items() if pos not in protected}
        for pos, title in extras.items():
            boundaries.setdefault(pos, title)

        in_backmatter = False
        for i, doc in enumerate(docs):
            if (i, 0) in toc_positions:
                in_backmatter = False
            if not toc_positions or (i, 0) < first or in_backmatter:
                boundaries.setdefault((i, 0), "")
            for pos in sorted(p for p in extras.keys() | toc_positions if p[0] == i):
                in_backmatter = pos not in toc_positions

        # A single forward partition guarantees every readable character occurs once.
        result, pieces, title = [], [], ""

        def flush():
            text = _clean("".join(pieces))
            if text:
                first_line = text.split("\n", 1)[0]
                result.append((title or (first_line if len(first_line) <= 80 else f"Chapter {len(result) + 1}"), text))
            pieces.clear()

        for i, doc in enumerate(docs):
            offset = 0
            for pos in sorted(p for p in boundaries if p[0] == i):
                pieces.append(doc.text[offset:pos[1]])
                flush()
                title = boundaries[pos]
                offset = pos[1]
            pieces.append(doc.text[offset:])
        flush()
        return result
