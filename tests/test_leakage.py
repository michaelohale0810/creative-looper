from creative_looper.leakage import count_domain_mentions, domain_pattern


def test_domain_pattern_matches_word_variants_only():
    pattern = domain_pattern("Geology")
    assert len(pattern.findall("Geology and geological strata, geologists")) == 3
    assert not pattern.findall("jazz and music")


def test_domain_pattern_handles_multiword_domains():
    pattern = domain_pattern("Quantum Physics")
    assert len(pattern.findall("quantum tunnelling and physical laws")) == 2


def test_short_words_alone_match_nothing():
    assert not domain_pattern("AI").findall("AI and ai")


def test_count_domain_mentions_skips_missing_reports(tmp_path):
    (tmp_path / "04_pitch.md").write_text("Geology Geology jazz")
    counts = count_domain_mentions(tmp_path, "Geology", ["04_pitch.md", "03_critique.md"])
    assert counts == {"04_pitch.md": 2}
