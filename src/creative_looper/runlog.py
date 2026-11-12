"""The CSV log: one row per run, appended to output/runs.csv.

It records when each run happened, the two domains, how it ended, and every score of the
pitch and of pitch2, so runs can be compared in a spreadsheet.
"""

import csv
from datetime import datetime
from pathlib import Path

from creative_looper.benchmark import BenchmarkResult, benchmark_files
from creative_looper.observability import logger
from creative_looper.report import PITCH2_REPORT, PITCH_REPORT, read_report

CSV_NAME = "runs.csv"

# The scores recorded for each pitch, in column order: (column suffix, how to read it).
_SCORES = [
    ("index", lambda r: r.index),
    ("semantic_distance", lambda r: r.semantic_distance.score),
    ("metaphorical_density", lambda r: r.metaphorical_density.score),
    ("freedom_from_cliche", lambda r: r.freedom_from_cliche.score),
    ("uniqueness", lambda r: r.uniqueness.score),
    ("core_premise_novelty", lambda r: r.uniqueness_detail.premise_novelty),
    ("twist_execution", lambda r: r.uniqueness_detail.twist_execution),
    ("truly_unique", lambda r: r.truly_unique),
    ("red_flags", lambda r: len(r.red_flags)),
    ("red_flag_penalty", lambda r: r.uniqueness_penalty),
]

COLUMNS = (
    ["started_at", "finished_at", "primary_domain", "target_domain", "status", "error",
     "run_folder", "model", "judge_model", "pitch_title", "pitch2_title"]
    + [f"pitch_{name}" for name, _ in _SCORES]
    + [f"pitch2_{name}" for name, _ in _SCORES]
    + ["index_change", "benchmark_file", "benchmark2_file"]
)


def _title(run_dir: Path, report: str) -> str:
    """The novel title (the pitch's first heading), or "" if the pitch was not written."""
    for line in read_report(run_dir, report).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def build_row(
    *,
    primary: str,
    target: str,
    started: datetime,
    finished: datetime,
    status: str,
    error: str,
    run_dir: Path,
    model: str,
    first: BenchmarkResult | None,
    second: BenchmarkResult | None,
) -> dict[str, object]:
    """One CSV row. Anything the run never got to (a cancelled or failed run) is left blank.

    `status` is complete, cancelled (Ctrl+C) or failed.
    """
    row: dict[str, object] = {
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "primary_domain": primary,
        "target_domain": target,
        "status": status,
        "error": " ".join(error.split()),
        "run_folder": run_dir.name,
        "model": model,
        "judge_model": (first or second).judge_model if (first or second) else "",
        "pitch_title": _title(run_dir, PITCH_REPORT),
        "pitch2_title": _title(run_dir, PITCH2_REPORT),
        "index_change": "",  # filled in below when both pitches were scored
        "benchmark_file": f"{run_dir.name}/{benchmark_files('')[0]}" if first else "",
        "benchmark2_file": f"{run_dir.name}/{benchmark_files('2')[0]}" if second else "",
    }
    for prefix, result in (("pitch", first), ("pitch2", second)):
        for name, read in _SCORES:
            row[f"{prefix}_{name}"] = "" if result is None or read(result) is None else read(result)
    if first and second and first.index is not None and second.index is not None:
        row["index_change"] = second.index - first.index
    return row


def append_row(csv_path: Path, row: dict[str, object]) -> None:
    """Append `row` to the CSV, writing the header first if the file is new.

    If an existing file has different columns (this code changed since it was written),
    it is renamed aside rather than mixed with rows of another shape.
    """
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f), [])
        if header != COLUMNS:
            aside = csv_path.with_name(f"{csv_path.stem}_{datetime.now():%Y%m%d_%H%M%S}.csv")
            csv_path.rename(aside)
            logger.warning("%s had different columns; moved it to %s", csv_path.name, aside.name)
    is_new = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
        if is_new:
            writer.writeheader()
        writer.writerow(row)
