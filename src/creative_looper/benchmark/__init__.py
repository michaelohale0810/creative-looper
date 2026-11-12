"""Creativity benchmark: a hostile LLM judge scores a story pitch on four criteria.

* Semantic Distance: how bold the jump between the two domains is. Judged on the
  phenomenon and the mapping, so a revised pitch reuses the first pitch's score.
* Metaphorical Density: how deeply the concept's mechanics are built into the pitch.
* Freedom from Cliche: how well the pitch avoids stock AI phrasing, corporate buzzwords
  and predictable story shapes.
* Uniqueness: how interchangeable the pitch is with other pitches. A separate adversarial
  judge call deducts points for named defects, and rule-based red flags (`redflags.py`)
  each cost a further point. The judge also records trope, twist and critique data that
  is reported but not part of the index.

The Creativity Index (out of 40) is the sum of the four scores.

Modules: `prompts` (the judge's instructions), `judge` (calling it and parsing replies),
`results` (the data model), `scoring` (the orchestration) and `render` (reports and files).
"""

from creative_looper.benchmark.judge import JudgeUnavailable, ask_judge, parse_judgement
from creative_looper.benchmark.render import (
    add_readme_summary,
    benchmark_files,
    feedback_text,
    render_markdown,
    save_benchmark,
)
from creative_looper.benchmark.results import (
    BenchmarkResult,
    Criterion,
    UniquenessDetail,
    ground_cliches,
    to_criterion,
    to_uniqueness_detail,
)
from creative_looper.benchmark.scoring import benchmark_run, final_uniqueness, run_benchmark

__all__ = [
    "BenchmarkResult",
    "Criterion",
    "JudgeUnavailable",
    "UniquenessDetail",
    "add_readme_summary",
    "ask_judge",
    "benchmark_files",
    "benchmark_run",
    "feedback_text",
    "final_uniqueness",
    "ground_cliches",
    "parse_judgement",
    "render_markdown",
    "run_benchmark",
    "save_benchmark",
    "to_criterion",
    "to_uniqueness_detail",
]
