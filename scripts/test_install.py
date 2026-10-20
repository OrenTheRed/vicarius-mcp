"""Tests for install.sh: the questions, going back, the review, and what an install writes.

Each test runs the real script with bash, answers from a file (VICARIUS_INSTALL_INPUT), a temporary
HOME, and fake uv, git, claude and codex programs first on PATH, so nothing touches the network or
the real machine. Set INSTALL_TEST_BASH=/bin/bash to run them under the bash 3.2 macOS ships.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "install.sh"
BASH = os.environ.get("INSTALL_TEST_BASH", "bash")

FAKES = {
    # Records every call. tool dir --bin names the fake bin dir; run ... python - runs python3.
    "uv": """
        echo "uv $*" >> "$FAKE_LOG"
        case "$1 $2" in
          "--version ") echo "uv 0.0.0-test" ;;
          "tool dir") echo "$FAKE_BIN" ;;
          "tool install")
            for s in vicarius-v2-mcp vicarius-mcp; do
              printf '#!/bin/sh\\necho "%s 9.9.9"\\n' "$s" > "$FAKE_BIN/$s"; chmod +x "$FAKE_BIN/$s"
            done ;;
          "run --no-project") shift 4; exec python3 "$@" ;;
        esac
    """,
    "git": """
        echo "git $*" >> "$FAKE_LOG"
        [ "$1" = ls-remote ] && printf 'abc\\trefs/tags/v9.9.9\\nabd\\trefs/tags/v9.9.8\\n'
        exit 0
    """,
    "claude": """
        echo "claude $*" >> "$FAKE_LOG"
        [ "$2" = get ] && exit 1
        exit 0
    """,
    "codex": """
        echo "codex $*" >> "$FAKE_LOG"
        [ "$2" = get ] && exit 1
        exit 0
    """,
    "curl": """
        echo "curl $*" >> "$FAKE_LOG"
        echo 200
    """,
}


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.log = self.tmp / "calls.log"
        self.log.touch()
        for name, body in FAKES.items():
            path = self.bin / name
            path.write_text("#!/bin/sh\n" + textwrap.dedent(body))
            path.chmod(path.stat().st_mode | stat.S_IEXEC)
        self.tenants = self.home / ".config/vicarius-v2-mcp/tenants.json"

    def run_installer(self, answers, *args, check=True):
        answers_file = self.tmp / "answers.txt"
        answers_file.write_text("\n".join(answers) + "\n")
        env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "TMPDIR": str(self.tmp),
            "VICARIUS_INSTALL_INPUT": str(answers_file),
            "FAKE_LOG": str(self.log),
            "FAKE_BIN": str(self.bin),
            "NO_COLOR": "1",
        }
        result = subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60)
        if check:
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr)
        return result

    def calls(self):
        return self.log.read_text()

    # v2 only, one tenant acme, defaults after that, connect Claude Code only, submit.
    ONE_TENANT = ["1", "acme", "key-acme-123", "", "3", "n", "1", "y", "n", "n", "1", "1"]

    def test_a_dry_run_shows_the_commands_and_changes_nothing(self):
        out = self.run_installer(self.ONE_TENANT, "--dry-run").stdout
        self.assertIn("[dry-run] uv tool install --force git+https://github.com/OrenTheRed/vicarius-mcp@v9.9.9#subdirectory=v2", out)
        self.assertIn("[dry-run] claude mcp add --scope user vicarius-v2 -- vicarius-v2-mcp", out)
        self.assertIn("Dry run finished. Nothing was changed.", out)
        self.assertNotIn("key-acme-123", out)
        self.assertFalse(self.tenants.exists())
        self.assertNotIn("uv tool install", self.calls())
        self.assertNotIn("mcp add", self.calls())

    def test_b_goes_back_one_question_at_a_time(self):
        answers = [
            "2",                   # v1 only
            "b",                   # back from the dashboard name to the servers question
            "1",                   # v2 only
            "acme", "b",           # back from the key to the tenant name
            "acme2", "key-2", "",  # name, key, default host
            "1",                   # add another tenant
            "b",                   # back out of the new tenant to the list
            "3",                   # continue
            "y",                   # read-only
            "b",                   # back from the toolsets question to read-only
            "n", "2",              # not read-only; core tools
            "n", "n", "n",         # no clients
            "2",                   # main
            "2",                   # review: go back
            "1",                   # version: latest release
            "1",                   # review: submit
        ]
        out = self.run_installer(answers, "--dry-run").stdout
        review = out.split("Review")[-1]
        self.assertIn("Servers:      v2", review)
        self.assertNotIn("v1", review.split("Ready?")[0])
        self.assertIn("v2 tenants:   acme2,", review)
        self.assertIn("v2 tools:     core", review)
        self.assertIn("Read-only:    n", review)
        self.assertIn("Version:      release", review)
        self.assertIn("Connect:      nothing", review)

    def test_going_back_keeps_an_earlier_client_answer(self):
        # claude is on PATH, so Claude Code defaults to y. After n and a step back, the default is n.
        answers = ["1", "acme", "k", "", "3", "n", "1", "n", "n", "n", "b", "", "", "", "1", "1"]
        out = self.run_installer(answers, "--dry-run").stdout
        self.assertIn("Connect Claude Code? (y/n) [y]", out)
        self.assertIn("Connect Claude Code? (y/n) [n]", out)
        self.assertIn("Connect:      nothing", out.split("Review")[-1])

    def test_b_at_the_first_question_stays_there(self):
        out = self.run_installer(["b", "q"]).stdout
        self.assertIn("This is the first question.", out)
        self.assertIn("Cancelled. Nothing was changed.", out)

    def test_quitting_at_the_review_changes_nothing(self):
        out = self.run_installer(self.ONE_TENANT[:-1] + ["3"]).stdout
        self.assertIn("Cancelled. Nothing was changed.", out)
        self.assertFalse(self.tenants.exists())
        self.assertEqual(self.calls().count("uv tool install"), 0)

    def test_an_install_writes_a_private_tenants_file_and_connects_claude_code(self):
        self.run_installer(self.ONE_TENANT)
        self.assertEqual(json.loads(self.tenants.read_text()), {"acme": {"api_key": "key-acme-123"}})
        self.assertEqual(stat.S_IMODE(self.tenants.stat().st_mode), 0o600)
        calls = self.calls()
        self.assertIn("uv tool install --force git+https://github.com/OrenTheRed/vicarius-mcp@v9.9.9#subdirectory=v2", calls)
        self.assertIn("claude mcp add --scope user vicarius-v2 -- vicarius-v2-mcp", calls)
        self.assertNotIn("key-acme-123", calls)  # a v2 key never appears on a command line
        self.assertEqual(list(self.tmp.glob("vicarius-install.*")), [])  # the private temp file is gone

    def test_merging_keeps_the_existing_tenants_and_saves_a_backup(self):
        self.tenants.parent.mkdir(parents=True)
        self.tenants.write_text(json.dumps({"old": {"api_key": "old-key"}}))
        answers = ["1", "1", "new", "new-key", "eu.vicarius.cloud", "3", "n", "1", "n", "n", "n", "1", "1"]
        self.run_installer(answers)
        self.assertEqual(json.loads(self.tenants.read_text()), {
            "old": {"api_key": "old-key"},
            "new": {"api_key": "new-key", "host": "eu.vicarius.cloud"},
        })
        self.assertEqual(json.loads((self.tenants.parent / "tenants.json.bak").read_text()), {"old": {"api_key": "old-key"}})

    def test_keeping_the_tenants_file_skips_the_tenant_questions(self):
        self.tenants.parent.mkdir(parents=True)
        self.tenants.write_text(json.dumps({"old": {"api_key": "old-key"}}))
        out = self.run_installer(["1", "2", "n", "1", "n", "n", "n", "1", "1"]).stdout
        self.assertNotIn("New tenant", out)
        self.assertEqual(json.loads(self.tenants.read_text()), {"old": {"api_key": "old-key"}})

    def test_v1_read_only_on_codex_and_claude_desktop(self):
        config = self.claude_desktop_config()
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"mcpServers": {"other": {"command": "other-mcp"}}, "theme": "dark"}))
        answers = ["2", "acme", "v1-key", "y", "n", "y", "y", "2", "1"]
        self.run_installer(answers)
        calls = self.calls()
        self.assertIn("uv tool install --force git+https://github.com/OrenTheRed/vicarius-mcp#subdirectory=v1", calls)
        self.assertIn("codex mcp add vicarius --env VICARIUS_DASHBOARD=acme --env VICARIUS_API_KEY=v1-key --env VICARIUS_READ_ONLY=true -- vicarius-mcp", calls)
        data = json.loads(config.read_text())
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcpServers"]["other"], {"command": "other-mcp"})
        self.assertEqual(data["mcpServers"]["vicarius"], {
            "command": str(self.bin / "vicarius-mcp"),
            "env": {"VICARIUS_DASHBOARD": "acme", "VICARIUS_API_KEY": "v1-key", "VICARIUS_READ_ONLY": "true"},
        })
        self.assertFalse(self.tenants.exists())

    def test_a_bad_tenant_name_is_asked_again(self):
        answers = ["1", "bad name!", "acme", "k", "", "3", "n", "1", "n", "n", "n", "1", "1"]
        out = self.run_installer(answers, "--dry-run").stdout
        self.assertIn("Use letters, digits, dot, dash or underscore only.", out)
        self.assertIn("v2 tenants:   acme,", out)

    def test_no_terminal_is_a_clear_error(self):
        env = {"HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin", "VICARIUS_INSTALL_INPUT": str(self.tmp / "missing")}
        result = subprocess.run([BASH, str(SCRIPT)], capture_output=True, text=True, env=env, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("needs a terminal", result.stderr)

    def claude_desktop_config(self):
        if os.uname().sysname == "Darwin":
            return self.home / "Library/Application Support/Claude/claude_desktop_config.json"
        return self.home / ".config/Claude/claude_desktop_config.json"


if __name__ == "__main__":
    unittest.main()
