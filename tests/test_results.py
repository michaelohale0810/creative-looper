from helpers import make_result

from creative_looper.benchmark import Criterion, ground_cliches, to_criterion, to_uniqueness_detail


def test_scores_are_clamped_and_rounded():
    assert to_criterion({"score": 14}).score == 10
    assert to_criterion({"score": 0}).score == 1
    assert to_criterion({"score": "6.6", "evidence": " x "}) == Criterion(7, "x", [])


def test_missing_or_garbled_score_is_none():
    assert to_criterion(None).score is None
    assert to_criterion({"evidence": "no score"}).score is None
    assert to_criterion({"score": "high"}).score is None


def test_creativity_index_is_the_sum_of_the_four_scores():
    assert make_result(md=6, cf=4, distance=7, uq=3).index == 20.0


def test_any_unjudged_criterion_voids_the_index():
    for field in ("semantic_distance", "metaphorical_density", "freedom_from_cliche", "uniqueness"):
        result = make_result()
        setattr(result, field, Criterion(None, "failed"))
        assert result.index is None


def test_truly_unique_is_decided_by_the_final_score_not_the_model():
    assert not make_result(uq=8).truly_unique
    assert make_result(uq=9).truly_unique
    result = make_result(uq=9)
    result.uniqueness = Criterion(None, "failed")
    assert not result.truly_unique


def test_uniqueness_detail_is_read_and_clamped():
    d = to_uniqueness_detail({
        "trope_checklist": ["chosen one", "the twist is the AI"],
        "core_premise_novelty": 12, "twist_execution_score": "3", "harsh_critique": " bad ",
    })
    assert d.tropes == ["chosen one", "the twist is the AI"]
    assert (d.premise_novelty, d.twist_execution, d.critique) == (10, 3, "bad")
    assert to_uniqueness_detail(None).premise_novelty is None


def test_cliche_quotes_must_appear_in_the_piece():
    piece = "A real-time Dashboard for the board. Synergy is promised."
    quotes = ["dashboard", "Real-Time", "seamless", "ecosystem", "  "]
    assert ground_cliches(quotes, piece) == ["dashboard", "Real-Time"]
