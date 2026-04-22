"""Noise cancellation for free-form address input.

Removes tokens that are not part of a deliverable address:

* Conversational filler ("please verify", "the address is", "thanks")
* Surrounding quotes, markdown fences, emoji, zero-width characters
* Duplicated punctuation, stray URLs, phone numbers, email addresses
* Attention markers ("ATTN:", "C/O")
* Country suffix ("USA", "United States of America")

The result is not yet parsed; it is a cleaned single-line string suitable
for downstream parsing by :mod:`app.tools.address_parser`.
"""
from __future__ import annotations

import re
import unicodedata

_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"
)
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "]+",
    flags=re.UNICODE,
)
_MULTI_SPACE_RE = re.compile(r"\s{2,}")
_MULTI_PUNCT_RE = re.compile(r"([,.\-])\1{1,}")

# Leading filler that users often type before an address.
_FILLER_PREFIXES: tuple[str, ...] = (
    "please verify",
    "please validate",
    "please check",
    "please standardize",
    "can you verify",
    "can you validate",
    "can you check",
    "could you verify",
    "verify this address",
    "verify the address",
    "verify address",
    "validate this address",
    "validate the address",
    "validate address",
    "check this address",
    "check the address",
    "check address",
    "standardize this address",
    "the address is",
    "my address is",
    "our address is",
    "shipping address",
    "billing address",
    "mailing address",
    "address:",
    "addr:",
    "here is",
    "here's",
    "here it is",
    "this one",
    "address",
)

_COUNTRY_SUFFIXES: tuple[str, ...] = (
    "united states of america",
    "united states",
    "u s a",
    "u.s.a.",
    "u s",
    "u.s.",
    "usa",
)

_ATTENTION_PREFIXES: tuple[str, ...] = (
    "attn:",
    "attn.",
    "attention:",
    "c/o",
    "care of",
)

_TRAILING_FILLERS: tuple[str, ...] = (
    "thanks",
    "thank you",
    "please",
    "cheers",
    "ty",
)


def _strip_fillers(text: str) -> str:
    """Repeatedly strip known conversational prefixes."""
    lowered = text.lstrip().lower()
    changed = True
    while changed:
        changed = False
        for filler in _FILLER_PREFIXES:
            if lowered.startswith(filler):
                remainder = text.lstrip()[len(filler):]
                # Drop leading punctuation after the filler
                remainder = remainder.lstrip(" :,.-")
                text = remainder
                lowered = text.lstrip().lower()
                changed = True
                break
    return text


def _strip_attention(text: str) -> str:
    """Remove ATTN: and c/o markers, keeping the recipient line content."""
    lowered = text.lower()
    for prefix in _ATTENTION_PREFIXES:
        idx = lowered.find(prefix)
        if idx == -1:
            continue
        # Drop from prefix up to the next newline or comma
        end = len(text)
        for delim in ("\n", ","):
            d = text.find(delim, idx + len(prefix))
            if d != -1 and d < end:
                end = d
        text = (text[:idx] + text[end:]).strip()
        lowered = text.lower()
    return text


def _strip_trailing_country(text: str) -> str:
    lowered = text.rstrip().lower()
    for suffix in _COUNTRY_SUFFIXES:
        if lowered.endswith(suffix):
            cut = len(text.rstrip()) - len(suffix)
            text = text.rstrip()[:cut].rstrip(" ,")
            break
    return text


def _strip_trailing_filler(text: str) -> tuple[str, bool]:
    """Strip conversational tails like 'thanks!' or 'please'."""
    changed = False
    lowered = text.rstrip().lower()
    rstripped = text.rstrip(" .,!?\"'")
    lowered_rstripped = rstripped.lower()
    for filler in _TRAILING_FILLERS:
        if lowered_rstripped.endswith(filler) and not lowered_rstripped.endswith(
            f"0{filler}"
        ):
            cut = len(rstripped) - len(filler)
            text = rstripped[:cut].rstrip(" .,!?\"'")
            changed = True
            lowered = text.rstrip().lower()
            lowered_rstripped = text.lower()
    return text, changed


def _normalize_unicode(text: str) -> str:
    """NFKC normalize and strip zero-width / invisible characters."""
    text = unicodedata.normalize("NFKC", text)
    # Strip zero-width and bidi control characters
    return "".join(ch for ch in text if unicodedata.category(ch) not in ("Cf", "Cc") or ch in "\n\t")


def cancel_noise(raw: str) -> tuple[str, list[str]]:
    """Return a cleaned address string and a list of noise categories removed."""
    if not raw:
        return "", []
    notes: list[str] = []
    text = _normalize_unicode(raw)
    text = text.strip().strip("\"'`")
    # Fenced code or bracket wrappers
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip("[]()<>")

    if _EMOJI_RE.search(text):
        notes.append("emoji")
        text = _EMOJI_RE.sub(" ", text)

    if _URL_RE.search(text):
        notes.append("url")
        text = _URL_RE.sub(" ", text)

    if _EMAIL_RE.search(text):
        notes.append("email")
        text = _EMAIL_RE.sub(" ", text)

    if _PHONE_RE.search(text):
        notes.append("phone")
        text = _PHONE_RE.sub(" ", text)

    new = _strip_fillers(text)
    if new != text:
        notes.append("filler")
        text = new

    new = _strip_attention(text)
    if new != text:
        notes.append("attention")
        text = new

    new = _strip_trailing_country(text)
    if new != text:
        notes.append("country_suffix")
        text = new

    text, trailing_changed = _strip_trailing_filler(text)
    if trailing_changed and "filler" not in notes:
        notes.append("filler")

    # Strip surrounding quotes again, now that prefixes/suffixes are gone
    text = text.strip().strip("\"'`“”‘’")

    text = _MULTI_PUNCT_RE.sub(r"\1", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip(" ,.-")
    return text, notes
