# doc-drift

**Find the docs that lie.** `docdrift` reports the environment variables and CLI flags your documentation promises that the code no longer has, and the ones the code has that nobody documented.

[![ci](https://github.com/mgkvibez/doc-drift/actions/workflows/ci.yml/badge.svg)](https://github.com/mgkvibez/doc-drift/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

```console docdrift-ignore
$ docdrift check
Docs that are wrong now
  stale-env      LEGACY_TOKEN                 README.md:41
                 the docs promise it and the code never reads it: rename the doc, or read the variable

Code nobody is told about
  undocumented-flag  --secret-mode            src/cli.py:22
                     the flag exists and no one can find it

1 stale in docs, 1 missing from docs (3 docs, 11 source files)
```

## Why this exists

Docs drift in a specific, boring way: someone renames a variable or deletes a flag, the code stays green, and the README keeps instructing people to use something that no longer exists. Nothing catches it, because tests exercise code and nothing exercises prose.

<!-- docdrift: ignore-next-line -->
The usual version of this tool greps. Grep lies in both directions: it finds `DATABASE_URL` inside a comment or a deleted branch, and it misses a name that appears with different spacing. `docdrift` reads the source with `ast`, so a variable inside a comment is not a variable, and a renamed function is really renamed.

## Install

```bash
pipx install doc-drift-py
```

The distribution is `doc-drift-py` because PyPI refused `doc-drift` as too similar to an
existing project. The command stays `docdrift`: nothing you type changes.

## Use

```bash
docdrift check                          # README.md + docs/ against src/ (or .)
docdrift check --docs docs --src app    # explicit paths
docdrift check --fail-on stale          # only fail on docs that are wrong, not gaps
docdrift check --symbols                # also check backticked function/class names
docdrift check --json                   # machine-readable
docdrift check --ignore LEGACY_*        # skip a name, exact or prefix
```

Exit codes are the contract:

| code | meaning |
|---|---|
| 0 | nothing drifted |
| 1 | drift found (the useful failure) |
| 2 | usage or configuration problem: bad path, no docs, no source |

In CI:

```yaml docdrift-ignore
- name: Docs tell the truth
  run: pipx run --spec git+https://github.com/mgkvibez/doc-drift.git docdrift check --fail-on stale
```

## What counts as a claim

Precision matters more than coverage here, because a checker that cries wolf gets deleted. So a documentation mention only counts when it is written the way a user would read it:

<!-- docdrift: ignore-next-line -->
- an environment variable in backticks, after `export`, inside `os.environ.get(...)`, or anywhere inside a fenced code block
<!-- docdrift: ignore-next-line -->
- a `--flag` written as a flag, not a hyphenated word and not a version range like `1.0--2.0`

Plain uppercase prose is ignored on purpose: `This speaks HTTP and JSON over TCP` is not a claim about your environment.

<!-- docdrift: ignore-next-line -->
On the code side, only real reads count: `os.environ["X"]`, `os.environ.get("X")`, `os.getenv("X")`, `argparse.add_argument("--flag")`. Files that fail to parse are skipped silently and cannot create findings.

## Suppressing a false positive

Some docs legitimately discuss names they do not promise: a migration guide, an example of another tool's command, a paragraph about how the check works. Two markers handle that, and both keep line numbers honest by blanking rather than deleting.

<!-- docdrift: ignore-next-line -->
- `<!-- docdrift: ignore-next-line -->` blanks the line that follows it
- a fence tagged `docdrift-ignore` (` ```console docdrift-ignore `) is treated as an illustration, never as a claim

argparse's own `-h`, `--help` and `--version` are excluded automatically, because no project documents those.

## What it deliberately does not do

- **Not every framework.** Flags are read from `argparse`. Click, Typer and docopt are not parsed yet, and a project using them will report its flags as undocumented. That is a known gap, not a silent one.
- **Not every language.** Source scanning is Python only. Markdown, RST and plain text docs are read.
<!-- docdrift: ignore-next-line -->
- **A flag in an example may not be yours.** `gh run view --log-failed` in your README is a flag of `gh`, not of your project, and it will be reported. Use `--ignore` or tag that fence `docdrift-ignore`. Found by running this on its own sibling project.
- **Not a prose checker.** It says a name is missing, not that a sentence is wrong.
- **Symbols are opt-in.** Backticked `function_name` references are heuristic, so they are behind `--symbols` and off by default.

## Dogfooding

This repo runs `docdrift` on itself in the gate, so the README above cannot quietly drift from the code that ships it.

## License

MIT
