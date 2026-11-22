"""Unit tests for data directory resolution and file helpers in quranai.utils."""

import pathlib
import pytest

from quranai.utils import (
    DATA_DIR_ENV_VAR,
    get_data_dir,
    get_data_file_path,
    list_data_files,
    read_data_file,
)


def test_get_data_dir_defaults_to_package_data_dir(monkeypatch):
    monkeypatch.delenv(DATA_DIR_ENV_VAR, raising=False)
    data_dir = get_data_dir()
    assert isinstance(data_dir, pathlib.Path)
    assert data_dir.name == "data"
    assert data_dir.parent.name == "quranai"


def test_get_data_dir_whitespace_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV_VAR, "   ")
    data_dir = get_data_dir()
    assert data_dir.name == "data"
    assert data_dir.parent.name == "quranai"


def test_get_data_dir_uses_env_override(monkeypatch, tmp_path):
    custom_dir = tmp_path / "corpora"
    monkeypatch.setenv(DATA_DIR_ENV_VAR, str(custom_dir))

    assert get_data_dir() == custom_dir
    assert not custom_dir.exists()

    ensured = get_data_dir(ensure_exists=True)
    assert ensured == custom_dir
    assert custom_dir.is_dir()


def test_get_data_dir_expands_tilde(monkeypatch):
    monkeypatch.setenv(DATA_DIR_ENV_VAR, "~/quranai-test-data")
    assert get_data_dir() == pathlib.Path("~/quranai-test-data").expanduser()


def test_get_data_file_path_and_ensure_dir(monkeypatch, tmp_path):
    custom_dir = tmp_path / "nested" / "corpora"
    monkeypatch.setenv(DATA_DIR_ENV_VAR, str(custom_dir))

    path = get_data_file_path("hadith.json", ensure_dir=True)
    assert path == custom_dir / "hadith.json"
    assert custom_dir.is_dir()


def test_list_data_files_and_read_data_file(monkeypatch, tmp_path):
    custom_dir = tmp_path / "corpora"
    custom_dir.mkdir()
    (custom_dir / "sample.txt").write_text("hello world", encoding="utf-8")
    (custom_dir / "quranai.chroma").mkdir()
    monkeypatch.setenv(DATA_DIR_ENV_VAR, str(custom_dir))

    files = list_data_files()
    assert files == ["sample.txt"]
    assert read_data_file("sample.txt") == "hello world"


def test_list_data_files_missing_dir_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv(DATA_DIR_ENV_VAR, str(tmp_path / "does_not_exist"))
    assert list_data_files() == []
