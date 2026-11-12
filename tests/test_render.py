import json

from helpers import make_result

from creative_looper.benchmark import (
    add_readme_summary,
    benchmark_files,
    feedback_text,
    render_markdown,
    save_benchmark,
    to_uniqueness_detail,
)


def with_detail(result, **raw):
    result.uniqueness_detail = to_uniqueness_detail(raw)
    return result


def test_markdown_report_lists_scores_and_cliches():
    text = render_markdown(make_result(), "Judging used 10 input tokens.")
    assert "**Creativity Index: 20 / 40**" in text
    assert "The West Wing: politics" in text
    assert "### Story Pitch" in text
    assert "“neon-soaked sprawl”" in text
    assert "Judging used 10 input tokens." in text


def test_save_writes_files_and_replaces_the_readme_section(tmp_path):
    (tmp_path / "README.md").write_text("# Geology → Jazz\n\nGenerated.\n")
    for result in (make_result(), make_result(distance=9)):  # re-scoring must not duplicate
        save_benchmark(tmp_path, result, "")
        add_readme_summary(tmp_path, result)
    readme = (tmp_path / "README.md").read_text()
    assert readme.count("## Creativity benchmark") == 1
    assert "22 / 40" in readme
    data = json.loads((tmp_path / "creativity_benchmark.json").read_text())
    assert data["creativity_index"] == 22.0
    assert (data["metaphorical_density"], data["freedom_from_cliche"], data["uniqueness"]) == (6, 4, 3)
    assert (tmp_path / "creativity_benchmark.md").exists()


def test_second_benchmark_has_its_own_files_and_readme_section(tmp_path):
    (tmp_path / "README.md").write_text("# A → B\n")
    for result, tag in ((make_result(), ""), (make_result(uq=6), "2")):
        save_benchmark(tmp_path, result, "", tag)
        add_readme_summary(tmp_path, result, tag)
    add_readme_summary(tmp_path, make_result(uq=7), "2")  # replaces only its own section
    assert benchmark_files("2") == ("creativity_benchmark2.md", "creativity_benchmark2.json")
    assert (tmp_path / "creativity_benchmark.md").exists() and (tmp_path / "creativity_benchmark2.md").exists()
    assert json.loads((tmp_path / "creativity_benchmark2.json").read_text())["uniqueness"] == 6
    readme = (tmp_path / "README.md").read_text()
    assert readme.count("## Creativity benchmark\n") == 1 and readme.count("## Creativity benchmark 2\n") == 1
    assert "20 / 40" in readme and "24 / 40" in readme  # first untouched; second replaced (7+6+4+7)
    assert "# Creativity Benchmark 2: Geology → Jazz" in (tmp_path / "creativity_benchmark2.md").read_text()


def test_readme_summary_does_nothing_without_a_readme(tmp_path):
    add_readme_summary(tmp_path, make_result())
    assert not (tmp_path / "README.md").exists()


def test_trope_and_twist_data_reach_the_markdown_and_json(tmp_path):
    result = with_detail(
        make_result(), trope_checklist=["chosen one"], core_premise_novelty=3,
        twist_execution_score=2, harsh_critique="derivative",
    )
    text = render_markdown(result)
    assert "**Trope checklist:** chosen one" in text and "**Harsh critique:** derivative" in text
    assert "Core premise novelty:** 3/10" in text
    save_benchmark(tmp_path, result)
    data = json.loads((tmp_path / "creativity_benchmark.json").read_text())
    assert data["trope_checklist"] == ["chosen one"] and data["truly_unique"] is False
    assert data["twist_execution_score"] == 2


def test_feedback_for_the_reviser_has_findings_but_no_bookkeeping():
    result = with_detail(make_result(), trope_checklist=["chosen one"], harsh_critique="derivative")
    text = feedback_text(result)
    assert "chosen one" in text and "derivative" in text and "neon-soaked sprawl" in text
    assert "About these scores" not in text and "Judge model" not in text
