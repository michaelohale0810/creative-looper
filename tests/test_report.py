from datetime import datetime

import pytest
from crewai.types.usage_metrics import UsageMetrics

from creative_looper.report import (
    PITCH2_REPORT,
    PITCH_REPORT,
    REPORT_TITLES,
    add_header,
    clean_markdown,
    finalize_run,
    read_domains,
    read_report,
    usage_table,
)

WHEN = datetime(2026, 10, 25, 14, 30)


def test_strips_wrapping_fence():
    assert clean_markdown("```markdown\n# Title\n\nBody\n```") == "# Title\n\nBody\n"


def test_keeps_inner_code_blocks():
    text = "# T\n\n```py\nx = 1\n```\n\nmore"
    assert clean_markdown(text) == text + "\n"


def test_bold_field_lines_become_separate_paragraphs():
    raw = "## C\n**Genre:** Noir\n**Logline:** Rain.\n**Setting:** City\n\nplain"
    assert clean_markdown(raw) == "## C\n**Genre:** Noir\n\n**Logline:** Rain.\n\n**Setting:** City\n\nplain\n"


def test_bullet_fields_are_left_alone():
    raw = "- **Concept:** x\n- **Risk:** y"
    assert clean_markdown(raw) == raw + "\n"


def test_header_goes_under_title():
    out = add_header("# Title\n\n## Section\n", "Biology", "Politics", WHEN)
    assert out == "# Title\n\n> Biology → Politics · 2026-10-25 14:30\n\n## Section\n"


def test_header_without_title():
    out = add_header("Just text\n", "A", "B", WHEN)
    assert out.startswith("> A → B · 2026-10-25 14:30\n\nJust text")


def test_finalize_writes_index_for_existing_reports(tmp_path):
    (tmp_path / "01_phenomenon.md").write_text("# P\n\nx\n")
    (tmp_path / "03_critique.md").write_text("# C\n\ny\n")
    finalize_run(tmp_path, "Biology", "Politics", WHEN)
    index = (tmp_path / "README.md").read_text()
    assert "[Phenomenon](01_phenomenon.md)" in index
    assert "[Critique](03_critique.md)" in index
    assert "02_mapping.md" not in index
    assert "> Biology → Politics" in (tmp_path / "01_phenomenon.md").read_text()


def test_usage_table_separates_reasoning_and_totals():
    usage = [
        ("Exploring", UsageMetrics(prompt_tokens=100, completion_tokens=70, reasoning_tokens=20, total_tokens=170)),
        ("Mapping", UsageMetrics(prompt_tokens=1000, completion_tokens=500, reasoning_tokens=0, total_tokens=1500)),
    ]
    table = "\n".join(usage_table(usage))
    assert "| Exploring | 100 | 50 | 20 | 170 |" in table
    assert "| Mapping | 1,000 | 500 | 0 | 1,500 |" in table
    assert "| **Total** | **1,100** | **550** | **20** | **1,670** |" in table


def test_finalize_adds_usage_section(tmp_path):
    (tmp_path / "01_phenomenon.md").write_text("# P\n")
    usage = [("Exploring", UsageMetrics(prompt_tokens=1, completion_tokens=1, total_tokens=2))]
    finalize_run(tmp_path, "A", "B", WHEN, usage=usage)
    assert "## Token usage" in (tmp_path / "README.md").read_text()


def test_the_run_has_a_pitch_and_a_revised_pitch2():
    assert PITCH_REPORT == "04_pitch.md" and PITCH2_REPORT == "05_pitch2.md"
    assert "pitch2" in REPORT_TITLES[PITCH2_REPORT]


def test_finalize_indexes_both_pitches(tmp_path):
    for name in (PITCH_REPORT, PITCH2_REPORT):
        (tmp_path / name).write_text("# Novel\n\ntext\n")
    finalize_run(tmp_path, "A", "B", WHEN)
    index = (tmp_path / "README.md").read_text()
    assert f"({PITCH_REPORT})" in index and f"({PITCH2_REPORT})" in index


def test_read_report_drops_the_header_and_truncates(tmp_path):
    (tmp_path / "a.md").write_text("# T\n\n> A → B · 2026-01-01 10:00\n\nbody text\n")
    assert "A → B" not in read_report(tmp_path, "a.md")
    assert read_report(tmp_path, "a.md", limit=3) == "# T"
    assert read_report(tmp_path, "missing.md") == ""


def test_domains_are_read_from_the_run_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Quantum Physics → Macroeconomics\n\nGenerated.\n")
    assert read_domains(tmp_path) == ("Quantum Physics", "Macroeconomics")
    with pytest.raises(ValueError):
        read_domains(tmp_path / "missing")
