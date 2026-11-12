from creative_looper.redflags import MAX_PENALTY, penalty, pitch_body, proper_nouns, red_flags

GENERIC_PITCH = """# The Withdrawal Protocol

*Political Thriller, Adult Fiction, 90,000 words*

What happens when the weight of disputes becomes too much? Elias Thorne is a senior advisor
who must navigate the crisis. The most dangerous forces are not external.

*For readers of The West Wing, and Station Eleven*
"""

SPECIFIC_PITCH = """# Salt for the Tide Clerk

*Literary fantasy, adult, 85,000 words*

Odile Marchetti has stamped tide tables at the harbor of Port Vellam for thirty years, until
the morning the Admiralty Court of Brennick orders every clock in the Lantern District
stopped. Her brother Teodor smuggles pocket watches through the Cinder Gate in loaves of bread.

*For readers of Piranesi and The Goblin Emperor*
"""


def test_generic_pitch_collects_flags():
    text = " ".join(red_flags(GENERIC_PITCH))
    assert "stock pitch phrasing" in text
    assert "elias" in text and "thorne" in text
    assert "west wing" in text
    assert "abstract" in text


def test_specific_pitch_is_clean():
    assert red_flags(SPECIFIC_PITCH) == []


def test_copying_the_brief_is_flagged():
    prose = "The harbor clerk stamps every tide table before the court orders all clocks stopped now."
    flags = red_flags(f"# T\n\n{prose} Odile Marchetti, Brennick, Lantern, Teodor.\n", prose)
    assert any("copied from the brief" in f for f in flags)


def test_penalty_is_capped():
    assert penalty([]) == 0
    assert penalty(["a"] * 10) == MAX_PENALTY


def test_pitch_body_splits_title_prose_and_comps():
    title, prose, comps = pitch_body(SPECIFIC_PITCH)
    assert title == "Salt for the Tide Clerk"
    assert "Odile" in prose and "Piranesi" not in prose
    assert "Piranesi" in comps


def test_the_ending_paragraph_counts_as_prose_but_the_comps_line_does_not():
    pitch = SPECIFIC_PITCH.replace(
        "\n*For readers", "\n**The ending:** Elias Thorne burns the ledger.\n\n*For readers"
    )
    _, prose, comps = pitch_body(pitch)
    assert "burns the ledger" in prose and "Piranesi" not in prose
    assert any("elias" in f for f in red_flags(pitch))


def test_proper_nouns_ignore_sentence_starts():
    assert proper_nouns("The clerk met Odile in Brennick. Then left.") == {"odile", "brennick"}
