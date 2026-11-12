import pytest
from helpers import DISTANCE, GOOD_REPORT, UNIQUE, FakeJudge, make_run_dir

from creative_looper.benchmark import Criterion, JudgeUnavailable, final_uniqueness, run_benchmark
from creative_looper.report import PITCH2_REPORT, PITCH_REPORT


@pytest.fixture
def no_wait(monkeypatch):
    monkeypatch.setattr("creative_looper.benchmark.judge.time.sleep", lambda _s: None)


def test_run_is_scored_on_distance_plus_the_pitch(tmp_path):
    judge = FakeJudge([DISTANCE, GOOD_REPORT, UNIQUE])
    result = run_benchmark(make_run_dir(tmp_path), "A", "B", judge)
    assert result.pitch == PITCH_REPORT and judge.calls == 3
    # the test pitch has almost no named things, so the red flags cost uniqueness points
    assert result.red_flags and result.uniqueness_penalty >= 1
    assert result.index == 7 + 6 + 5 + (6 - result.uniqueness_penalty)


def test_missing_pitch_is_an_error_not_an_empty_score(tmp_path):
    with pytest.raises(ValueError, match="nothing to score"):
        run_benchmark(tmp_path, "A", "B", FakeJudge([]))


def test_pitch2_is_scored_reusing_the_first_semantic_distance(tmp_path):
    run_dir = make_run_dir(tmp_path)
    (run_dir / PITCH2_REPORT).write_text("# Better\n\ntext\n")
    judge = FakeJudge([GOOD_REPORT, UNIQUE])  # no semantic-distance reply is needed
    reused = Criterion(8, "kept from benchmark 1")
    result = run_benchmark(run_dir, "A", "B", judge, PITCH2_REPORT, reused)
    assert judge.calls == 2
    assert result.pitch == PITCH2_REPORT and result.semantic_distance is reused


def test_one_unreachable_call_becomes_na(tmp_path, no_wait):
    script = [DISTANCE] + [OSError("x")] * 3 + [UNIQUE]
    result = run_benchmark(make_run_dir(tmp_path), "A", "B", FakeJudge(script))
    assert result.metaphorical_density.score is None
    assert result.index is None


def test_scoring_stops_when_the_judge_stays_unreachable(tmp_path, no_wait):
    judge = FakeJudge([OSError("dns")] * 100)
    with pytest.raises(JudgeUnavailable):
        run_benchmark(make_run_dir(tmp_path), "A", "B", judge)
    assert judge.calls == 6  # two calls x three attempts, then it gives up


def test_final_uniqueness_takes_a_point_per_red_flag_and_never_drops_below_one():
    assert final_uniqueness(Criterion(9), flag_penalty=0).score == 9
    assert final_uniqueness(Criterion(5), flag_penalty=2).score == 3
    assert final_uniqueness(Criterion(2), flag_penalty=3).score == 1
    assert final_uniqueness(Criterion(None), flag_penalty=3).score is None
