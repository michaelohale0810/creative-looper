import pytest
from helpers import FakeJudge

from creative_looper.benchmark import JudgeUnavailable, ask_judge, parse_judgement

NO_WAIT = lambda _seconds: None  # noqa: E731


def test_parse_plain_and_fenced_json():
    assert parse_judgement('{"a": 1}') == {"a": 1}
    assert parse_judgement('Sure!\n```json\n{"a": {"score": 5}}\n```\nDone') == {"a": {"score": 5}}


@pytest.mark.parametrize("bad", ["", "no json here", "{broken", "[1, 2]"])
def test_parse_rejects_unusable_replies(bad):
    assert parse_judgement(bad) is None


def test_judge_retries_network_errors_then_succeeds():
    judge = FakeJudge([OSError("dns"), OSError("dns"), '{"ok": 1}'])
    assert ask_judge(judge, "p", "x", sleep=NO_WAIT) == {"ok": 1}
    assert judge.calls == 3


def test_unreachable_judge_raises_after_all_attempts():
    judge = FakeJudge([OSError("dns")] * 3)
    with pytest.raises(JudgeUnavailable):
        ask_judge(judge, "p", "x", sleep=NO_WAIT)
    assert judge.calls == 3


def test_judge_that_answers_without_json_gives_none_not_an_error():
    judge = FakeJudge(["sorry, no"] * 3)
    assert ask_judge(judge, "p", "x", sleep=NO_WAIT) is None
