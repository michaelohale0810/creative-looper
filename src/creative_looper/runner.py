"""Running the pipeline for real: one run (with its folder, log and CSV row), or a loop of them."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from crewai import LLM

from creative_looper import paths
from creative_looper.domains import pick_pair
from creative_looper.errors import short_error
from creative_looper.observability import logger, setup_run_logging
from creative_looper.pipeline import ImprovementFailed, RunOutcome, run_pipeline
from creative_looper.runlog import CSV_NAME, append_row, build_row

MAX_CONSECUTIVE_FAILURES = 3  # failed runs in a row before the loop gives up


def run_once(
    primary: str,
    target: str,
    llm: LLM,
    provider: str | None = None,
    verbose: bool = False,
    root: Path | None = None,
) -> RunOutcome:
    """One complete run: create its folder and log, run the pipeline, and record a CSV row.

    The row is written however the run ends, then the original exception (if any) is
    raised again for the caller to report.
    """
    root = root or paths.OUTPUT_ROOT
    run_dir = paths.create_run_dir(primary, target, root=root)
    print(f"Results will be saved to: {run_dir}")
    print(f"Log file: {setup_run_logging(run_dir, verbose=verbose)}")
    logger.info("run started: %s -> %s (model %s)", primary, target, llm.model)
    print(f"Model: {llm.model}")

    started = datetime.now()
    outcome = RunOutcome(run_dir)
    status, error = "complete", ""
    try:
        outcome = run_pipeline(primary, target, run_dir, llm, provider, verbose)
    except ImprovementFailed as e:
        outcome, status, error = e.outcome, "failed", str(e.__cause__ or e)
        raise
    except (KeyboardInterrupt, EOFError):
        status = "cancelled"
        raise
    except Exception as e:
        status, error = "failed", str(e)
        raise
    finally:
        try:
            append_row(
                root / CSV_NAME,
                build_row(
                    primary=primary, target=target, started=started, finished=datetime.now(),
                    status=status, error=error, run_dir=run_dir, model=str(llm.model),
                    first=outcome.first, second=outcome.second,
                ),
            )
        except OSError as e:  # a CSV problem must not hide the run's real outcome
            logger.warning("could not write %s: %s", CSV_NAME, e)
            print(f"Warning: could not write {CSV_NAME}: {e}")
    print(f"Done. Reports written to: {run_dir}")
    return outcome


@dataclass
class LoopSummary:
    runs: int = 0  # runs started
    failures: int = 0
    interrupted: bool = False  # ended by Ctrl+C
    gave_up: bool = False  # too many failures in a row


def run_loop(
    primaries: list[str],
    targets: list[str],
    llm: LLM,
    provider: str | None = None,
    verbose: bool = False,
    max_runs: int | None = None,
    rng: random.Random | None = None,
    run: Callable[..., RunOutcome] = run_once,
) -> LoopSummary:
    """Draw a random pair of domains and run the pipeline on it, again and again.

    Runs until Ctrl+C (the run in progress is abandoned, keeping its reports, and recorded
    as `cancelled`), until `max_runs` runs have started, or after MAX_CONSECUTIVE_FAILURES
    failed runs in a row. A single failed run is recorded in the CSV and the loop carries
    on. `run` can be replaced in tests.
    """
    summary = LoopSummary()
    in_a_row = 0
    while max_runs is None or summary.runs < max_runs:
        primary, target = pick_pair(primaries, targets, rng)
        summary.runs += 1
        print(f"\n=== Run {summary.runs}: {primary} → {target} ===")
        try:
            run(primary, target, llm, provider, verbose)
        except KeyboardInterrupt:
            summary.interrupted = True
            print("\nInterrupted: leaving the loop.")
            break
        except Exception as e:  # recorded in the CSV by run_once; the loop carries on
            summary.failures += 1
            in_a_row += 1
            cause = e.__cause__ or e
            print(f"Run {summary.runs} failed ({type(cause).__name__}): {short_error(cause)}")
            if in_a_row >= MAX_CONSECUTIVE_FAILURES:
                summary.gave_up = True
                print(f"{in_a_row} failed runs in a row: stopping. Check the model and run.log.")
                break
            continue
        in_a_row = 0
    print(
        f"\nLoop finished: {summary.runs} run(s) started, {summary.failures} failed. "
        f"Results are in {paths.OUTPUT_ROOT / CSV_NAME}"
    )
    return summary
