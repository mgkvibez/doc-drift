"""Command line. Exit codes are part of the contract:

0  nothing drifted
1  drift found (docdrift is a check, so this is the useful failure)
2  usage or configuration problem: bad path, nothing to scan, bad flag
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__, code, docs
from .compare import compare
from .report import ENV, FLAG, SYMBOL, Report, summarise, render_json, render_text

EXIT_CLEAN = 0
EXIT_DRIFT = 1
EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docdrift",
        description="Find env vars and CLI flags that documentation mentions but code does not have, and vice versa.",
    )
    parser.add_argument("--version", action="version", version="docdrift %s" % __version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    check = sub.add_parser("check", help="compare docs against source")
    check.add_argument("--docs", action="extend", nargs="+", metavar="PATH", default=None,
                       help="doc file(s) or dir(s); default README.md and docs/")
    check.add_argument("--src", action="extend", nargs="+", metavar="PATH", default=None,
                       help="source file(s) or dir(s); default src/ then .")
    check.add_argument("--ignore", action="extend", nargs="+", metavar="NAME", default=[],
                       help="names to skip, exact or prefix with *")
    check.add_argument("--symbols", action="store_true",
                       help="also check backticked function/class names (heuristic, off by default)")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument("--fail-on", choices=["stale", "any", "none"], default="any",
                       help="which drift fails the build (default: any)")
    return parser


def _default_docs() -> List[Path]:
    candidates = [Path("README.md"), Path("README.rst"), Path("docs")]
    return [p for p in candidates if p.exists()]


def _default_src() -> List[Path]:
    for candidate in (Path("src"), Path(".")):
        if candidate.exists():
            return [candidate]
    return []


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))

    doc_paths = [Path(p) for p in (args.docs or [])] or _default_docs()
    src_paths = [Path(p) for p in (args.src or [])] or _default_src()

    missing = [str(p) for p in doc_paths + src_paths if not p.exists()]
    if missing:
        print("error: path not found: %s" % ", ".join(missing), file=sys.stderr)
        return EXIT_USAGE
    if not doc_paths:
        print("error: no docs found; pass --docs or add a README.md", file=sys.stderr)
        return EXIT_USAGE
    if not src_paths:
        print("error: no source found; pass --src", file=sys.stderr)
        return EXIT_USAGE

    code_facts = code.scan(src_paths)
    doc_facts = docs.scan(doc_paths, symbols=args.symbols)

    subjects = [ENV, FLAG] + ([SYMBOL] if args.symbols else [])
    report = Report(
        docs=[str(p) for p in docs.iter_doc_files(doc_paths)],
        sources=[str(p) for p in code.iter_python_files(src_paths)],
        findings=compare(code_facts, doc_facts, subjects=subjects, ignore=args.ignore),
    )

    print(render_json(report) if args.json else render_text(report))

    if report.ok or args.fail_on == "none":
        return EXIT_CLEAN
    if args.fail_on == "stale" and not report.stale():
        return EXIT_CLEAN
    line = summarise(report)
    if line and not args.json:
        print(line, file=sys.stderr)
    return EXIT_DRIFT


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
