import random

import pytest

from creative_looper.domains import load_domains, pick_pair


def write(tmp_path, text):
    path = tmp_path / "list.txt"
    path.write_text(text, encoding="utf-8")
    return path


def test_blank_lines_comments_and_duplicates_are_skipped_keeping_order(tmp_path):
    path = write(tmp_path, "# a comment\nGeology\n\n  Jazz  \ngeology\n# more\nQuantum Physics\n")
    assert load_domains(path) == ["Geology", "Jazz", "Quantum Physics"]


def test_an_unusable_line_is_reported_with_its_line_number(tmp_path):
    with pytest.raises(ValueError, match=r"line 3.*'!!!'"):
        load_domains(write(tmp_path, "Geology\n\n!!!\n"))


def test_empty_and_missing_files_are_clear_errors(tmp_path):
    with pytest.raises(ValueError, match="lists no domains"):
        load_domains(write(tmp_path, "# only comments\n\n"))
    with pytest.raises(ValueError, match="Cannot read"):
        load_domains(tmp_path / "missing.txt")


def test_pick_pair_is_reproducible_with_a_seed_and_never_pairs_a_domain_with_itself():
    primaries, targets = ["A", "B", "C"], ["a", "B", "D"]
    pairs = [pick_pair(primaries, targets, random.Random(1)) for _ in range(3)]
    assert pairs[0] == pairs[1] == pairs[2]
    rng = random.Random(7)
    for _ in range(200):
        primary, target = pick_pair(primaries, targets, rng)
        assert primary.casefold() != target.casefold()


def test_pick_pair_gives_up_when_only_one_domain_is_on_offer():
    with pytest.raises(ValueError, match="same domain"):
        pick_pair(["Jazz"], ["jazz"])
