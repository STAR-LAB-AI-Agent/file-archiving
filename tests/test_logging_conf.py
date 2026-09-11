"""日志敏感信息打码单测。"""

from file_organizer.logging_conf import mask_sensitive


def test_mask_sensitive():
    assert mask_sensitive("api_key=sk-123456") == "api_key=***"
    assert mask_sensitive("token: abcdef") == "token=***"
    assert mask_sensitive("password = hunter2") == "password=***"
    assert "1234" in mask_sensitive("普通消息 1234")  # 无敏感信息不变
