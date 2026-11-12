"""The benchmark's data model, and turning the judge's JSON into it."""

from dataclasses import dataclass, field

from creative_looper.observability import logger

# A pitch counts as "truly unique" only at or above this final uniqueness score.
UNIQUE_THRESHOLD = 8.5


@dataclass
class Criterion:
    """One 1-10 score with the judge's reasoning. `score` is None if it could not be judged."""

    score: int | None
    evidence: str = ""
    cliches: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    similar: list[str] = field(default_factory=list)  # real works a pitch resembles


@dataclass
class UniquenessDetail:
    """Extra data from the uniqueness judge, recorded but not part of the index."""

    tropes: list[str] = field(default_factory=list)
    premise_novelty: int | None = None
    twist_execution: int | None = None
    critique: str = ""


@dataclass
class BenchmarkResult:
    """The scores for one pitch.

    The Creativity Index is the sum of the four criteria, out of 40.
    """

    primary: str
    target: str
    judge_model: str
    pitch: str  # name of the report that was scored
    semantic_distance: Criterion  # rates the phenomenon and mapping, not the pitch
    metaphorical_density: Criterion
    freedom_from_cliche: Criterion
    uniqueness: Criterion
    uniqueness_detail: UniquenessDetail = field(default_factory=UniquenessDetail)
    red_flags: list[str] = field(default_factory=list)
    uniqueness_penalty: int = 0  # points the red flags took off the judge's uniqueness score

    @property
    def criteria(self) -> list[Criterion]:
        return [
            self.semantic_distance,
            self.metaphorical_density,
            self.freedom_from_cliche,
            self.uniqueness,
        ]

    @property
    def index(self) -> float | None:
        """Sum of the four scores, or None if any of them could not be judged."""
        scores = [c.score for c in self.criteria]
        return None if None in scores else float(sum(scores))

    @property
    def truly_unique(self) -> bool:
        """Decided here, not by the model: the final uniqueness score must reach the threshold."""
        score = self.uniqueness.score
        return score is not None and score >= UNIQUE_THRESHOLD


def to_criterion(raw: object) -> Criterion:
    """Turn one criterion's JSON into a Criterion with a score clamped to 1-10."""
    if not isinstance(raw, dict):
        return Criterion(None, "judge reply was missing this criterion")
    try:
        score = max(1, min(10, round(float(raw["score"]))))
    except (KeyError, TypeError, ValueError):
        return Criterion(None, "judge gave no usable score")

    def strings(key: str, limit: int) -> list[str]:
        value = raw.get(key) or []
        return [str(v) for v in value][:limit] if isinstance(value, list) else []

    return Criterion(
        score,
        str(raw.get("evidence", "")).strip(),
        strings("cliches_found", 8),
        strings("weaknesses", 6),
        strings("closest_existing_works", 3),
    )


def to_uniqueness_detail(raw: object) -> UniquenessDetail:
    """Read the trope list, sub-scores and critique from the uniqueness reply."""
    if not isinstance(raw, dict):
        return UniquenessDetail()
    tropes = raw.get("trope_checklist")

    def sub(key: str) -> int | None:
        return to_criterion({"score": raw.get(key)}).score

    return UniquenessDetail(
        [str(t) for t in tropes][:15] if isinstance(tropes, list) else [],
        sub("core_premise_novelty"),
        sub("twist_execution_score"),
        str(raw.get("harsh_critique", "")).strip(),
    )


def ground_cliches(cliches: list[str], piece: str) -> list[str]:
    """Keep only the quoted cliches that really occur in the piece (case-insensitive).

    The judge sometimes echoes the example words from its own instructions, so every
    quote is checked against the text.
    """
    text = piece.lower()
    kept = [c for c in cliches if c.strip().lower() and c.strip().lower() in text]
    if len(kept) < len(cliches):
        logger.info("dropped %d cliche quote(s) not found in the text", len(cliches) - len(kept))
    return kept
