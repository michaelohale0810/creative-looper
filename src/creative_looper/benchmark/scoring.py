"""Scoring a pitch: build each prompt, call the judge, and combine the answers."""

import time
from pathlib import Path

from crewai import LLM

from creative_looper.benchmark.judge import MAX_CONSECUTIVE_FAILURES, JudgeUnavailable, ask_judge
from creative_looper.benchmark.prompts import REPORT_PROMPT, SEMANTIC_DISTANCE_PROMPT, UNIQUENESS_PROMPT
from creative_looper.benchmark.render import save_benchmark
from creative_looper.benchmark.results import (
    BenchmarkResult,
    Criterion,
    ground_cliches,
    to_criterion,
    to_uniqueness_detail,
)
from creative_looper.observability import format_elapsed, logger
from creative_looper.redflags import penalty, red_flags
from creative_looper.report import (
    BRIEF_REPORT,
    MAPPING_REPORT,
    PHENOMENON_REPORT,
    PITCH_REPORT,
    REPORT_TITLES,
    read_report,
)


def final_uniqueness(judged: Criterion, flag_penalty: int) -> Criterion:
    """Turn the judge's uniqueness score into the final one.

    Each rule-based red flag (see `redflags`) takes a point off, which no model can argue
    with. The score never drops below 1.
    """
    if judged.score is not None and flag_penalty:
        judged.score = max(1, judged.score - flag_penalty)
    return judged


def run_benchmark(
    run_dir: Path,
    primary: str,
    target: str,
    judge: LLM,
    pitch: str = PITCH_REPORT,
    distance: Criterion | None = None,
) -> BenchmarkResult:
    """Score the `pitch` report of a finished run with the judge model.

    Semantic distance rates the phenomenon and mapping, which a revised pitch does not
    change, so pass `distance` (from an earlier scoring of the same run) to reuse it.
    Raises ValueError if the pitch does not exist, and JudgeUnavailable if the judge
    stays unreachable.
    """
    piece = read_report(run_dir, pitch)
    if not piece:
        raise ValueError(f"{run_dir / pitch} not found; there is nothing to score")
    brief = read_report(run_dir, BRIEF_REPORT)

    logger.info("benchmark of %s started (judge %s)", pitch, judge.model)
    failures = 0

    def judged(prompt: str, label: str) -> dict:
        """Ask the judge. One unreachable call leaves an n/a score instead of losing the run."""
        nonlocal failures
        try:
            data = ask_judge(judge, prompt, label)
        except JudgeUnavailable:
            failures += 1
            if failures >= MAX_CONSECUTIVE_FAILURES:
                raise
            print(f"  could not reach the judge for {label}; scored as n/a")
            return {}
        failures = 0
        return data or {}

    if distance is None:
        print("Judging semantic distance...")
        data = judged(
            SEMANTIC_DISTANCE_PROMPT.format(
                primary=primary,
                target=target,
                phenomenon=read_report(run_dir, PHENOMENON_REPORT),
                mapping=read_report(run_dir, MAPPING_REPORT),
            ),
            "semantic distance",
        )
        distance = to_criterion(data.get("semantic_distance"))

    print(f"Judging {REPORT_TITLES[pitch]}...")
    data = judged(
        REPORT_PROMPT.format(title=REPORT_TITLES[pitch], target=target, brief=brief, piece=piece),
        pitch,
    )
    cliche_freedom = to_criterion(data.get("freedom_from_cliche"))
    cliche_freedom.cliches = ground_cliches(cliche_freedom.cliches, piece)

    # The rule-based checks run first so the uniqueness judge can be told what they found.
    flags = red_flags(piece, brief)
    logger.info("red flags in %s: %s", pitch, flags or "none")
    udata = judged(
        UNIQUENESS_PROMPT.format(
            target=target,
            brief=brief,
            piece=piece,
            flags="\n".join(f"- {f}" for f in flags) or "- none found",
        ),
        f"{pitch} uniqueness",
    ).get("uniqueness")
    detail = to_uniqueness_detail(udata)
    cut = penalty(flags)
    uniqueness = final_uniqueness(to_criterion(udata), cut)

    result = BenchmarkResult(
        primary=primary,
        target=target,
        judge_model=str(judge.model),
        pitch=pitch,
        semantic_distance=distance,
        metaphorical_density=to_criterion(data.get("metaphorical_density")),
        freedom_from_cliche=cliche_freedom,
        uniqueness=uniqueness,
        uniqueness_detail=detail,
        red_flags=flags,
        uniqueness_penalty=cut,
    )
    logger.info(
        "judged %s: density %s, cliche-freedom %s, uniqueness %s (red-flag penalty %d), index %s/40",
        pitch,
        result.metaphorical_density.score,
        result.freedom_from_cliche.score,
        uniqueness.score,
        cut,
        result.index,
    )
    return result


def benchmark_run(
    run_dir: Path,
    primary: str,
    target: str,
    judge: LLM,
    pitch: str = PITCH_REPORT,
    tag: str = "",
    distance: Criterion | None = None,
) -> BenchmarkResult:
    """Score a pitch, save the results (see `save_benchmark`), and log the judge's token cost."""
    started = time.monotonic()
    before = judge.get_token_usage_summary().model_copy()
    result = run_benchmark(run_dir, primary, target, judge, pitch, distance)
    used = judge.get_token_usage_summary().model_copy().delta_since(before)
    usage_line = (
        f"Judging used {used.prompt_tokens:,} input and {used.completion_tokens:,} output "
        f"tokens in {format_elapsed(time.monotonic() - started)}."
    )
    save_benchmark(run_dir, result, usage_line, tag)
    return result
