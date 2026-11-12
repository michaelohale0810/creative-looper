"""Where a run's files go and how its folder is named."""

import os
import re
from datetime import datetime
from pathlib import Path

# Runs are written under ./output in the directory the command is run from, or under
# CREATIVE_LOOPER_OUTPUT if that is set. (Not relative to this file, so it also works
# when the package is installed rather than run from a checkout.)
OUTPUT_ROOT = Path(os.getenv("CREATIVE_LOOPER_OUTPUT") or Path.cwd() / "output")


def sanitize_domain(name: str) -> str:
    """Collapse anything that isn't a letter or digit into single underscores."""
    cleaned = re.sub(r"\W+", "_", name.strip()).strip("_")
    if not cleaned:
        raise ValueError("Domain name must contain at least one letter or digit.")
    return cleaned


def create_run_dir(
    primary: str, target: str, root: Path = OUTPUT_ROOT, now: datetime | None = None
) -> Path:
    """Create output/[Primary]_[Target]_[YYYYMMDD_HHMMSS]/ and return its path.

    The timestamp keeps repeated runs of the same domains from overwriting each other.
    """
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_dir = root / f"{sanitize_domain(primary)}_{sanitize_domain(target)}_{stamp}"
    run_dir.mkdir(parents=True)
    return run_dir
