"""The files a run writes: their names, Markdown cleanup, headers and the README index."""

import re
from datetime import datetime
from pathlib import Path

from crewai.types.usage_metrics import UsageMetrics

# File names of the reports a run writes. Every module refers to these constants so a
# report can be renamed in one place. The numbers give the order the pipeline runs in.
PHENOMENON_REPORT = "01_phenomenon.md"
MAPPING_REPORT = "02_mapping.md"
CRITIQUE_REPORT = "03_critique.md"
BRIEF_REPORT = "03b_target_brief.md"  # the concept in target-domain language only
PITCH_REPORT = "04_pitch.md"
PITCH2_REPORT = "05_pitch2.md"  # the pitch revised from the first benchmark's feedback

REPORT_TITLES = {
    PHENOMENON_REPORT: "Phenomenon",
    MAPPING_REPORT: "Analogical Mapping",
    CRITIQUE_REPORT: "Critique",
    BRIEF_REPORT: "Target-Domain Brief",
    PITCH_REPORT: "Story Pitch (pitch)",
    PITCH2_REPORT: "Revised Story Pitch (pitch2)",
}

README_NAME = "README.md"

# A judge or reader never needs more than this much of a report.
MAX_REPORT_CHARS = 12_000

_WRAPPING_FENCE = re.compile(r"\A\s*```[a-zA-Z]*\n(.*?)\n```\s*\Z", re.DOTALL)


# Consecutive "**Field:** value" lines render as one paragraph unless a blank line separates them.
_BOLD_LINE_RUN = re.compile(r"^(\*\*.+)\n(?=\*\*)", re.MULTILINE)


def clean_markdown(raw: str) -> str:
    """Strip a wrapping code fence and separate runs of bold field lines into paragraphs."""
    match = _WRAPPING_FENCE.match(raw)
    text = (match.group(1) if match else raw).strip()
    return _BOLD_LINE_RUN.sub(r"\1\n\n", text) + "\n"


def add_header(text: str, primary: str, target: str, when: datetime) -> str:
    """Insert a one-line context blockquote under the first H1 (or at the top)."""
    line = f"> {primary} → {target} · {when:%Y-%m-%d %H:%M}\n"
    head, sep, rest = text.partition("\n")
    if head.startswith("# "):
        return f"{head}\n\n{line}\n{rest.lstrip(chr(10))}"
    return f"{line}\n{text}"


def usage_table(usage: list[tuple[str, UsageMetrics]]) -> list[str]:
    """Markdown table of token usage per step, with a total row.

    CrewAI's completion count includes reasoning tokens for Gemini, so output is
    shown net of reasoning to keep input + output + reasoning equal to the total.
    """
    rows = ["| Step | Input | Output | Reasoning | Total |", "| --- | ---: | ---: | ---: | ---: |"]
    totals = [0, 0, 0, 0]
    for label, m in usage:
        output = max(0, m.completion_tokens - m.reasoning_tokens)
        values = [m.prompt_tokens, output, m.reasoning_tokens, m.total_tokens]
        totals = [t + v for t, v in zip(totals, values)]
        rows.append(f"| {label} | " + " | ".join(f"{v:,}" for v in values) + " |")
    rows.append("| **Total** | " + " | ".join(f"**{v:,}**" for v in totals) + " |")
    return rows


def finalize_run(
    run_dir: Path,
    primary: str,
    target: str,
    when: datetime | None = None,
    usage: list[tuple[str, UsageMetrics]] | None = None,
) -> None:
    """Add context headers to each report and write a README.md index."""
    when = when or datetime.now()
    found = []
    for name, title in REPORT_TITLES.items():
        path = run_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(add_header(text, primary, target, when), encoding="utf-8")
        found.append((name, title))

    index = [f"# {primary} → {target}", "", f"Generated {when:%Y-%m-%d %H:%M}.", ""]
    index += [f"- [{title}]({name})" for name, title in found]
    if usage:
        index += ["", "## Token usage", ""] + usage_table(usage)
    (run_dir / README_NAME).write_text("\n".join(index) + "\n", encoding="utf-8")


def read_report(run_dir: Path, name: str, limit: int = MAX_REPORT_CHARS) -> str:
    """A report's text without its context header, cut to `limit` characters.

    Returns "" if the report does not exist, so callers can test for presence.
    """
    path = run_dir / name
    if not path.exists():
        return ""
    text = re.sub(r"^> .*\n", "", path.read_text(encoding="utf-8"), count=1, flags=re.MULTILINE)
    return text[:limit]


def read_domains(run_dir: Path) -> tuple[str, str]:
    """Recover the two domains from the heading of a run's README.md ("# A → B")."""
    readme = run_dir / README_NAME
    if readme.exists():
        match = re.search(r"^# (.+?) → (.+)$", readme.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    raise ValueError(f"Cannot find the domains in {readme}; expected a '# A → B' heading.")
