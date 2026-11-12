"""Command-line entry point: read the arguments, set up a run, and report problems readably.

All the real work is in `pipeline.py`; this module only talks to the person at the terminal.
"""

import argparse
import sys
import warnings
from pathlib import Path

from creative_looper.config import PROVIDERS, get_llm
from creative_looper.domains import DEFAULT_PRIMARY_FILE, DEFAULT_TARGET_FILE, load_domains
from creative_looper.errors import short_error
from creative_looper.observability import logger, setup_run_logging
from creative_looper.paths import sanitize_domain
from creative_looper.pipeline import ImprovementFailed, score_run
from creative_looper.report import read_domains
from creative_looper.runner import run_loop, run_once


def prompt_domain(label: str, example: str) -> str:
    """Ask until the user enters something that can become a folder name."""
    while True:
        value = input(f"{label} (e.g., {example}): ").strip()
        try:
            sanitize_domain(value)
        except ValueError:
            print("Please enter a domain containing at least one letter or digit.")
            continue
        return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="creative-looper",
        description="Map an unusual phenomenon from one domain onto another and pitch a novel built on it, then score its creativity.",
    )
    parser.add_argument("primary", nargs="?", help="Primary domain (prompted for if omitted)")
    parser.add_argument("target", nargs="?", help="Target domain (prompted for if omitted)")
    parser.add_argument(
        "--score-run", metavar="RUN_DIR", type=Path,
        help="Only score an existing run folder (no generation) and exit",
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Run again and again on random pairs of domains drawn from the two list files, "
        "until you press Ctrl+C",
    )
    parser.add_argument(
        "--primary-file", metavar="FILE", type=Path, default=DEFAULT_PRIMARY_FILE,
        help="With --loop: file of primary domains, one per line (default: %(default)s)",
    )
    parser.add_argument(
        "--target-file", metavar="FILE", type=Path, default=DEFAULT_TARGET_FILE,
        help="With --loop: file of target domains, one per line (default: %(default)s)",
    )
    parser.add_argument(
        "--max-runs", metavar="N", type=int,
        help="With --loop: stop after N runs (default: no limit)",
    )
    parser.add_argument(
        "-p", "--provider", choices=PROVIDERS,
        help="Model provider: 'gemini' (online, needs GEMINI_API_KEY) or 'local' (Ollama, uses "
        "LOCAL_MODEL). Overrides LLM_PROVIDER in .env; default gemini",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Show full agent output while running")
    args = parser.parse_args(argv)
    if args.score_run is not None:
        if args.primary is not None:
            parser.error("--score-run scores an existing run on its own; drop the domains")
        if not args.score_run.is_dir():
            parser.error(f"{args.score_run} is not a run folder")
        return args
    if args.max_runs is not None and not args.loop:
        parser.error("--max-runs only applies with --loop")
    if args.max_runs is not None and args.max_runs < 1:
        parser.error("--max-runs must be at least 1")
    if args.loop and args.primary is not None:
        parser.error("--loop draws its domains from the list files; drop the domains")
    if args.primary is not None and args.target is None:
        parser.error("provide both primary and target domains, or neither")
    for value in (args.primary, args.target):
        if value is not None:
            try:
                sanitize_domain(value)
            except ValueError as e:
                parser.error(str(e))
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.verbose:
        warnings.filterwarnings("ignore")

    if args.score_run is not None:
        run_dir = args.score_run.resolve()
        try:
            setup_run_logging(run_dir, verbose=args.verbose)
            score_run(run_dir, *read_domains(run_dir), provider=args.provider)
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.", file=sys.stderr)
            raise SystemExit(130)
        except (ValueError, OSError) as e:
            raise SystemExit(f"Cannot score {run_dir}: {e}")
        except Exception as e:
            logger.error("scoring failed: %s", e)
            raise SystemExit(f"Scoring failed ({type(e).__name__}): {short_error(e)}")
        return

    llm = get_llm(provider=args.provider)  # fail fast on a missing key or model, before asking for input

    if args.loop:
        loop(args, llm)
        return

    run_dir = None
    try:
        primary = args.primary or prompt_domain("Primary Domain", "Biology, Quantum Physics")
        target = args.target or prompt_domain("Target Domain", "Politics, Macroeconomics")
        run_once(primary, target, llm, args.provider, args.verbose)
    except (KeyboardInterrupt, EOFError):
        logger.warning("run cancelled by user")
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(130)
    except ImprovementFailed as e:
        # The pitch exists, so say what is kept and how to retry just the scoring.
        run_dir = e.outcome.run_dir
        raise SystemExit(
            f"The pitch was written, but scoring or revising it failed "
            f"({type(e.__cause__).__name__}): {short_error(e.__cause__)}\n"
            f"Reports so far are in {run_dir}. Score what exists later with: "
            f"creative-looper --score-run {run_dir}"
        )
    except Exception as e:
        logger.error("run failed: %s", e)
        print(f"\nRun failed ({type(e).__name__}): {short_error(e)}", file=sys.stderr)
        print("Reports finished before the failure are kept in the run folder; details are in run.log.", file=sys.stderr)
        raise SystemExit(1)


def loop(args: argparse.Namespace, llm) -> None:
    """The --loop mode: load the two lists, then run until Ctrl+C (or --max-runs)."""
    try:
        primaries = load_domains(args.primary_file)
        targets = load_domains(args.target_file)
    except ValueError as e:
        raise SystemExit(str(e))
    print(f"Loaded {len(primaries)} primary and {len(targets)} target domains.")
    print("Looping. Press Ctrl+C to stop (the run in progress is abandoned; its reports are kept).")
    run_loop(primaries, targets, llm, args.provider, args.verbose, args.max_runs)


if __name__ == "__main__":
    main()
