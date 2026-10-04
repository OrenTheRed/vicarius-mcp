#!/usr/bin/env python3
"""Print the GitHub release notes for one version, taken from CHANGELOG.md.

usage: release_notes.py VERSION [CHANGELOG.md] [--check-pyproject FILE ...]

VERSION may be "1.2.0" or a tag such as "v1.2.0". The notes are the text under that version's
"## [X.Y.Z]" heading, followed by a link to the full comparison when the changelog has one.
Exits with an error when the changelog has no entry (or an empty one) for the version, or when a
--check-pyproject file declares a different version. The release workflow uses this so a release
cannot be published without a changelog entry that matches the tag.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


class ReleaseNotesError(Exception):
    pass


def extract(changelog: str, version: str) -> str:
    """The notes for `version`, or raise ReleaseNotesError."""
    version = version.removeprefix("v")
    if version.lower() == "unreleased":
        raise ReleaseNotesError("Unreleased is not a release")
    heading = re.compile(rf"^## \[{re.escape(version)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?\s*$")
    lines = changelog.splitlines()
    start = next((i for i, line in enumerate(lines) if heading.match(line)), None)
    if start is None:
        raise ReleaseNotesError(f"CHANGELOG.md has no entry for version {version}")
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## [") or re.match(r"^\[[^\]]+\]:\s", line):
            break
        body.append(line)
    text = "\n".join(body).strip()
    if not text:
        raise ReleaseNotesError(f"The CHANGELOG.md entry for version {version} is empty")

    link = re.search(rf"^\[{re.escape(version)}\]:\s+(\S+)\s*$", changelog, re.MULTILINE)
    if link and "/compare/" in link.group(1):
        text += f"\n\n**Full changelog:** {link.group(1)}"
    return text


def pyproject_version(path: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise ReleaseNotesError(f"No version found in {path}")
    return match.group(1)


def main(argv: list[str]) -> int:
    args = list(argv)
    check = []
    if "--check-pyproject" in args:
        i = args.index("--check-pyproject")
        check = args[i + 1:]
        args = args[:i]
    if not args:
        print(__doc__, file=sys.stderr)
        return 2
    version = args[0].removeprefix("v")
    changelog_path = Path(args[1]) if len(args) > 1 else Path("CHANGELOG.md")
    try:
        for path in check:
            found = pyproject_version(Path(path))
            if found != version:
                raise ReleaseNotesError(f"{path} says version {found}, but the release is {version}")
        print(extract(changelog_path.read_text(encoding="utf-8"), version))
    except (ReleaseNotesError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
