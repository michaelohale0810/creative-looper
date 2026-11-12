"""The whole run, start to finish, independent of the command line.

    crew (steps 1-4 + pitch)  ->  benchmark  ->  pitch2  ->  benchmark2  ->  README

`main.py` parses arguments and turns errors into messages; this module decides what
happens in what order, and guarantees the README index is written however the run ends.
"""

from dataclasses import dataclass
from pathlib import Path

from crewai import LLM
from crewai.types.usage_metrics import UsageMetrics

from creative_looper.benchmark import (
    BenchmarkResult,
    add_readme_summary,
    benchmark_files,
    benchmark_run,
    feedback_text,
)
from creative_looper.config import get_judge_llm
from creative_looper.crew import run_crew, run_revision
from creative_looper.observability import logger
from creative_looper.report import (
    BRIEF_REPORT,
    PITCH2_REPORT,
    PITCH_REPORT,
    finalize_run,
    read_report,
)

Usage = list[tuple[str, UsageMetrics]]


@dataclass
class RunOutcome:
    """What a run produced: its folder and the benchmark of each pitch that got one."""

    run_dir: Path
    first: BenchmarkResult | None = None  # benchmark of the pitch
    second: BenchmarkResult | None = None  # benchmark2, of pitch2


class ImprovementFailed(Exception):
    """Scoring or revising the pitch failed after the pitch itself was written.

    The reports that exist are kept and indexed; the original error is `__cause__`, and
    `outcome` holds whatever was scored before the failure.
    """

    def __init__(self, message: str, outcome: RunOutcome):
        super().__init__(message)
        self.outcome = outcome


def show(result: BenchmarkResult, run_dir: Path, name: str, tag: str) -> None:
    """Print one benchmark's headline."""
    index = result.index if result.index is not None else "n/a"
    print(
        f"Creativity Index for {name}: {index} / 40 (judge {result.judge_model}). "
        f"Details: {run_dir / benchmark_files(tag)[0]}"
    )


def show_change(first: BenchmarkResult, second: BenchmarkResult) -> None:
    """Print how much the revision changed the index (if both could be scored)."""
    if first.index is not None and second.index is not None:
        print(f"pitch -> pitch2: {first.index:g} -> {second.index:g} ({second.index - first.index:+g}) / 40")


def run_pipeline(
    primary: str,
    target: str,
    run_dir: Path,
    llm: LLM,
    provider: str | None = None,
    verbose: bool = False,
) -> RunOutcome:
    """Run every stage for one pair of domains and return what was produced.

    However the run ends (an error, or Ctrl+C), the README index of the reports written
    so far is left in the run folder. Errors in the first stage (analysis and pitch)
    propagate as they are; errors after it are raised as ImprovementFailed.
    """
    try:
        usage = run_crew(primary, target, run_dir, llm, verbose=verbose)
    except BaseException:
        finalize_run(run_dir, primary, target)
        raise
    return improve_pitch(primary, target, run_dir, llm, usage, provider, verbose)


def improve_pitch(
    primary: str,
    target: str,
    run_dir: Path,
    llm: LLM,
    usage: Usage,
    provider: str | None = None,
    verbose: bool = False,
) -> RunOutcome:
    """Score the pitch, write pitch2 from that scoring, then score pitch2.

    The README index is written once at the end (a `finally`, so even on failure or
    Ctrl+C): writing it after every stage would add each report's header twice.
    """
    outcome = RunOutcome(run_dir)
    try:
        judge = get_judge_llm(provider)
        outcome.first = benchmark_run(run_dir, primary, target, judge)
        show(outcome.first, run_dir, "pitch", "")

        usage = usage + run_revision(
            primary,
            target,
            run_dir,
            llm,
            original_pitch=read_report(run_dir, PITCH_REPORT),
            feedback=feedback_text(outcome.first),
            brief=read_report(run_dir, BRIEF_REPORT),
            verbose=verbose,
        )

        # Semantic distance rates the phenomenon and mapping, which pitch2 doesn't change.
        outcome.second = benchmark_run(
            run_dir, primary, target, judge, PITCH2_REPORT, "2", outcome.first.semantic_distance
        )
        show(outcome.second, run_dir, "pitch2", "2")
        show_change(outcome.first, outcome.second)
    except Exception as e:
        logger.error("improvement stage failed: %s", e)
        raise ImprovementFailed(str(e), outcome) from e
    finally:
        finalize_run(run_dir, primary, target, usage=usage)
        for result, tag in ((outcome.first, ""), (outcome.second, "2")):
            if result is not None:
                add_readme_summary(run_dir, result, tag)
    return outcome


def score_run(run_dir: Path, primary: str, target: str, provider: str | None = None) -> None:
    """Score the pitch (and pitch2, if the run has one) of a run that already exists."""
    judge = get_judge_llm(provider)
    first = benchmark_run(run_dir, primary, target, judge)
    add_readme_summary(run_dir, first)
    show(first, run_dir, "pitch", "")
    if (run_dir / PITCH2_REPORT).exists():
        second = benchmark_run(run_dir, primary, target, judge, PITCH2_REPORT, "2", first.semantic_distance)
        add_readme_summary(run_dir, second, "2")
        show(second, run_dir, "pitch2", "2")
        show_change(first, second)
