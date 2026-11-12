"""Domain lists: reading them from files and drawing a random pair for a run.

A list file has one domain per line. Blank lines and lines starting with # are ignored.
"""

import random
from pathlib import Path

from creative_looper.paths import sanitize_domain

# Where the loop looks for its lists unless told otherwise (relative to the working directory).
DEFAULT_PRIMARY_FILE = Path("domains/primary_domains.txt")
DEFAULT_TARGET_FILE = Path("domains/target_domains.txt")

MAX_PAIR_DRAWS = 20


def load_domains(path: Path) -> list[str]:
    """Read a domain list. Duplicates (ignoring case) are dropped, order is kept.

    Raises ValueError, naming the file and line, for a missing or empty file or for a
    line that cannot be used as a domain (it must contain a letter or digit).
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise ValueError(f"Cannot read the domain list {path}: {e.strerror or e}") from e

    domains: list[str] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            sanitize_domain(text)  # the name must be usable in a folder name
        except ValueError:
            raise ValueError(f"{path}, line {number}: {text!r} has no letters or digits") from None
        if text.casefold() not in seen:
            seen.add(text.casefold())
            domains.append(text)
    if not domains:
        raise ValueError(f"{path} lists no domains (one per line; # starts a comment)")
    return domains


def pick_pair(
    primaries: list[str], targets: list[str], rng: random.Random | None = None
) -> tuple[str, str]:
    """A random (primary, target) pair that is not the same domain twice.

    Raises ValueError if the lists only offer the same domain on both sides.
    """
    rng = rng or random
    for _ in range(MAX_PAIR_DRAWS):
        primary, target = rng.choice(primaries), rng.choice(targets)
        if primary.casefold() != target.casefold():
            return primary, target
    raise ValueError("The primary and target lists only offer the same domain; add more.")
