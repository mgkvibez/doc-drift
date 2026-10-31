#!/usr/bin/env bash
# Local gate. CI runs this same script, so the two are independent checks of the
# same contract rather than two different opinions.
set -u
fail() { echo "GATE FAILED: $1"; exit 1; }

echo "== check 1/5: editable install"
python3 -m pip install -q -e ".[dev]" || fail "install"

echo "== check 2/5: version consistency (pyproject vs module)"
pyver=$(python3 -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
modver=$(python3 -c "import docdrift;print(docdrift.__version__)")
[ "$pyver" = "$modver" ] || fail "pyproject $pyver != module $modver"
echo "version $pyver consistent"

echo "== check 3/5: test suite"
python3 -m pytest -q || fail "tests"

echo "== check 4/5: CLI contract on real fixtures (0 clean, 1 drift, 2 usage)"
tmpd=$(mktemp -d)
mkdir -p "$tmpd/src"
printf 'Set `DATABASE_URL`.\n' > "$tmpd/README.md"
printf 'import os\nK = os.environ["DATABASE_URL"]\n' > "$tmpd/src/app.py"
( cd "$tmpd" && python3 -m docdrift.cli check >/dev/null 2>&1 ); code=$?
[ "$code" = "0" ] || fail "clean project should exit 0, got $code"
printf 'Set `DATABASE_URL` and `LEGACY_TOKEN`.\n' > "$tmpd/README.md"
( cd "$tmpd" && python3 -m docdrift.cli check >/dev/null 2>&1 ); code=$?
[ "$code" = "1" ] || fail "drift should exit 1, got $code"
( cd "$tmpd" && python3 -m docdrift.cli check --docs missing.md >/dev/null 2>&1 ); code=$?
[ "$code" = "2" ] || fail "usage error should exit 2, got $code"
echo "exit codes 0/1/2 as documented"

echo "== check 5/5: dogfood (this repo's own docs must match its own code)"
python3 -m docdrift.cli check --docs README.md CHANGELOG.md --src docdrift >/dev/null 2>&1 || fail "docdrift reports drift in its own repo"

echo "ALL CHECKS PASSED"
