"""Match what the docs claim against what the code does."""

from __future__ import annotations

from fnmatch import fnmatchcase
from typing import Iterable, List, Sequence, Set

from .code import CodeFacts
from .docs import DocFacts
from .report import ENV, FLAG, STALE, SYMBOL, UNDOCUMENTED, Finding

# argparse generates these; nobody documents them per project
BUILTIN_FLAGS = ("-h", "--help", "--version")


def _ignored(name: str, patterns: Sequence[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("*"):
            if name.startswith(pattern[:-1]):
                return True
        elif fnmatchcase(name, pattern) or name == pattern:
            return True
    return False


def _pair(doc_map, code_map, subject: str, ignore: Sequence[str]) -> List[Finding]:
    findings: List[Finding] = []
    for name, (path, line) in sorted(doc_map.items()):
        if _ignored(name, ignore):
            continue
        if name not in code_map:
            findings.append(Finding(kind=STALE, subject=subject, name=name, doc_path=path, doc_line=line))
    for name, (path, line) in sorted(code_map.items()):
        if _ignored(name, ignore):
            continue
        if name not in doc_map:
            findings.append(Finding(kind=UNDOCUMENTED, subject=subject, name=name, code_path=path, code_line=line))
    return findings


def compare(code: CodeFacts, docs: DocFacts, *, subjects: Iterable[str] = (ENV, FLAG),
            ignore: Sequence[str] = ()) -> List[Finding]:
    findings: List[Finding] = []
    for subject in subjects:
        if subject == ENV:
            findings.extend(_pair(docs.env, code.env, ENV, ignore))
        elif subject == FLAG:
            findings.extend(_pair(docs.flags, code.flags, FLAG, tuple(ignore) + BUILTIN_FLAGS))
        elif subject == SYMBOL:
            findings.extend(_pair(docs.symbols, code.symbols, SYMBOL, ignore))
    # stale first: those break the reader right now
    findings.sort(key=lambda f: (f.kind != STALE, f.subject, f.name))
    return findings
