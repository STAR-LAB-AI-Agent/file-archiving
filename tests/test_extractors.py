"""extractors 内容抽取单测。"""

from file_organizer.extractors import extract_text


def test_extract_txt(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("本合同甲方乙方", encoding="utf-8")
    assert "合同" in extract_text(f)


def test_extract_truncates(tmp_path):
    f = tmp_path / "long.txt"
    f.write_text("a" * 2000, encoding="utf-8")
    assert len(extract_text(f, max_chars=100)) == 100


def test_extract_unknown_suffix_empty(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_bytes(b"\x00\x01\x02")
    assert extract_text(f) == ""


def test_extract_missing_file_empty(tmp_path):
    assert extract_text(tmp_path / "nope.txt") == ""
