# Changelog

## v0.1.1 - 2026-10-31

- Distribution renamed to `doc-drift-py`. PyPI rejected `doc-drift` as too similar to an
  existing project, and the distribution name must equal the PyPI project name exactly
  or the upload fails with a 403. The `docdrift` command and the import are unchanged.
- `scripts/verify.sh` gained a check that the name in `pyproject.toml` equals the name
  the README tells people to install, because this rename broke nothing in the suite
  and would have shipped a README pointing at a package that does not exist.


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
