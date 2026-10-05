import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import release_notes as rn  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SAMPLE = """# Changelog

## [Unreleased]

### Changed
- Not released yet.

## [1.2.0] - 2026-10-04

Adds a thing.

### Added
- The thing.

### Fixed
- A bug.

## [1.1.0] - 2026-10-01

### Added
- Older thing.

## [1.0.0] - 2026-09-30

### Added
- First thing.

[Unreleased]: https://example.com/compare/v1.2.0...HEAD
[1.2.0]: https://example.com/compare/v1.1.0...v1.2.0
[1.1.0]: https://example.com/releases/tag/v1.1.0
"""


class ExtractTests(unittest.TestCase):
    def test_returns_only_that_versions_section_with_a_compare_link(self):
        notes = rn.extract(SAMPLE, "1.2.0")
        self.assertIn("Adds a thing.", notes)
        self.assertIn("### Fixed\n- A bug.", notes)
        self.assertNotIn("Older thing", notes)
        self.assertNotIn("Not released yet", notes)
        self.assertNotIn("[1.1.0]:", notes)
        self.assertTrue(notes.endswith("**Full changelog:** https://example.com/compare/v1.1.0...v1.2.0"))

    def test_accepts_a_tag_name(self):
        self.assertEqual(rn.extract(SAMPLE, "v1.2.0"), rn.extract(SAMPLE, "1.2.0"))

    def test_no_footer_when_the_link_is_not_a_comparison(self):
        notes = rn.extract(SAMPLE, "1.1.0")
        self.assertEqual(notes, "### Added\n- Older thing.")

    def test_last_version_without_a_link_still_works(self):
        self.assertEqual(rn.extract(SAMPLE, "1.0.0"), "### Added\n- First thing.")

    def test_missing_version_is_an_error(self):
        with self.assertRaises(rn.ReleaseNotesError):
            rn.extract(SAMPLE, "9.9.9")

    def test_version_is_matched_exactly(self):
        with self.assertRaises(rn.ReleaseNotesError):
            rn.extract(SAMPLE, "1.2")

    def test_empty_entry_is_an_error(self):
        with self.assertRaises(rn.ReleaseNotesError):
            rn.extract("## [2.0.0] - 2026-11-01\n\n## [1.0.0] - 2026-10-01\n- x\n", "2.0.0")

    def test_unreleased_is_not_a_release(self):
        with self.assertRaises(rn.ReleaseNotesError):
            rn.extract(SAMPLE, "Unreleased")


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(Path(__file__).parent / "release_notes.py"), *args],
                              capture_output=True, text=True)

    def test_prints_notes_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(SAMPLE, encoding="utf-8")
            out = self.run_cli("v1.2.0", str(changelog))
        self.assertEqual(out.returncode, 0)
        self.assertIn("### Added\n- The thing.", out.stdout)

    def test_exits_nonzero_when_the_entry_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(SAMPLE, encoding="utf-8")
            out = self.run_cli("v3.0.0", str(changelog))
        self.assertEqual(out.returncode, 1)
        self.assertIn("no entry for version 3.0.0", out.stderr)
        self.assertEqual(out.stdout, "")

    def test_pyproject_version_must_match_the_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(SAMPLE, encoding="utf-8")
            good, bad = Path(tmp) / "good.toml", Path(tmp) / "bad.toml"
            good.write_text('[project]\nversion = "1.2.0"\n', encoding="utf-8")
            bad.write_text('[project]\nversion = "1.1.0"\n', encoding="utf-8")
            ok = self.run_cli("v1.2.0", str(changelog), "--check-pyproject", str(good))
            mismatch = self.run_cli("v1.2.0", str(changelog), "--check-pyproject", str(good), str(bad))
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(mismatch.returncode, 1)
        self.assertIn("says version 1.1.0", mismatch.stderr)


class RealChangelogTests(unittest.TestCase):
    """The repository's own CHANGELOG.md must be ready to release."""

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_the_current_version_has_an_entry(self):
        for pyproject in ("v1/pyproject.toml", "v2/pyproject.toml"):
            version = rn.pyproject_version(ROOT / pyproject)
            with self.subTest(pyproject=pyproject, version=version):
                self.assertTrue(rn.extract(self.changelog, version))

    def test_the_readme_pin_example_names_the_current_version(self):
        version = rn.pyproject_version(ROOT / "v2/pyproject.toml")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"@v{version}#subdirectory=v2", readme, "update the pinning example in README.md for this release")

    def test_both_packages_share_one_version(self):
        self.assertEqual(rn.pyproject_version(ROOT / "v1/pyproject.toml"), rn.pyproject_version(ROOT / "v2/pyproject.toml"))

    def test_every_released_version_has_notes(self):
        versions = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", self.changelog, re.MULTILINE)
        self.assertTrue(versions)
        for version in versions:
            with self.subTest(version=version):
                self.assertTrue(rn.extract(self.changelog, version))


if __name__ == "__main__":
    unittest.main()
