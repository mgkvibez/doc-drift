"""End to end: exit codes are the contract CI depends on."""

from __future__ import annotations

import json
import textwrap

import pytest

from docdrift.cli import main


def project(tmp_path, readme, source):
    (tmp_path / "README.md").write_text(textwrap.dedent(readme), encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    (src / "app.py").write_text(textwrap.dedent(source), encoding="utf-8")
    return tmp_path


@pytest.fixture
def clean(tmp_path, monkeypatch):
    path = project(tmp_path, "Set `DATABASE_URL`.\n", """
        import os
        KEY = os.environ["DATABASE_URL"]
    """)
    monkeypatch.chdir(path)
    return path


def test_clean_project_exits_zero(clean, capsys):
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert "no issues found by docdrift v0.1.0" in out


def test_stale_env_var_fails(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Set `DATABASE_URL` and `LEGACY_TOKEN`.\n", """
        import os
        KEY = os.environ["DATABASE_URL"]
    """)
    monkeypatch.chdir(path)
    assert main(["check"]) == 1
    out = capsys.readouterr().out
    assert "stale-env" in out and "LEGACY_TOKEN" in out
    assert "README.md:1" in out


def test_undocumented_flag_fails_by_default(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Just prose.\n", """
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--secret-mode", action="store_true")
    """)
    monkeypatch.chdir(path)
    assert main(["check"]) == 1
    assert "undocumented-flag" in capsys.readouterr().out


def test_fail_on_stale_ignores_undocumented_only(tmp_path, monkeypatch):
    path = project(tmp_path, "Just prose.\n", """
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--secret-mode", action="store_true")
    """)
    monkeypatch.chdir(path)
    assert main(["check", "--fail-on", "stale"]) == 0


def test_fail_on_none_never_fails(tmp_path, monkeypatch):
    path = project(tmp_path, "Set `GONE`.\n", "")
    monkeypatch.chdir(path)
    assert main(["check", "--fail-on", "none"]) == 0


def test_ignore_exact_and_prefix(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Set `GONE` and `ALSO_GONE`.\n", "")
    monkeypatch.chdir(path)
    assert main(["check", "--ignore", "GONE", "--ignore", "ALSO_*"]) == 0
    assert "no issues found" in capsys.readouterr().out


def test_json_output_shape(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Set `GONE`.\n", "")
    monkeypatch.chdir(path)
    assert main(["check", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["stale"] == 1
    finding = payload["findings"][0]
    assert finding["kind"] == "stale" and finding["subject"] == "env"
    assert finding["doc"]["line"] == 1


def test_missing_path_is_a_usage_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["check", "--docs", "nope.md"]) == 2


def test_no_docs_anywhere_is_a_usage_error(tmp_path, monkeypatch):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["check"]) == 2


def test_symbols_flag_finds_renamed_function(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Call `old_helper()` to start.\n", """
        def new_helper():
            pass
    """)
    monkeypatch.chdir(path)
    assert main(["check"]) == 0
    assert main(["check", "--symbols"]) == 1
    assert "stale-symbol" in capsys.readouterr().out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_builtin_argparse_flags_are_never_reported(tmp_path, monkeypatch, capsys):
    path = project(tmp_path, "Just prose.\n", """
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--version", action="version", version="1")
        p.add_argument("--help")
    """)
    monkeypatch.chdir(path)
    assert main(["check"]) == 0
    assert "undocumented-flag" not in capsys.readouterr().out
