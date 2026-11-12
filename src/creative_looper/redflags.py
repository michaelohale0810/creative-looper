"""Rule-based checks on a story pitch that a model judge cannot talk itself out of.

Each flag is a short sentence naming a concrete, verifiable weakness. They are shown to
the uniqueness judge and each one lowers the uniqueness score (see PENALTY_PER_FLAG).
"""

import re

PENALTY_PER_FLAG = 1
MAX_PENALTY = 3

# Phrasing that marks a pitch as machine-written boilerplate.
STOCK_PHRASES = [
    "what happens when", "in a world where", "the world believes", "race against time",
    "ticking clock", "must navigate", "not external", "the most dangerous", "unpredictable nature",
    "delve", "tapestry", "testament to", "symphony of", "dance of", "web of lies",
    "nothing is as it seems", "will stop at nothing", "changes everything", "irreversible",
    "profound", "moment of reckoning", "no one is safe", "a chance to reorient", "what remains of",
    "complex cycle", "calculated", "the question that", "forced to confront",
]

# Names and surnames language models reach for again and again.
GENERIC_NAMES = [
    "elias", "elara", "elena", "kaelen", "kael", "aris", "aria", "lyra", "silas", "thorne",
    "vance", "voss", "sterling", "blackwood", "ashford", "sarah chen", "dr. chen", "marcus",
    "evelyn", "julian", "finch", "hayes", "reyes", "mercer", "sato", "rourke",
]

# Comparable titles so famous that they say nothing about this particular book.
OVERUSED_COMPS = [
    "west wing", "station eleven", "black mirror", "hunger games", "game of thrones",
    "handmaid's tale", "1984", "nineteen eighty-four", "dune", "the martian", "inception",
    "house of cards", "da vinci code", "gone girl", "ready player one", "blade runner",
]

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def proper_nouns(prose: str) -> set[str]:
    """Capitalized words that do not start a sentence: a rough count of named things."""
    found = set()
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", prose):
        for word in _WORD.findall(sentence)[1:]:
            if word[0].isupper() and len(word) > 2:
                found.add(word.lower())
    return found


def pitch_body(pitch: str) -> tuple[str, str, str]:
    """Split a pitch report into (title, prose, comps line)."""
    lines = [l for l in pitch.strip().splitlines() if l.strip() and not l.startswith("> ")]
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
    comps = next((l for l in reversed(lines) if re.search(r"for readers of", l, re.I)), "")
    # Drop the heading, the italic genre and comps lines; keep bold lines such as "**The ending:**".
    prose = [
        l for l in lines
        if not l.startswith("#") and l is not comps and not (l.startswith("*") and not l.startswith("**"))
    ]
    return title, "\n".join(prose), comps


def red_flags(pitch: str, brief: str = "") -> list[str]:
    """Concrete weaknesses found in `pitch`, compared with the `brief` it was written from."""
    title, prose, comps = pitch_body(pitch)
    flags: list[str] = []
    lowered = prose.lower()

    stock = [p for p in STOCK_PHRASES if p in lowered]
    if len(stock) >= 2:
        flags.append("stock pitch phrasing: " + ", ".join(f"“{p}”" for p in stock[:5]))

    text = f"{title} {prose}".lower()
    names = [n for n in GENERIC_NAMES if re.search(rf"\b{re.escape(n)}\b", text)]
    if names:
        flags.append("generic AI-favorite name(s): " + ", ".join(names[:4]))

    comp_hits = [c for c in OVERUSED_COMPS if c in comps.lower()]
    if comp_hits:
        flags.append("comparable titles too famous to be informative: " + ", ".join(comp_hits))

    words = _words(prose)
    nouns = proper_nouns(prose)
    if words and len(nouns) < 4:
        flags.append(
            f"abstract: only {len(nouns)} named person(s), place(s) or thing(s) in the prose, "
            "so the premise is stated as concepts rather than shown through particulars"
        )

    if brief:
        pitch_grams = _ngrams(words, 4)
        if pitch_grams:
            shared = len(pitch_grams & _ngrams(_words(brief), 4)) / len(pitch_grams)
            if shared > 0.15:
                flags.append(
                    f"{shared:.0%} of the pitch's four-word runs are copied from the brief, "
                    "so it restates the brief instead of inventing a story"
                )
    return flags


def penalty(flags: list[str]) -> int:
    return min(MAX_PENALTY, PENALTY_PER_FLAG * len(flags))


# Defects a hostile editor deducts points for, used by the pitch reviser to audit its own
# draft. (Giving this list to the local judge as a deduction checklist made it deduct
# 11-19 points from every pitch, good or bad, and score all of them 1, so the judge does
# not use it.) (points, defect)
PITCH_DEFECTS: list[tuple[int, str]] = [
    (3, "the premise matches a well-known book, film or show"),
    (2, "no particular people, places, objects or events: only roles, institutions, forces or abstractions"),
    (2, "the ending is predictable or a stock reveal (it was a dream, the AI did it, the mentor was the villain, it was all a simulation)"),
    (1, "the protagonist is a generic type with a generic name (a lone advisor, detective, scientist or engineer)"),
    (1, "the hook is a stock opening: a 'what happens when' question, 'in a world where', or a statement of what 'the world believes'"),
    (1, "the title could belong to any other book of its genre"),
    (1, "the stakes are generic (the fate of a nation, the world, humanity) instead of specific and personal"),
    (1, "the pitch restates the brief's mechanism in general terms instead of showing it through concrete events"),
    (1, "a comparable title is famous (so tells an agent nothing), does not fit, or does not exist"),
    (1, "each cliché or trope you can name (up to 3 points in all)"),
    (3, "any other serious weakness (explain it; at most 3 points in all)"),
]


def defects_list() -> str:
    return "\n".join(f"  -{points}  {text}" for points, text in PITCH_DEFECTS)
