"""What the documentation claims, read conservatively on purpose.

A doc checker loses trust the first time it reports a false positive, so the rules
here are narrow: an environment variable counts when it is backticked or written in
a shell context, and a flag counts when it is written the way a user would type it.
A name that merely looks uppercase is prose, not a claim about the code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt"}

# --flag, not a hyphenated word and not a range like 1--2
FLAG_RE = re.compile(r"(?<![\w-])--([a-z0-9][a-z0-9-]*)")
# backticked token
BACKTICK_RE = re.compile(r"`([^`\n]{1,120})`")
# ENV_STYLE_NAME with at least one underscore, or a well-known bare name
ENV_RE = re.compile(r"(?<!\w)([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?!\w)")
SHELL_CONTEXT_RE = re.compile(r"(?:export\s+$|\bos\.environ\.get\(\s*['\"]|\bgetenv\(\s*['\"])")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
FENCE_RE = re.compile(r"^(```|~~~).*?^\1", re.S | re.M)
# ```console docdrift-ignore ... ```  content is an illustration, never a claim
IGNORE_FENCE_RE = re.compile(r"^(```|~~~)[^\n]*docdrift-ignore[^\n]*\n.*?^\1", re.S | re.M)
# <!-- docdrift: ignore-next-line --> blanks the line after it
IGNORE_NEXT_RE = re.compile(r"<!--\s*docdrift:\s*ignore-next-line\s*-->[^\n]*\n[^\n]*")

# words that are capitalised and underscored but are not variables
ENV_STOPWORDS = {
    "README", "CHANGELOG", "TODO", "FIXME", "NOTE", "WARNING", "USAGE", "MIT",
    "HTTP_200", "HTTP_404", "HTTP_500", "SOC", "SOC_2", "AI_ML", "CI_CD",
}


@dataclass
class DocFacts:
    """name -> (path, line)"""

    env: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    flags: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    symbols: Dict[str, Tuple[str, int]] = field(default_factory=dict)

    def merge(self, other: "DocFacts") -> None:
        for attr in ("env", "flags", "symbols"):
            mine = getattr(self, attr)
            for key, value in getattr(other, attr).items():
                mine.setdefault(key, value)


def _strip_noise(text: str) -> str:
    """Blank out anything that is not a claim, keeping line numbers intact.

    Blanking rather than deleting is deliberate: every reported line number has to
    match the file a human will open.
    """
    def blank(match: "re.Match[str]") -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    text = IGNORE_NEXT_RE.sub(blank, text)
    text = IGNORE_FENCE_RE.sub(blank, text)
    return HTML_COMMENT_RE.sub(blank, text)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def scan_doc(path: Path, *, symbols: bool = False) -> DocFacts:
    raw = path.read_text(encoding="utf-8", errors="replace")
    text = _strip_noise(raw)
    facts = DocFacts()
    name = str(path)

    for match in FLAG_RE.finditer(text):
        facts.flags.setdefault("--" + match.group(1), (name, _line_of(text, match.start())))

    for match in ENV_RE.finditer(text):
        candidate = match.group(1)
        if candidate in ENV_STOPWORDS:
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start:match.start()]
        backticked = prefix.count("`") % 2 == 1 or text[match.end():match.end() + 1] == "`"
        shellish = bool(SHELL_CONTEXT_RE.search(prefix))
        # inside a code fence counts as a claim, since that is where commands live
        fenced = any(f.start() < match.start() < f.end() for f in FENCE_RE.finditer(text))
        if backticked or shellish or fenced:
            facts.env.setdefault(candidate, (name, _line_of(text, match.start())))

    for match in BACKTICK_RE.finditer(text):
        token = match.group(1).strip()
        if token.isupper() and len(token) >= 2 and token not in ENV_STOPWORDS:
            facts.env.setdefault(token, (name, _line_of(text, match.start())))
        elif symbols and _looks_like_symbol(token):
            facts.symbols.setdefault(token.split("(")[0].strip(), (name, _line_of(text, match.start())))

    return facts


def _looks_like_symbol(token: str) -> bool:
    token = token.split("(")[0].strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", token):
        return False
    if token.isupper():
        return False  # that is an env var or a constant, handled above
    return "_" in token or token[:1].isupper()


def iter_doc_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix.lower() in DOC_SUFFIXES:
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in DOC_SUFFIXES:
                    yield child


def scan(paths: Sequence[Path], *, symbols: bool = False) -> DocFacts:
    facts = DocFacts()
    for file_path in iter_doc_files(paths):
        facts.merge(scan_doc(file_path, symbols=symbols))
    return facts
