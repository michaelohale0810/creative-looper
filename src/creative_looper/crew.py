"""Assembling and running the CrewAI crews.

Two crews run per pipeline: the main one (analysis, brief, pitch) and a one-task crew that
writes pitch2. They are separate because pitch2 needs the first benchmark's scoring,
which happens outside CrewAI between them.
"""

import sys
import time
from pathlib import Path

from crewai import LLM, Crew, Process
from crewai.types.usage_metrics import UsageMetrics

from creative_looper.agents import (
    analogical_mapper,
    analytical_critic,
    concept_distiller,
    phenomenon_explorer,
    pitch_reviser,
    pitch_writer,
)
from creative_looper.leakage import count_domain_mentions
from creative_looper.observability import Heartbeat, RunTracker, format_elapsed, logger
from creative_looper.report import PITCH2_REPORT, PITCH_REPORT
from creative_looper.tasks import (
    critique_mapping,
    distill_brief,
    explore_phenomenon,
    map_to_target,
    revise_pitch,
    write_pitch,
)

LABELS = [
    "Exploring phenomenon",
    "Mapping to target",
    "Critiquing",
    "Distilling target-domain brief",
    "Writing story pitch",
]
REVISION_LABELS = ["Revising pitch (pitch2)"]


def kickoff(crew: Crew, tracker: RunTracker, inputs: dict[str, str]) -> None:
    """Run `crew` with progress, a heartbeat and a clear message if a step fails."""
    labels = tracker.labels
    tracker.started()
    try:
        with Heartbeat(lambda: tracker.current):
            crew.kickoff(inputs=inputs)
    except Exception:
        label, elapsed = tracker.current
        step_no = len(tracker.usage) + 1
        logger.exception(
            "step %d/%d '%s' failed after %s", step_no, len(labels), label, format_elapsed(elapsed)
        )
        print(
            f"\nFailed during step {step_no}/{len(labels)} ('{label}') "
            f"after {format_elapsed(elapsed)}.",
            file=sys.stderr,
        )
        raise


def report_leaks(run_dir: Path, primary: str, report: str) -> None:
    """Print and log how often `report` still mentions the primary domain."""
    leaks = count_domain_mentions(run_dir, primary, [report]).get(report, 0)
    logger.info("primary-domain term mentions in %s: %d", report, leaks)
    print(f"Primary-domain term mentions in {report}: {leaks}")


def run_crew(
    primary: str, target: str, run_dir: Path, llm: LLM, verbose: bool = False
) -> list[tuple[str, UsageMetrics]]:
    """Run the four analytical steps, then the story pitch (pitch), which reads only the
    brief. Returns the token usage per step. The run's README is written later, by the caller."""
    explorer = phenomenon_explorer(llm)
    mapper = analogical_mapper(llm)
    critic = analytical_critic(llm)
    distiller = concept_distiller(llm)
    writer = pitch_writer(llm)

    phenomenon = explore_phenomenon(explorer, run_dir)
    mapping = map_to_target(mapper, run_dir, phenomenon)
    critique = critique_mapping(critic, run_dir, mapping)
    brief = distill_brief(distiller, run_dir, mapping, critique, primary, target, llm)
    pitch = write_pitch(writer, run_dir, brief)

    tracker = RunTracker(llm, LABELS)
    crew = Crew(
        agents=[explorer, mapper, critic, distiller, writer],
        tasks=[phenomenon, mapping, critique, brief, pitch],
        process=Process.sequential,
        verbose=verbose,
        task_callback=tracker,
    )
    started = time.monotonic()
    kickoff(crew, tracker, {"primary_domain": primary, "target_domain": target})
    report_leaks(run_dir, primary, PITCH_REPORT)
    logger.info("analysis and pitch finished in %s", format_elapsed(time.monotonic() - started))
    return tracker.usage


def run_revision(
    primary: str,
    target: str,
    run_dir: Path,
    llm: LLM,
    original_pitch: str,
    feedback: str,
    brief: str,
    verbose: bool = False,
) -> list[tuple[str, UsageMetrics]]:
    """Write pitch2 from the first pitch, its benchmark feedback and the brief.

    The reviser may go beyond the brief, so the run's own state is passed in as inputs
    rather than as task context.
    """
    reviser = pitch_reviser(llm)
    tracker = RunTracker(llm, REVISION_LABELS)
    crew = Crew(
        agents=[reviser],
        tasks=[revise_pitch(reviser, run_dir)],
        process=Process.sequential,
        verbose=verbose,
        task_callback=tracker,
    )
    kickoff(
        crew,
        tracker,
        {
            "target_domain": target,
            "original_pitch": original_pitch,
            "feedback": feedback,
            "brief": brief,
        },
    )
    report_leaks(run_dir, primary, PITCH2_REPORT)
    return tracker.usage
