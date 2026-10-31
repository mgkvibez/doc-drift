"""Code-side extraction. ast, not grep, is the point."""

from __future__ import annotations

import textwrap

from docdrift.code import scan, scan_file


def write(tmp_path, name, body):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_os_environ_subscript(tmp_path):
    path = write(tmp_path, "a.py", """
        import os
        key = os.environ["DATABASE_URL"]
    """)
    facts = scan_file(path)
    assert "DATABASE_URL" in facts.env


def test_os_environ_get(tmp_path):
    path = write(tmp_path, "a.py", """
        import os
        key = os.environ.get("API_TOKEN", "")
    """)
    assert "API_TOKEN" in scan_file(path).env


def test_os_getenv(tmp_path):
    path = write(tmp_path, "a.py", """
        import os
        key = os.getenv("STRIPE_KEY")
    """)
    assert "STRIPE_KEY" in scan_file(path).env


def test_env_name_in_a_comment_is_not_a_read(tmp_path):
    path = write(tmp_path, "a.py", """
        # os.environ["GHOST_VAR"] is handled elsewhere
        x = 1
    """)
    assert scan_file(path).env == {}


def test_env_name_in_a_dead_string_is_not_a_read(tmp_path):
    path = write(tmp_path, "a.py", """
        MESSAGE = 'set os.environ["GHOST_VAR"] first'
    """)
    assert scan_file(path).env == {}


def test_argparse_flags_including_short_forms(tmp_path):
    path = write(tmp_path, "a.py", """
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("-f", "--file")
    """)
    facts = scan_file(path)
    assert "--dry-run" in facts.flags
    assert "--file" in facts.flags
    assert "-f" in facts.flags


def test_non_flag_add_argument_positionals_ignored(tmp_path):
    path = write(tmp_path, "a.py", """
        import argparse
        p = argparse.ArgumentParser()
        p.add_argument("target")
    """)
    assert scan_file(path).flags == {}


def test_symbols_defined_and_private_excluded(tmp_path):
    path = write(tmp_path, "a.py", """
        def public_thing():
            pass

        def _private_thing():
            pass

        class Widget:
            pass

        async def fetch_all():
            pass
    """)
    facts = scan_file(path)
    assert "public_thing" in facts.symbols
    assert "Widget" in facts.symbols
    assert "fetch_all" in facts.symbols
    assert "_private_thing" not in facts.symbols


def test_unparseable_file_is_skipped_silently(tmp_path):
    path = write(tmp_path, "broken.py", """
        def oops(:
    """)
    facts = scan_file(path)
    assert facts.env == {} and facts.flags == {} and facts.symbols == {}


def test_scan_merges_a_tree_and_skips_vendored_dirs(tmp_path):
    write(tmp_path, "pkg/a.py", 'import os\nX = os.environ["ONE"]\n')
    write(tmp_path, "pkg/deep/b.py", 'import os\nY = os.getenv("TWO")\n')
    vendored = tmp_path / ".venv" / "lib"
    vendored.mkdir(parents=True)
    (vendored / "c.py").write_text('import os\nZ = os.getenv("VENDORED")\n', encoding="utf-8")
    facts = scan([tmp_path])
    assert set(facts.env) == {"ONE", "TWO"}
