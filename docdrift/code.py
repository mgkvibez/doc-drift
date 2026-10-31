"""What the code actually has, read with ast rather than regex.

Grep over source finds names in comments, in dead strings, and in the tests of a
library you forgot to delete. Parsing means a variable inside a comment is not a
variable, and a renamed function is really renamed.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__",
             ".mypy_cache", ".pytest_cache", ".ruff_cache", "site-packages"}


@dataclass
class CodeFacts:
    """Where each thing lives, so a finding can point at a line."""

    env: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    flags: Dict[str, Tuple[str, int]] = field(default_factory=dict)
    symbols: Dict[str, Tuple[str, int]] = field(default_factory=dict)

    def merge(self, other: "CodeFacts") -> None:
        for attr in ("env", "flags", "symbols"):
            mine = getattr(self, attr)
            for key, value in getattr(other, attr).items():
                mine.setdefault(key, value)


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.facts = CodeFacts()

    # os.environ["X"], os.environ.get("X"), os.getenv("X")
    def _env_name(self, node: ast.AST) -> Optional[str]:
        if isinstance(node, ast.Subscript):
            target = node.value
            if isinstance(target, ast.Attribute) and target.attr == "environ":
                key = node.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    return key.value
        return None

    def visit_Subscript(self, node: ast.Subscript) -> None:
        name = self._env_name(node)
        if name:
            self.facts.env.setdefault(name, (self.path, getattr(node, "lineno", 0)))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        # os.environ.get("X") / os.getenv("X")
        if isinstance(func, ast.Attribute) and func.attr in ("get", "getenv"):
            owner = func.value
            is_environ = (
                (isinstance(owner, ast.Attribute) and owner.attr == "environ")
                or (isinstance(owner, ast.Name) and owner.id == "os" and func.attr == "getenv")
            )
            if is_environ and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    self.facts.env.setdefault(first.value, (self.path, node.lineno))
        # argparse: add_argument("--flag") / add_argument("-f", "--flag")
        if isinstance(func, ast.Attribute) and func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    value = arg.value
                    if value.startswith("-") and len(value) > 1:
                        self.facts.flags.setdefault(value, (self.path, node.lineno))
        self.generic_visit(node)

    def _define(self, node) -> None:
        name = getattr(node, "name", None)
        if name and not name.startswith("_"):
            self.facts.symbols.setdefault(name, (self.path, node.lineno))
        self.generic_visit(node)

    visit_FunctionDef = _define
    visit_AsyncFunctionDef = _define
    visit_ClassDef = _define


def scan_file(path: Path) -> CodeFacts:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError:
        return CodeFacts()  # a file we cannot parse contributes nothing, and says nothing
    visitor = _Visitor(str(path))
    visitor.visit(tree)
    return visitor.facts


def iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*.py")):
                if not SKIP_DIRS.intersection(child.parts):
                    yield child


def scan(paths: Sequence[Path]) -> CodeFacts:
    facts = CodeFacts()
    for file_path in iter_python_files(paths):
        facts.merge(scan_file(file_path))
    return facts
