import csv
import random

import pytest
from helpers import make_result

from creative_looper import runner
from creative_looper.pipeline import ImprovementFailed, RunOutcome
from creative_looper.runner import MAX_CONSECUTIVE_FAILURES, run_loop, run_once


class FakeLLM:
    model = "fake/model"


def rows(root):
    with (root / "runs.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.paths, "OUTPUT_ROOT", tmp_path)
    monkeypatch.setattr(runner, "setup_run_logging", lambda run_dir, verbose=False: run_dir / "run.log")
    return tmp_path


def test_a_complete_run_is_recorded(root, monkeypatch):
    monkeypatch.setattr(
        runner, "run_pipeline",
        lambda primary, target, run_dir, *a: RunOutcome(run_dir, make_result(), make_result(uq=6)),
    )
    outcome = run_once("Geology", "Jazz", FakeLLM(), root=root)
    [row] = rows(root)
    assert (row["primary_domain"], row["target_domain"], row["status"]) == ("Geology", "Jazz", "complete")
    assert row["pitch2_uniqueness"] == "6" and row["model"] == "fake/model"
    assert row["run_folder"] == outcome.run_dir.name and outcome.run_dir.parent == root


@pytest.mark.parametrize(
    "error, status",
    [(RuntimeError("boom\nlines"), "failed"), (KeyboardInterrupt(), "cancelled")],
)
def test_failures_and_ctrl_c_are_recorded_then_reraised(root, monkeypatch, error, status):
    def broken(*args):
        raise error

    monkeypatch.setattr(runner, "run_pipeline", broken)
    with pytest.raises(type(error)):
        run_once("A", "B", FakeLLM(), root=root)
    [row] = rows(root)
    assert row["status"] == status
    assert row["error"] == ("boom lines" if status == "failed" else "")


def test_a_failure_after_the_pitch_keeps_the_scores_it_got(root, monkeypatch):
    def partial(primary, target, run_dir, *a):
        raise ImprovementFailed("revision failed", RunOutcome(run_dir, make_result()))

    monkeypatch.setattr(runner, "run_pipeline", partial)
    with pytest.raises(ImprovementFailed):
        run_once("A", "B", FakeLLM(), root=root)
    [row] = rows(root)
    assert row["status"] == "failed" and row["pitch_index"] == "20.0" and row["pitch2_index"] == ""


class Recorder:
    """A stand-in for run_once that logs the pairs it was given."""

    def __init__(self, outcomes=None):
        self.pairs, self.outcomes = [], list(outcomes or [])

    def __call__(self, primary, target, llm, provider, verbose):
        self.pairs.append((primary, target))
        item = self.outcomes.pop(0) if self.outcomes else RunOutcome(None)
        if isinstance(item, BaseException):  # includes KeyboardInterrupt
            raise item
        return item


def loop(run, **kwargs):
    return run_loop(["A", "B", "C"], ["x", "y", "z"], FakeLLM(), run=run, rng=random.Random(3), **kwargs)


def test_loop_stops_after_max_runs():
    run = Recorder()
    summary = loop(run, max_runs=4)
    assert len(run.pairs) == summary.runs == 4 and not summary.interrupted


def test_loop_draws_random_pairs_from_both_lists():
    run = Recorder()
    loop(run, max_runs=30)
    assert {p for p, _ in run.pairs} == {"A", "B", "C"} and {t for _, t in run.pairs} == {"x", "y", "z"}


def test_one_failed_run_does_not_end_the_loop():
    run = Recorder([RuntimeError("blip")])
    summary = loop(run, max_runs=3)
    assert summary.runs == 3 and summary.failures == 1 and not summary.gave_up


def test_repeated_failures_in_a_row_end_the_loop():
    run = Recorder([RuntimeError("down")] * 10)
    summary = loop(run)
    assert summary.gave_up and summary.runs == summary.failures == MAX_CONSECUTIVE_FAILURES


def test_a_success_resets_the_failure_count():
    outcomes = [RuntimeError("x"), RuntimeError("x"), RunOutcome(None), RuntimeError("x"), RuntimeError("x"), RunOutcome(None)]
    summary = loop(Recorder(outcomes), max_runs=6)
    assert summary.runs == 6 and not summary.gave_up


def test_ctrl_c_ends_the_loop_cleanly():
    run = Recorder([RunOutcome(None), KeyboardInterrupt()])
    summary = loop(run)
    assert summary.interrupted and summary.runs == 2 and not summary.gave_up


def test_a_loop_without_a_limit_keeps_going_until_interrupted():
    run = Recorder([RunOutcome(None)] * 25 + [KeyboardInterrupt()])
    assert loop(run).runs == 26
