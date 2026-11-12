import csv
from datetime import datetime

from helpers import make_result

from creative_looper.report import PITCH_REPORT
from creative_looper.runlog import COLUMNS, append_row, build_row

WHEN = datetime(2026, 11, 11, 10, 0, 0)


def row_for(run_dir, **overrides):
    args = dict(
        primary="Geology", target="Jazz", started=WHEN, finished=WHEN, status="complete",
        error="", run_dir=run_dir, model="m", first=make_result(), second=make_result(uq=6),
    )
    args.update(overrides)
    return build_row(**args)


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_row_records_domains_scores_titles_and_the_change(tmp_path):
    run_dir = tmp_path / "Geology_Jazz_20261111_100000"
    run_dir.mkdir()
    (run_dir / PITCH_REPORT).write_text("# The Salt Line\n\nbody\n")
    row = row_for(run_dir)
    assert set(row) == set(COLUMNS)
    assert (row["primary_domain"], row["target_domain"], row["status"]) == ("Geology", "Jazz", "complete")
    assert row["started_at"] == "2026-11-11T10:00:00" and row["pitch_title"] == "The Salt Line"
    assert row["pitch_index"] == 20.0 and row["pitch2_index"] == 23.0 and row["index_change"] == 3.0
    assert row["pitch_uniqueness"] == 3 and row["pitch2_uniqueness"] == 6
    assert row["benchmark_file"].endswith("creativity_benchmark.md")
    assert row["benchmark2_file"].endswith("creativity_benchmark2.md")


def test_a_stopped_or_failed_run_leaves_unreached_columns_blank(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    row = row_for(run_dir, status="failed", error="model\ndown", second=None)
    assert set(row) == set(COLUMNS)
    assert row["error"] == "model down" and row["pitch2_index"] == "" and row["index_change"] == ""
    assert row["benchmark2_file"] == "" and row["pitch_index"] == 20.0
    empty = row_for(run_dir, first=None, second=None)
    assert empty["pitch_index"] == "" and empty["judge_model"] == ""


def test_rows_are_appended_under_one_header(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    path = tmp_path / "runs.csv"
    append_row(path, row_for(run_dir))
    append_row(path, row_for(run_dir, primary="Mycology"))
    rows = read_rows(path)
    assert [r["primary_domain"] for r in rows] == ["Geology", "Mycology"]
    assert path.read_text().count("started_at") == 1


def test_a_file_with_other_columns_is_moved_aside_not_mixed(tmp_path):
    run_dir = tmp_path / "r"
    run_dir.mkdir()
    path = tmp_path / "runs.csv"
    path.write_text("old,columns\n1,2\n")
    append_row(path, row_for(run_dir))
    assert len(read_rows(path)) == 1
    moved = [p for p in tmp_path.glob("runs_*.csv")]
    assert len(moved) == 1 and moved[0].read_text() == "old,columns\n1,2\n"
