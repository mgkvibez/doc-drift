"""Findings and their rendering.

Two kinds of drift, in both directions: docs that mention something the code no
longer has, and code that nothing in the docs mentions. The first breaks whoever
follows the instructions, the second hides a feature from them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

STALE = "stale"          # docs mention it, code does not have it
UNDOCUMENTED = "undocumented"  # code has it, docs do not mention it

ENV = "env"
FLAG = "flag"
SYMBOL = "symbol"


@dataclass(frozen=True)
class Finding:
    kind: str            # STALE | UNDOCUMENTED
    subject: str         # ENV | FLAG | SYMBOL
    name: str
    doc_path: str = ""
    doc_line: int = 0
    code_path: str = ""
    code_line: int = 0

    @property
    def label(self) -> str:
        return "%s-%s" % (self.kind, self.subject)

    def as_dict(self) -> Dict[str, object]:
        data = {"kind": self.kind, "subject": self.subject, "name": self.name}
        if self.doc_path:
            data["doc"] = {"path": self.doc_path, "line": self.doc_line}
        if self.code_path:
            data["code"] = {"path": self.code_path, "line": self.code_line}
        return data


@dataclass
class Report:
    docs: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)

    def stale(self) -> List[Finding]:
        return [f for f in self.findings if f.kind == STALE]

    def undocumented(self) -> List[Finding]:
        return [f for f in self.findings if f.kind == UNDOCUMENTED]

    @property
    def ok(self) -> bool:
        return not self.findings

    def counts(self) -> Dict[str, int]:
        return {"stale": len(self.stale()), "undocumented": len(self.undocumented())}


_ADVICE = {
    (STALE, ENV): "the docs promise it and the code never reads it: rename the doc, or read the variable",
    (STALE, FLAG): "the docs document a flag the parser does not define, so following them fails",
    (STALE, SYMBOL): "the docs name something no longer defined, so the example will not run",
    (UNDOCUMENTED, ENV): "the code reads a variable nobody is told to set",
    (UNDOCUMENTED, FLAG): "the flag exists and no one can find it",
    (UNDOCUMENTED, SYMBOL): "public surface with no mention anywhere",
}


def render_text(report: Report) -> str:
    if report.ok:
        return "no issues found by docdrift v%s across %d doc(s) and %d source file(s)" % (
            _version(), len(report.docs), len(report.sources))

    lines = []
    for group, title in ((STALE, "Docs that are wrong now"), (UNDOCUMENTED, "Code nobody is told about")):
        items = [f for f in report.findings if f.kind == group]
        if not items:
            continue
        lines.append(title)
        for f in items:
            where = "%s:%d" % (f.doc_path, f.doc_line) if f.doc_path else "%s:%d" % (f.code_path, f.code_line)
            lines.append("  %-14s %-28s %s" % (f.label, f.name, where))
            advice = _ADVICE.get((f.kind, f.subject))
            if advice:
                lines.append("  %-14s %s" % ("", advice))
        lines.append("")

    c = report.counts()
    lines.append("%d stale in docs, %d missing from docs (%d docs, %d source files)" % (
        c["stale"], c["undocumented"], len(report.docs), len(report.sources)))
    return "\n".join(lines).rstrip()


def render_json(report: Report) -> str:
    return json.dumps({
        "tool": "docdrift",
        "version": _version(),
        "docs": report.docs,
        "sources": report.sources,
        "counts": report.counts(),
        "findings": [f.as_dict() for f in report.findings],
    }, indent=2)


def _version() -> str:
    from . import __version__
    return __version__


def summarise(report: Report) -> Optional[str]:
    """One line for CI logs, or None when clean."""
    if report.ok:
        return None
    c = report.counts()
    return "docdrift: %d stale reference(s), %d undocumented item(s)" % (c["stale"], c["undocumented"])
