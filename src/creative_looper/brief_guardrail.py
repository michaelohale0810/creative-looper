"""Quality gate for the target-domain brief.

The pitch writer must see the idea in target-domain language only, so the brief is
checked for words that still belong to the primary domain and sent back for a rewrite
(up to MAX_BRIEF_REWRITES times) while it leans on them. CrewAI calls the guardrail
each time the brief agent finishes a draft.
"""

from collections.abc import Callable
from typing import Any

from crewai import LLM
from crewai.tasks.task_output import TaskOutput

from creative_looper.leakage import domain_pattern
from creative_looper.observability import logger

MAX_BRIEF_REWRITES = 3
MAX_TERMS_REPORTED = 15


def foreign_terms(draft: str, primary: str, target: str, llm: LLM) -> list[str]:
    """Ask the model which words in `draft` belong to the primary domain.

    Names can be matched by pattern (see `leakage`), but technical jargon (a "catalyst"
    or "redox potential" in a boardroom) can only be recognized by reading it.
    """
    reply = llm.call(
        f"Below is a brief that is supposed to be written purely in the language of "
        f"{target}. List every word or phrase in it that comes from {primary} or from "
        f"another technical field (science, engineering, medicine, etc.) and would "
        f"sound out of place in an ordinary conversation among {target} "
        f"practitioners. Reply with only a comma-separated list of those words and "
        f"phrases, or the single word NONE if there are none.\n\n---\n{draft}"
    )
    reply = str(reply).strip()
    if not reply or reply.upper().startswith("NONE"):
        return []
    terms = [term.strip(" .*`\"'") for term in reply.split(",") if term.strip()]
    return terms[:MAX_TERMS_REPORTED]


def make_guardrail(
    primary: str, target: str, llm: LLM
) -> Callable[[TaskOutput], tuple[bool, Any]]:
    """Build the guardrail for one run (it counts its own rewrite attempts).

    CrewAI's contract: return (True, output) to accept the draft, or (False, message)
    to send `message` back to the agent as feedback for another attempt.
    """
    attempts = 0

    def guardrail(output: TaskOutput) -> tuple[bool, Any]:
        nonlocal attempts
        attempts += 1
        problems = sorted(set(domain_pattern(primary).findall(output.raw)))
        problems += foreign_terms(output.raw, primary, target, llm)
        if not problems or attempts > MAX_BRIEF_REWRITES:
            # Out of attempts: accept the draft with a warning rather than failing the run.
            if problems:
                logger.warning("brief accepted with leftover primary-domain terms: %s", problems)
            return True, output
        logger.warning("brief rewrite %d requested; foreign terms: %s", attempts, problems)
        return False, (
            f"The brief still uses vocabulary from {primary} or technical fields: "
            f"{', '.join(problems)}. Rewrite it so none of these (or similar words) appear; "
            f"express every idea, limit and insight in plain {target} language."
        )

    return guardrail
