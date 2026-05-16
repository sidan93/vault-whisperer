import pytest
from pathlib import Path
from auth import load_whitelist, access_error


def test_load_whitelist_reads_user_ids(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("123456789\n987654321\n")
    assert load_whitelist(str(f)) == {123456789, 987654321}


def test_load_whitelist_skips_comments(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("# Family\n123456789\n")
    assert load_whitelist(str(f)) == {123456789}


def test_load_whitelist_skips_empty_lines(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("123456789\n\n987654321\n")
    assert load_whitelist(str(f)) == {123456789, 987654321}


def test_access_error_rejects_group():
    error = access_error("group", 123, {123})
    assert error == "Бот работает только в личных сообщениях."


def test_access_error_rejects_supergroup():
    error = access_error("supergroup", 123, {123})
    assert error == "Бот работает только в личных сообщениях."


def test_access_error_rejects_unknown_user():
    error = access_error("private", 999, {123})
    assert error == "У вас нет доступа."


def test_access_error_allows_whitelisted_user():
    error = access_error("private", 123, {123})
    assert error is None
