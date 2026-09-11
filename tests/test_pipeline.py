"""pipeline 组合测试。"""

from pathlib import Path

import pytest

from file_organizer.pipeline import DEFAULT_PIPELINE, load_pipeline, run_pipeline
from file_organizer.stages.where import StageError


def test_default_pipeline():
    assert load_pipeline(None) == DEFAULT_PIPELINE
    assert DEFAULT_PIPELINE["stages"][0]["op"] == "classify"


def test_pipeline_compose(make_record):
    entries = [
        make_record("a.pdf", path="/root/a.pdf", extension="pdf", size=100),
        make_record("b.jpg", path="/root/b.jpg", extension="jpg", size=200),
        make_record("c.mp4", path="/root/c.mp4", extension="mp4", size=100 * 1024 * 1024),
    ]
    desc = {
        "stages": [
            {"op": "filter", "where": {"field": "extension", "op": "in", "value": ["pdf", "jpg", "mp4"]}},
            {"op": "classify", "by": "type"},
            {"op": "filter", "where": {"field": "size", "op": "gt", "value": 10485760}},
            {"op": "move", "rule": "by_category"},
        ],
        "rules": {"type_rules": {"文档": ["pdf"], "图片": ["jpg"], "视频": ["mp4"]}, "default_folder": "其他"},
    }
    out = run_pipeline(desc, entries, root="/root")
    assert len(out) == 1  # 仅 c.mp4 通过 size 过滤
    assert out[0].name == "c.mp4"
    assert out[0].category == "视频"
    assert Path(out[0].target) == Path("/root") / "视频"


def test_pipeline_unknown_op(make_record):
    with pytest.raises(StageError):
        run_pipeline({"stages": [{"op": "nope"}]}, [make_record()], root="/root")
