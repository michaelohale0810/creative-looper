"""Presenting a benchmark: the Markdown report, the JSON data, the README summary and the
feedback text handed to the pitch reviser."""

import json
import re
from pathlib import Path

from creative_looper.benchmark.results import UNIQUE_THRESHOLD, BenchmarkResult
from creative_looper.report import README_NAME, REPORT_TITLES

SECTION_HEADING = "## Creativity benchmark"  # in the run README; the second one adds " 2"
ABOUT_HEADING = "## About these scores"


def fmt(value: float | int | None) -> str:
    return "n/a" if value is None else f"{value:g}"


def benchmark_files(tag: str = "") -> tuple[str, str]:
    """File names of a benchmark's report and data: tag "" is the first, "2" the second."""
    return f"creativity_benchmark{tag}.md", f"creativity_benchmark{tag}.json"


def _summary_table(result: BenchmarkResult) -> list[str]:
    return [
        f"**Creativity Index: {fmt(result.index)} / 40**",
        "",
        "| Criterion | Score | Basis |",
        "| --- | ---: | --- |",
        f"| Semantic Distance | {fmt(result.semantic_distance.score)} | the phenomenon and mapping |",
        f"| Metaphorical Density | {fmt(result.metaphorical_density.score)} | the story pitch |",
        f"| Freedom from Cliché | {fmt(result.freedom_from_cliche.score)} | the story pitch |",
        f"| Uniqueness | {fmt(result.uniqueness.score)} | the story pitch, after red-flag penalty |",
        "",
        f"Semantic Distance: {result.semantic_distance.evidence}",
        "",
    ]


def _judges_notes(result: BenchmarkResult) -> list[str]:
    """The judge's reasoning for the pitch: evidence, resemblances, tropes, critique."""
    density, cliche, unique = result.metaphorical_density, result.freedom_from_cliche, result.uniqueness
    detail = result.uniqueness_detail
    lines = [
        "## Judge's notes",
        "",
        f"### {REPORT_TITLES[result.pitch]}",
        f"- **Metaphorical Density ({fmt(density.score)}):** {density.evidence}",
        f"- **Freedom from Cliché ({fmt(cliche.score)}):** {cliche.evidence}",
        f"- **Uniqueness ({fmt(unique.score)}):** {unique.evidence}",
    ]
    if cliche.cliches:
        lines.append("- **Clichés found:** " + "; ".join(f"“{c}”" for c in cliche.cliches))
    if unique.similar:
        lines.append("- **Resembles:** " + "; ".join(unique.similar))
    lines.append(
        f"- **Core premise novelty:** {fmt(detail.premise_novelty)}/10 · "
        f"**Twist execution:** {fmt(detail.twist_execution)}/10 · "
        f"**Truly unique (final uniqueness ≥ {UNIQUE_THRESHOLD:g}):** {'yes' if result.truly_unique else 'no'}"
    )
    if detail.tropes:
        lines.append("- **Trope checklist:** " + "; ".join(detail.tropes))
    if detail.critique:
        lines += ["", f"**Harsh critique:** {detail.critique}"]
    weaknesses = [w for c in (density, cliche, unique) for w in c.weaknesses]
    if weaknesses:
        lines += ["", "**Weaknesses the judge listed:**"] + [f"- {w}" for w in weaknesses]
    lines.append("")

    if result.red_flags:
        lines += [
            "### Rule-based red flags",
            f"Each flag took a point off Uniqueness (total penalty {result.uniqueness_penalty}).",
            "",
            *[f"- {flag}" for flag in result.red_flags],
            "",
        ]
    return lines


def render_markdown(result: BenchmarkResult, usage_line: str = "", tag: str = "") -> str:
    """The full benchmark report as Markdown."""
    lines = [
        f"# Creativity Benchmark{' ' + tag if tag else ''}: {result.primary} → {result.target}",
        "",
        *_summary_table(result),
        *_judges_notes(result),
        ABOUT_HEADING,
        "",
        f"Judge model: `{result.judge_model}`. {usage_line}".strip(),
        "",
        "An LLM judge is noisy and tends to favor its own style, so compare scores only "
        "between runs scored by the same judge model, and treat differences of a point or "
        "so as noise.",
        "",
    ]
    return "\n".join(lines)


def save_benchmark(run_dir: Path, result: BenchmarkResult, usage_line: str = "", tag: str = "") -> Path:
    """Write creativity_benchmark[tag].md and .json; returns the Markdown path."""
    md_name, json_name = benchmark_files(tag)
    md_path = run_dir / md_name
    md_path.write_text(render_markdown(result, usage_line, tag), encoding="utf-8")

    detail = result.uniqueness_detail
    payload = {
        "primary": result.primary,
        "target": result.target,
        "judge_model": result.judge_model,
        "pitch": result.pitch,
        "creativity_index": result.index,
        "semantic_distance": result.semantic_distance.score,
        "metaphorical_density": result.metaphorical_density.score,
        "freedom_from_cliche": result.freedom_from_cliche.score,
        "uniqueness": result.uniqueness.score,
        "truly_unique": result.truly_unique,
        "core_premise_novelty": detail.premise_novelty,
        "twist_execution_score": detail.twist_execution,
        "trope_checklist": detail.tropes,
        "harsh_critique": detail.critique,
        "red_flags": result.red_flags,
        "uniqueness_penalty": result.uniqueness_penalty,
    }
    (run_dir / json_name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return md_path


def add_readme_summary(run_dir: Path, result: BenchmarkResult, tag: str = "") -> None:
    """Add (or replace) this benchmark's summary section in the run's README.md.

    Each benchmark owns one section, so re-scoring replaces it without touching the other.
    """
    readme = run_dir / README_NAME
    if not readme.exists():
        return
    heading = f"{SECTION_HEADING} {tag}".strip()
    # Drop this section only: it runs to the next "## " heading or the end of the file.
    text = re.sub(
        rf"\n*^{re.escape(heading)}\n.*?(?=^## |\Z)",
        "\n",
        readme.read_text(encoding="utf-8"),
        flags=re.S | re.M,
    )
    report = benchmark_files(tag)[0]
    text = text.rstrip() + "\n" + (
        f"\n{heading}\n\n"
        f"**Creativity Index: {fmt(result.index)} / 40** "
        f"(semantic distance {fmt(result.semantic_distance.score)}, "
        f"metaphorical density {fmt(result.metaphorical_density.score)}, "
        f"freedom from cliché {fmt(result.freedom_from_cliche.score)}, "
        f"uniqueness {fmt(result.uniqueness.score)}). "
        f"Details: [{report}]({report}).\n"
    )
    readme.write_text(text, encoding="utf-8")


def feedback_text(result: BenchmarkResult) -> str:
    """The benchmark's findings as notes for the pitch reviser (no run bookkeeping)."""
    return render_markdown(result).split(ABOUT_HEADING)[0].strip()
