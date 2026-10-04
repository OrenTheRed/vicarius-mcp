"""Whole-token matching, so a loose substring cannot score a wrong answer as right."""

from __future__ import annotations

import re


def whole(needle: str, text: str) -> bool:
    """`needle` as a whole token: "18" is not in "118" or "CVE-2025-1018", and "s-1" is not in "s-10"."""
    return re.search(rf"(?<![\w-]){re.escape(needle)}(?![\w-])", text, re.IGNORECASE) is not None
