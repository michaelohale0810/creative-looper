"""Turning exceptions into one-line messages a person can act on."""


def short_error(e: BaseException, limit: int = 300) -> str:
    """A one-line, human-readable version of an exception (known causes get advice)."""
    text = " ".join(str(e).split())
    if "API key not valid" in text or "API_KEY_INVALID" in text:
        return "Gemini rejected GEMINI_API_KEY. Check the key in your .env file."
    if any(m in text for m in ("nodename nor servname", "Name or service not known", "Temporary failure in name resolution")):
        return "Could not reach the Gemini API (DNS lookup failed). Check your network or VPN and try again."
    if "Connection refused" in text or "Cannot connect to host" in text:
        return "Could not reach the local Ollama server. Start it (`ollama serve`) or check OLLAMA_HOST."
    return text if len(text) <= limit else text[:limit] + "..."
