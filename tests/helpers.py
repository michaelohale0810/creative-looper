"""Shared fakes and builders for the benchmark and pipeline tests."""

from creative_looper.benchmark import BenchmarkResult, Criterion
from creative_looper.report import (
    BRIEF_REPORT,
    MAPPING_REPORT,
    PHENOMENON_REPORT,
    PITCH_REPORT,
)

# Canned judge replies.
DISTANCE = '{"semantic_distance": {"score": 7, "evidence": "e"}}'
GOOD_REPORT = (
    '{"metaphorical_density": {"score": 6, "evidence": "e"},'
    ' "freedom_from_cliche": {"score": 5, "evidence": "e", "cliches_found": []}}'
)
UNIQUE = '{"uniqueness": {"score": 6, "evidence": "e", "closest_existing_works": []}}'


class FakeJudge:
    """Stands in for an LLM: replays a script of replies or exceptions."""

    model = "fake/judge"

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def call(self, _prompt):
        self.calls += 1
        item = self.script.pop(0) if self.script else '{"a": 1}'
        if isinstance(item, Exception):
            raise item
        return item


def make_result(md=6, cf=4, distance=7, uq=3) -> BenchmarkResult:
    """A scored pitch with the given criterion scores."""
    return BenchmarkResult(
        primary="Geology",
        target="Jazz",
        judge_model="gemini/judge",
        pitch=PITCH_REPORT,
        semantic_distance=Criterion(distance, "bold"),
        metaphorical_density=Criterion(md, "dense"),
        freedom_from_cliche=Criterion(cf, "tropey", ["neon-soaked sprawl"]),
        uniqueness=Criterion(uq, "derivative", similar=["The West Wing: politics"]),
    )


def make_run_dir(tmp_path):
    """A run folder holding the reports the benchmark reads."""
    for name in (PHENOMENON_REPORT, MAPPING_REPORT, BRIEF_REPORT, PITCH_REPORT):
        (tmp_path / name).write_text(f"# {name}\n\ntext\n")
    return tmp_path
