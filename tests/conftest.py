"""共享测试夹具。"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from file_organizer.model import FileRecord


@pytest.fixture
def make_record():
    """构造 FileRecord 的工厂，便于各 stage 单测造数。"""

    def _make(
        name="a.pdf",
        *,
        path=None,
        extension=None,
        size=100,
        mtime=1700000000.0,
        category=None,
        **kw,
    ) -> FileRecord:
        if path is None:
            path = f"/root/{name}"
        if "." in name:
            stem, _, suffix = name.rpartition(".")
            suffix = "." + suffix
        else:
            stem, suffix = name, ""
        ext = extension if extension is not None else suffix.lstrip(".")
        return FileRecord(
            path=path,
            relative_path=name,
            name=name,
            stem=stem,
            suffix=suffix,
            extension=ext,
            mime_type="application/octet-stream",
            size=size,
            mtime=mtime,
            mtime_iso=datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            category=category,
            **kw,
        )

    return _make
