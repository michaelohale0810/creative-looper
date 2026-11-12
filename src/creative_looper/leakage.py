"""Detecting primary-domain vocabulary in text that should live in the target domain only.

The pitch writer sees only the target-domain brief, so any word from the primary domain
that shows up in a report is "leakage". This is an indicator for spotting it, not an
exact test: it matches the domain's name and its word forms, not its jargon.
"""

import re
from pathlib import Path


def domain_pattern(domain: str) -> re.Pattern[str]:
    """Rough matcher for a domain's vocabulary: the stem of each word of 4+ letters.

    "Geology" matches geology and geological; "Quantum Physics" matches quantum and
    physics. It is an indicator for spotting leakage, not an exact test.
    """
    stems = [
        re.escape(word[: max(4, len(word) - 2)])
        for word in re.findall(r"\w+", domain.lower())
        if len(word) >= 4
    ]
    return re.compile(r"\b(?:" + "|".join(stems) + ")", re.IGNORECASE) if stems else re.compile(r"(?!)")


def count_domain_mentions(run_dir: Path, domain: str, names: list[str]) -> dict[str, int]:
    """Count mentions of `domain`'s vocabulary in each named report that exists."""
    pattern = domain_pattern(domain)
    counts = {}
    for name in names:
        path = run_dir / name
        if path.exists():
            counts[name] = len(pattern.findall(path.read_text(encoding="utf-8")))
    return counts
