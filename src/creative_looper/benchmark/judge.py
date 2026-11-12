"""Talking to the judge model: calling it, retrying, and reading its JSON replies."""

import json
import re
import time

from crewai import LLM

from creative_looper.observability import logger

JUDGE_ATTEMPTS = 3
RETRY_DELAYS = (3, 8)  # seconds to wait before the 2nd and 3rd attempts
MAX_CONSECUTIVE_FAILURES = 2  # unreachable calls in a row before scoring gives up


class JudgeUnavailable(RuntimeError):
    """The judge model could not be reached, even after retries."""


def parse_judgement(reply: str) -> dict | None:
    """Pull the JSON object out of a judge reply, tolerating code fences and chatter."""
    match = re.search(r"\{.*\}", str(reply), re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def ask_judge(llm: LLM, prompt: str, label: str, sleep=None) -> dict | None:
    """Call the judge and return its parsed JSON reply.

    Unlike agent calls, a direct `llm.call` has no retry layer, so network errors and
    unparseable replies are retried here. Raises JudgeUnavailable if the model cannot
    be reached; returns None if it answered but never with usable JSON. `sleep` can be
    replaced in tests to avoid waiting.
    """
    last_error: Exception | None = None
    answered = False
    for attempt in range(1, JUDGE_ATTEMPTS + 1):
        try:
            reply = llm.call(prompt)
        except Exception as e:  # network, timeout, quota: all worth another try
            last_error = e
            logger.warning("judge call for %s failed (attempt %d): %s", label, attempt, e)
        else:
            answered = True
            data = parse_judgement(reply)
            if data is not None:
                return data
            logger.warning("judge reply for %s was not valid JSON (attempt %d)", label, attempt)
        if attempt < JUDGE_ATTEMPTS:
            (sleep or time.sleep)(RETRY_DELAYS[attempt - 1])
    if not answered:
        raise JudgeUnavailable(str(last_error)) from last_error
    return None
