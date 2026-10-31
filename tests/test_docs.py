"""Doc-side extraction. The hard requirement here is no false positives."""

from __future__ import annotations

import textwrap

from docdrift.docs import scan_doc


def write(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_backticked_env_var_is_a_claim(tmp_path):
    path = write(tmp_path, "README.md", "Set `DATABASE_URL` before starting.\n")
    assert "DATABASE_URL" in scan_doc(path).env


def test_export_line_is_a_claim(tmp_path):
    path = write(tmp_path, "README.md", "export STRIPE_SECRET_KEY=sk_test\n")
    assert "STRIPE_SECRET_KEY" in scan_doc(path).env


def test_fenced_block_is_a_claim(tmp_path):
    path = write(tmp_path, "README.md", """
        ```bash
        API_TOKEN=abc uvicorn app:app
        ```
    """)
    assert "API_TOKEN" in scan_doc(path).env


def test_plain_prose_acronyms_are_not_claims(tmp_path):
    path = write(tmp_path, "README.md", "This speaks HTTP and JSON over TCP, not XML.\n")
    facts = scan_doc(path)
    assert facts.env == {}


def test_uppercase_words_without_underscores_are_not_claims(tmp_path):
    path = write(tmp_path, "README.md", "Use the CLI, read the README, the MIT license applies.\n")
    assert scan_doc(path).env == {}


def test_html_comment_is_ignored(tmp_path):
    path = write(tmp_path, "README.md", """
        Visible text.
        <!-- Set `SECRET_FROM_COMMENT` when debugging. -->
        More visible text.
    """)
    assert "SECRET_FROM_COMMENT" not in scan_doc(path).env


def test_long_flag_is_a_claim(tmp_path):
    path = write(tmp_path, "README.md", "Run `docdrift check --fail-on stale`.\n")
    assert "--fail-on" in scan_doc(path).flags


def test_number_range_is_not_a_flag(tmp_path):
    path = write(tmp_path, "README.md", "Covers versions 1.0--2.0 only.\n")
    assert scan_doc(path).flags == {}


def test_bare_double_dash_is_not_a_flag(tmp_path):
    path = write(tmp_path, "README.md", "Then run `-- status`.\n")
    assert scan_doc(path).flags == {}


def test_symbols_off_by_default(tmp_path):
    path = write(tmp_path, "README.md", "Call `parse_flags()` yourself.\n")
    assert scan_doc(path).symbols == {}


def test_backticked_snake_case_symbol_when_enabled(tmp_path):
    path = write(tmp_path, "README.md", "Call `parse_flags()` yourself.\n")
    assert "parse_flags" in scan_doc(path, symbols=True).symbols


def test_backticked_uppercase_is_not_a_symbol(tmp_path):
    path = write(tmp_path, "README.md", "Set `DATABASE_URL` first.\n")
    assert scan_doc(path, symbols=True).symbols == {}


def test_line_numbers_point_at_the_claim(tmp_path):
    path = write(tmp_path, "README.md", """
        # Title

        Some text.

        Set `MISSING_VAR` here.
    """)
    facts = scan_doc(path)
    assert facts.env["MISSING_VAR"][1] == 6


# --- suppressions: the difference between a useful checker and a noisy one ---

def test_fenced_block_tagged_ignore_is_not_a_claim(tmp_path):
    path = write(tmp_path, "README.md", """
        ```console docdrift-ignore
        $ tool --not-a-real-flag
        Set `NOT_REAL_EITHER`.
        ```
    """)
    facts = scan_doc(path)
    assert facts.flags == {} and facts.env == {}


def test_untagged_fence_is_still_a_claim(tmp_path):
    path = write(tmp_path, "README.md", """
        ```console
        $ tool --real-flag
        ```
    """)
    assert "--real-flag" in scan_doc(path).flags


def test_ignore_next_line_only_skips_one_line(tmp_path):
    path = write(tmp_path, "README.md", """
        <!-- docdrift: ignore-next-line -->
        Illustrative `SKIPPED_NAME` here.
        But `REAL_NAME` here is a claim.
    """)
    facts = scan_doc(path)
    assert "SKIPPED_NAME" not in facts.env
    assert "REAL_NAME" in facts.env


def test_suppression_keeps_line_numbers_honest(tmp_path):
    path = write(tmp_path, "README.md", """
        ```console docdrift-ignore
        $ pretend
        ```
        Set `REAL_NAME` here.
    """)
    assert scan_doc(path).env["REAL_NAME"][1] == 5
