import pytest
from helpers import make_result

from creative_looper import pipeline
from creative_looper.report import PITCH2_REPORT, PITCH_REPORT


@pytest.fixture
def calls(monkeypatch, tmp_path):
    """Replace every slow stage with a recorder, and write the pitch files they would."""
    log = []
    (tmp_path / PITCH_REPORT).write_text("# Pitch\n")
    monkeypatch.setattr(pipeline, "get_judge_llm", lambda provider=None: "judge")

    def fake_benchmark(run_dir, primary, target, judge, pitch=PITCH_REPORT, tag="", distance=None):
        log.append(("benchmark", pitch, distance))
        return make_result()

    def fake_revision(*args, **kwargs):
        log.append(("revise", kwargs["feedback"] != "", kwargs["original_pitch"]))
        (tmp_path / PITCH2_REPORT).write_text("# Pitch 2\n")
        return []

    monkeypatch.setattr(pipeline, "benchmark_run", fake_benchmark)
    monkeypatch.setattr(pipeline, "run_revision", fake_revision)
    monkeypatch.setattr(pipeline, "finalize_run", lambda *a, **k: log.append(("finalize",)))
    monkeypatch.setattr(pipeline, "add_readme_summary", lambda *a, **k: log.append(("summary", a[-1] if len(a) > 2 else "")))
    return log


def test_stages_run_in_order_and_pitch2_reuses_the_first_distance(calls, tmp_path):
    pipeline.improve_pitch("A", "B", tmp_path, llm=None, usage=[])
    stages = [c[0] for c in calls]
    assert stages == ["benchmark", "revise", "benchmark", "finalize", "summary", "summary"]
    assert calls[0][1] == PITCH_REPORT and calls[2][1] == PITCH2_REPORT
    assert calls[2][2] is not None  # the second benchmark was handed the first one's distance
    assert calls[1][1] is True and "Pitch" in calls[1][2]  # feedback and the original pitch reached the reviser


def test_readme_is_still_written_when_a_stage_fails(calls, tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("model down")

    monkeypatch.setattr(pipeline, "run_revision", broken)
    with pytest.raises(pipeline.ImprovementFailed) as error:
        pipeline.improve_pitch("A", "B", tmp_path, llm=None, usage=[])
    assert isinstance(error.value.__cause__, RuntimeError)
    assert ("finalize",) in calls and ("summary", "") in calls  # first benchmark is still indexed
    assert sum(1 for c in calls if c[0] == "summary") == 1  # no second benchmark to index


def test_ctrl_c_still_writes_the_readme_and_is_not_wrapped(calls, tmp_path, monkeypatch):
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "run_revision", interrupted)
    with pytest.raises(KeyboardInterrupt):
        pipeline.improve_pitch("A", "B", tmp_path, llm=None, usage=[])
    assert ("finalize",) in calls


def test_a_completed_run_reports_both_benchmarks(calls, tmp_path):
    outcome = pipeline.improve_pitch("A", "B", tmp_path, llm=None, usage=[])
    assert outcome.first is not None and outcome.second is not None


def test_failure_carries_what_was_scored_so_far(calls, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "run_revision", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    with pytest.raises(pipeline.ImprovementFailed) as error:
        pipeline.improve_pitch("A", "B", tmp_path, llm=None, usage=[])
    assert error.value.outcome.first is not None and error.value.outcome.second is None


def test_the_readme_is_written_even_when_the_first_stage_is_interrupted(tmp_path, monkeypatch):
    written = []

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(pipeline, "run_crew", interrupted)
    monkeypatch.setattr(pipeline, "finalize_run", lambda *a, **k: written.append(a[0]))
    with pytest.raises(KeyboardInterrupt):
        pipeline.run_pipeline("A", "B", tmp_path, llm=None)
    assert written == [tmp_path]
