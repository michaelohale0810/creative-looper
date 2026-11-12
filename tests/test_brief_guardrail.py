from types import SimpleNamespace

from creative_looper.brief_guardrail import MAX_BRIEF_REWRITES, foreign_terms, make_guardrail


class FakeLLM:
    def __init__(self, reply="NONE"):
        self.reply = reply

    def call(self, _prompt):
        return self.reply


def draft(text):
    return SimpleNamespace(raw=text)  # the guardrail only reads `.raw`


def test_foreign_terms_parses_the_list_and_none():
    assert foreign_terms("x", "Biology", "Politics", FakeLLM("redox, `catalyst`, 'enzyme'.")) == ["redox", "catalyst", "enzyme"]
    assert foreign_terms("x", "Biology", "Politics", FakeLLM("NONE")) == []
    assert foreign_terms("x", "Biology", "Politics", FakeLLM("  ")) == []


def test_clean_draft_is_accepted():
    ok, output = make_guardrail("Geology", "Jazz", FakeLLM("NONE"))(draft("A quartet trades fours."))
    assert ok and output.raw == "A quartet trades fours."


def test_draft_naming_the_primary_domain_is_sent_back_with_the_terms():
    ok, feedback = make_guardrail("Geology", "Jazz", FakeLLM("NONE"))(draft("Geological strata of sound"))
    assert not ok and "geolo" in feedback.lower() and "Jazz" in feedback


def test_model_flagged_jargon_is_sent_back():
    ok, feedback = make_guardrail("Geology", "Jazz", FakeLLM("sediment"))(draft("A quiet room"))
    assert not ok and "sediment" in feedback


def test_it_gives_up_gracefully_after_the_allowed_rewrites():
    guardrail = make_guardrail("Geology", "Jazz", FakeLLM("sediment"))
    results = [guardrail(draft("x"))[0] for _ in range(MAX_BRIEF_REWRITES + 1)]
    assert results == [False] * MAX_BRIEF_REWRITES + [True]
