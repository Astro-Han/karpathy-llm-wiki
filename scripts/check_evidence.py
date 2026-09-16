#!/usr/bin/env python3
"""Mechanical evidence check for a Karpathy-style LLM wiki.

Report-only; never modifies files. Three sweeps:

1. Fidelity — extract candidate literals (specific numbers, ISO dates,
   direct quotes) from each wiki article and verify that each candidate
   appears verbatim in the body of the raw files linked by that
   article's Raw field. Misses are listed as suspects. Derived values,
   product names, and deliberate paraphrases will show up as suspects;
   judging them is the reader's job, not this script's.
2. Evidence errors — articles that cannot be verified at all: a missing
   Raw field on a non-archive article, Raw links that do not resolve,
   or Raw links that escape raw/ (evidence must live in immutable raw/).
3. Inventory — raw files that no article's Raw field references,
   excluding files whose ingest was logged as "no material".

Coverage boundary (closed candidate set, frozen): candidates are
- quotes of 15+ characters (double-quoted spans and body blockquotes)
- ISO dates (YYYY-MM-DD, YYYY-MM)
- specific numbers: thousands-grouped (10,000), dotted (2.1.80, 3.14),
  suffixed (42K, 99.9%), or 4+ digits (2026)
Small plain integers ("42", "500") and exotic forms (signs, currencies,
spelled-out dates) are deliberately not checked; they belong to the
compile-time locate-before-write rule and to judgment review. New prose
forms extend this list in the docstring, not the regexes.

The exit code carries no information; the report is the interface.

Usage: check_evidence.py [project-root] [article.md ...]
Defaults: project-root is the current directory; all wiki/**/*.md
articles except the top-level index.md, log.md, and AGENTS.md are
checked. Article paths may be absolute or relative to the project root.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

NUMBER_TOKEN_RE = re.compile(
    r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?"
    r"|\d+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?)(?![A-Za-z])"
)
SUFFIX_RE = re.compile(r"[KMB%]$")
DATE_RE = re.compile(r"\d{4}-\d{2}(?:-\d{2})?")
QUOTE_RES = [re.compile(r'"([^"\n]*)"'), re.compile(r"“([^”\n]*)”")]
METADATA_RE = re.compile(r"^>\s*(Sources?|Raw|Collected|Published|Updated|Archived):")
STATUS_LINE_RE = re.compile(r"^>\s*\*\*Status:")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
RAW_LINK_RE = re.compile(r"\(([^)]+\.md)[^)]*\)")
NO_MATERIAL_HEADING_RE = re.compile(
    r"^## \[[^\]]*\]\s*ingest\s*\|\s*no material:\s*(\S+)", re.IGNORECASE
)
ARCHIVED_RE = re.compile(r"^>\s*Archived:")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[ \t]*$")
WS_RE = re.compile(r"\s+")

SKIP_FILES = {"index.md", "log.md", "AGENTS.md"}


@dataclass(frozen=True)
class Document:
    title: str | None
    header: tuple[str, ...]
    body: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    kind: str
    value: str


def normalize(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def fence_opener(line: str) -> tuple[str, int] | None:
    m = FENCE_OPEN_RE.match(line)
    if not m:
        return None
    marker, info = m.groups()
    if marker[0] == "`" and "`" in info:
        return None
    return marker[0], len(marker)


def is_fence_closer(line: str, char: str, length: int) -> bool:
    m = FENCE_CLOSE_RE.match(line)
    return bool(m and m.group(1)[0] == char and len(m.group(1)) >= length)


def parse_document(text: str, keep_fences: bool = False) -> Document:
    """Return the visible title, metadata header, and body.

    The metadata header is only the contiguous blockquote immediately
    after the first H1 outside a fence. A fence is a body boundary; its
    removal must not promote a later blockquote into the header. Article
    candidates skip fenced blocks (commands and output are not prose
    claims); raw evidence keeps them, because a raw's fenced source text
    is exactly the evidence it exists to hold.
    """
    title = None
    header = []
    preamble = []
    body = []
    state = "before_title"
    fence_char = None
    fence_len = 0

    for line in text.splitlines():
        if fence_char:
            if is_fence_closer(line, fence_char, fence_len):
                fence_char = None
            if keep_fences and state == "body":
                body.append(line)
            continue
        opener = fence_opener(line)
        if opener:
            fence_char, fence_len = opener
            if state == "after_title":
                state = "body"
            if keep_fences and state == "body":
                body.append(line)
            continue
        if state == "before_title":
            if line.startswith("# "):
                title = line
                state = "after_title"
            else:
                preamble.append(line)
        elif state == "after_title":
            if not line.strip():
                continue
            if line.strip().startswith(">"):
                header.append(line)
                state = "header"
            else:
                body.append(line)
                state = "body"
        elif state == "header":
            if line.strip().startswith(">"):
                header.append(line)
            else:
                body.append(line)
                state = "body"
        else:
            body.append(line)

    return Document(title, tuple(header), tuple(preamble + body))


def strip_fences(text: str) -> str:
    """Remove Standard Markdown fenced code blocks."""
    out = []
    fence_char = None
    fence_len = 0
    for line in text.splitlines():
        if fence_char:
            if is_fence_closer(line, fence_char, fence_len):
                fence_char = None
            continue
        opener = fence_opener(line)
        if opener:
            fence_char, fence_len = opener
            continue
        out.append(line)
    return "\n".join(out)


def strip_noise(text: str) -> str:
    text = INLINE_CODE_RE.sub(" ", text)
    text = LINK_RE.sub(r"\1", text)
    return text


def keep_number(token: str) -> bool:
    token = token.strip()
    if SUFFIX_RE.search(token) or "," in token or "." in token:
        return True
    return len(token) >= 4


def extract_numeric_date_candidates(line: str) -> list[Candidate]:
    line = strip_noise(line)
    date_matches = list(DATE_RE.finditer(line))
    candidates = [Candidate("date", m.group(0)) for m in date_matches]
    number_text = list(line)
    for match in date_matches:
        number_text[match.start() : match.end()] = " " * (match.end() - match.start())
    candidates.extend(
        Candidate("number", m.group(0))
        for m in NUMBER_TOKEN_RE.finditer("".join(number_text))
        if keep_number(m.group(0))
    )
    return candidates


def extract_candidates(text: str) -> list[Candidate]:
    document = parse_document(text)
    lines = ([document.title] if document.title else []) + [
        line for line in document.header if not METADATA_RE.match(line.strip())
    ] + list(document.body)
    candidates: list[Candidate] = []
    skip_status_block = False
    blockquote: list[str] = []
    paragraph: list[str] = []

    def flush_blockquote():
        if blockquote:
            joined = normalize(" ".join(blockquote))
            if len(joined) >= 15:
                candidates.append(Candidate("quote", joined))
            blockquote.clear()

    def flush_paragraph():
        if paragraph:
            joined = normalize(" ".join(paragraph))
            for quote_re in QUOTE_RES:
                candidates.extend(
                    Candidate("quote", m.group(1))
                    for m in quote_re.finditer(joined)
                    if len(m.group(1).strip()) >= 15
                )
            paragraph.clear()

    for line in lines:
        stripped = line.strip()
        if STATUS_LINE_RE.match(stripped):
            flush_blockquote()
            flush_paragraph()
            skip_status_block = True
            continue
        if skip_status_block:
            if stripped.startswith(">"):
                continue
            skip_status_block = False
        if stripped.startswith(">"):
            flush_paragraph()
            content = strip_noise(stripped.lstrip(">").strip())
            blockquote.append(content)
            candidates.extend(extract_numeric_date_candidates(content))
            continue
        flush_blockquote()
        if not stripped:
            flush_paragraph()
            continue
        line = strip_noise(line)
        candidates.extend(extract_numeric_date_candidates(line))
        paragraph.append(line)
    flush_blockquote()
    flush_paragraph()
    seen = set()
    unique = []
    for candidate in candidates:
        value = candidate.value.strip().strip(".,;:()[]")
        candidate = Candidate(candidate.kind, value)
        if value and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def raw_links_of(article_text: str) -> list[str]:
    """Raw links come only from the metadata header; identical lines in
    the body or in code fences are content, not fields."""
    links = []
    for line in parse_document(article_text).header:
        if re.match(r"^>\s*Raw:", line.strip()):
            links.extend(RAW_LINK_RE.findall(line))
    return links


def contains(haystack: str, candidate: Candidate) -> bool:
    if candidate.kind == "quote":
        return candidate.value in haystack
    # Values must stand on their own, while sentence punctuation remains
    # valid. A month may not pass as the prefix of a full ISO date.
    right = r"(?!-\d{2})" if candidate.kind == "date" and len(candidate.value) == 7 else ""
    pattern = (
        r"(?<![\d.,])" + re.escape(candidate.value) + right + r"(?![A-Za-z0-9]|[.,]\d|%)"
    )
    return re.search(pattern, haystack) is not None


def source_content(path: Path) -> str:
    """Raw file body with the metadata header removed, fenced source text
    included. Collection metadata (Source/Collected/Published) is
    bookkeeping, not evidence; letting it match candidates would
    false-pass dates and years. But a raw's fenced blocks are source
    content (journal lines, config, output), so they are evidence."""
    document = parse_document(path.read_text(encoding="utf-8"), keep_fences=True)
    return normalize("\n".join(document.body))


def check_article(article: Path, root: Path) -> tuple[list[str], list[str]]:
    """Return (fidelity suspects, evidence errors) for one article."""
    text = article.read_text(encoding="utf-8")
    links = raw_links_of(text)
    if not links:
        if any(ARCHIVED_RE.match(line.strip()) for line in parse_document(text).header):
            return [], []
        return [], ["article has no Raw field"]
    raw_root = (root / "raw").resolve()
    raws = []
    errors = []
    for link in links:
        target = (article.parent / link).resolve()
        if not target.is_relative_to(raw_root):
            errors.append(f"Raw link escapes raw/: {link}")
        elif not target.is_file():
            errors.append(f"unresolvable Raw link: {link}")
        else:
            raws.append(source_content(target))
    misses = []
    if raws:
        for candidate in extract_candidates(text):
            candidate = Candidate(candidate.kind, normalize(candidate.value))
            if not any(contains(raw, candidate) for raw in raws):
                misses.append(candidate.value)
    return misses, errors


def iter_articles(wiki_dir: Path):
    for path in sorted(wiki_dir.rglob("*.md")):
        if path.relative_to(wiki_dir).as_posix() not in SKIP_FILES:
            yield path


def no_material_paths(log_file: Path) -> set[str]:
    if not log_file.is_file():
        return set()
    paths = set()
    text = strip_fences(log_file.read_text(encoding="utf-8"))
    for line in text.splitlines():
        m = NO_MATERIAL_HEADING_RE.match(line)
        if m:
            paths.add(m.group(1).strip("`,;."))
    return paths


def referenced_raws(root: Path) -> set[Path]:
    referenced = set()
    for article in iter_articles(root / "wiki"):
        for link in raw_links_of(article.read_text(encoding="utf-8")):
            target = (article.parent / link).resolve()
            referenced.add(target)
    return referenced


def unreferenced_raws(root: Path) -> list[str]:
    raw_dir = root / "raw"
    if not raw_dir.is_dir():
        return []
    referenced = referenced_raws(root)
    disposed = no_material_paths(root / "wiki" / "log.md")
    missing = []
    for path in sorted(raw_dir.rglob("*.md")):
        if path.resolve() not in referenced and path.relative_to(root).as_posix() not in disposed:
            missing.append(path.relative_to(root).as_posix())
    return missing


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    wiki_dir = root / "wiki"
    if not wiki_dir.is_dir():
        print(f"no wiki/ directory under {root}")
        return 1

    articles = []
    for arg in argv[2:]:
        path = Path(arg)
        if not path.is_absolute():
            path = root / path
        try:
            if path.resolve().relative_to(wiki_dir).as_posix() in SKIP_FILES:
                print(f"warning: {arg} is an index/log file, skipping", file=sys.stderr)
                continue
        except ValueError:
            pass
        if not path.is_file():
            print(f"warning: article not found: {arg}", file=sys.stderr)
            continue
        articles.append(path)
    if len(argv) <= 2:
        articles = list(iter_articles(wiki_dir))

    results = {}
    for article in articles:
        results[article] = check_article(article, root)

    def label(article: Path) -> Path:
        try:
            return article.resolve().relative_to(root)
        except ValueError:
            return article

    print("# Evidence check\n")
    print("## Fidelity suspects")
    suspect_count = 0
    for article, (misses, _) in results.items():
        if misses:
            print(f"\n{label(article)}")
            for miss in misses:
                print(f"- {miss}")
                suspect_count += 1
    if suspect_count == 0:
        print("\n(none)")

    print("\n## Evidence errors")
    error_count = 0
    for article, (_, errors) in results.items():
        if errors:
            print(f"\n{label(article)}")
            for error in errors:
                print(f"- {error}")
                error_count += 1
    if error_count == 0:
        print("(none)")

    print("\n## Unreferenced raw files")
    orphans = unreferenced_raws(root)
    for path in orphans:
        print(f"- {path}")
    if not orphans:
        print("(none)")

    print(
        f"\n## Summary\n{suspect_count} fidelity suspect(s), "
        f"{error_count} evidence error(s), {len(orphans)} unreferenced raw file(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
