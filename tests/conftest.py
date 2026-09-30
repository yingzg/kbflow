import pytest

from kbflow.scanners.file_index import FileIndex


@pytest.fixture(autouse=True)
def _isolate_home_and_cwd(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def make_index(tmp_path):
    def _make(files):
        for name, content in files.items():
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return FileIndex(tmp_path)

    return _make
