"""security 安全控制单测。"""

import os

import pytest

from file_organizer.security import (
    SecurityError,
    assert_within,
    is_system_path,
    is_within,
    risk_of,
)


def test_is_within(tmp_path):
    assert is_within(tmp_path / "a", tmp_path)
    assert not is_within(tmp_path.parent / "outside", tmp_path)


def test_assert_within(tmp_path):
    assert_within(tmp_path / "a", tmp_path)
    with pytest.raises(SecurityError):
        assert_within(tmp_path.parent / "x", tmp_path)


def test_risk_of():
    assert risk_of("move") == "medium"
    assert risk_of("delete") == "high"
    assert risk_of("scan") == "low"


def test_is_system_path_platform():
    if os.name == "nt":
        assert is_system_path(r"C:\Windows\System32")
    else:
        assert is_system_path("/etc")
