# Changelog

## v0.1.0 - 2026-10-31

- First release. `docdrift check` compares documentation claims against source in
  both directions: stale (`docs mention it, code does not have it`) and undocumented
  (`code has it, docs do not mention it`).
- Source facts come from `ast`, not grep, so names in comments and dead strings are
  not counted, and unparseable files cannot invent findings.
- Checks environment variables and `argparse` flags by default; backticked symbol
  references are opt-in behind `--symbols`.
- Exit codes: 0 clean, 1 drift, 2 usage. `--fail-on stale|any|none` decides what
  fails a build.
- Zero runtime dependencies. Python 3.9+.
