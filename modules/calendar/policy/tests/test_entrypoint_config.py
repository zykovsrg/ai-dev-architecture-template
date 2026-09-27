"""Entrypoint configuration must fail closed before any Calendar access."""

import json
from pathlib import Path

import pytest

from hub_calendar_policy.__main__ import ConfigError, load_allowed_calendar_ids


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "allowlist.json"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_installed_default_allows_no_calendar(tmp_path: Path) -> None:
    path = write(tmp_path, json.dumps({"calendar_ids": []}))

    assert load_allowed_calendar_ids(path) == frozenset()


def test_selected_identifiers_are_loaded(tmp_path: Path) -> None:
    path = write(tmp_path, json.dumps({"calendar_ids": ["calendar-1", "calendar-2"]}))

    assert load_allowed_calendar_ids(path) == frozenset({"calendar-1", "calendar-2"})


def test_an_absent_key_allows_no_calendar(tmp_path: Path) -> None:
    path = write(tmp_path, json.dumps({}))

    assert load_allowed_calendar_ids(path) == frozenset()


@pytest.mark.parametrize(
    "text",
    ['{"calendar_ids": "calendar-1"}', '{"calendar_ids": [1]}', '{"calendar_ids": [""]}', "[]"],
)
def test_a_malformed_allowlist_is_refused(tmp_path: Path, text: str) -> None:
    path = write(tmp_path, text)

    with pytest.raises(ConfigError):
        load_allowed_calendar_ids(path)


def test_invalid_json_is_refused(tmp_path: Path) -> None:
    path = write(tmp_path, "{not json")

    with pytest.raises(ConfigError, match="not valid JSON"):
        load_allowed_calendar_ids(path)


def test_a_missing_allowlist_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="missing"):
        load_allowed_calendar_ids(tmp_path / "absent.json")
