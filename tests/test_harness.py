"""Exercise the harness with temporary day folders and simulated HTTP responses."""

import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import aoc
from scripts import fetch_day

SYNTHETIC_SOLVER = """from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Answer:
    text: str

def solve(input_data: str, is_test: bool = False) -> str:
    source = "sample" if is_test else "real"
    return Answer(source + ":" + input_data).text.rstrip("\\r\\n")
"""


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = self.enterContext(TemporaryDirectory())
        self.root = Path(directory)
        self.enterContext(patch.object(aoc, "ROOT", self.root))
        self.stdout = self.enterContext(redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(redirect_stderr(io.StringIO()))

    def test_auth_finds_chrome_session_without_requesting_a_paste(self) -> None:
        account = "AoC User (https://github.com/example)"
        with (
            patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root), "AOC_SESSION": ""}),
            patch.object(aoc, "chrome_session_token", return_value="chrome-cookie") as retrieve,
            patch.object(aoc, "getpass") as prompt,
            patch.object(aoc, "session_account", return_value=account) as verify,
            patch("builtins.input", return_value="y") as confirm,
        ):
            self.assertEqual(aoc.main(["auth"]), 0)
            self.assertEqual(fetch_day.session_token(), "chrome-cookie")

        retrieve.assert_called_once_with()
        prompt.assert_not_called()
        verify.assert_called_once_with("chrome-cookie")
        confirm.assert_called_once_with(f"Save the session for {account}? [y/N] ")
        self.assertNotIn("chrome-cookie", self.stdout.getvalue() + self.stderr.getvalue())

    def test_auth_saves_verified_session_privately_after_confirmation(self) -> None:
        path = self.root / "aocd" / "token"
        path.parent.mkdir()
        path.write_text("old-cookie\n", encoding="utf-8")
        account = "AoC User (https://github.com/example)"

        with (
            patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root), "AOC_SESSION": ""}),
            patch.object(aoc, "getpass", return_value="  new-cookie  "),
            patch.object(aoc, "session_account", return_value=account) as verify,
            patch("builtins.input", return_value="yes") as confirm,
        ):
            self.assertEqual(aoc.main(["auth", "--manual"]), 0)
            self.assertEqual(fetch_day.session_token(), "new-cookie")

        verify.assert_called_once_with("new-cookie")
        confirm.assert_called_once_with(f"Save the session for {account}? [y/N] ")
        if os.name != "nt":
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn("new-cookie", self.stdout.getvalue() + self.stderr.getvalue())

    def test_auth_keeps_existing_session_when_verification_fails_or_user_declines(self) -> None:
        path = self.root / "aocd" / "token"
        path.parent.mkdir()
        path.write_text("old-cookie\n", encoding="utf-8")
        with (
            patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root)}),
            patch.object(aoc, "getpass", return_value="new-cookie"),
            patch.object(aoc, "session_account") as verify,
            patch("builtins.input", return_value="") as confirm,
        ):
            verify.side_effect = fetch_day.StopFetching("Expired session")
            self.assertEqual(aoc.main(["auth", "--manual"]), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "old-cookie\n")
            confirm.assert_not_called()

            verify.side_effect = None
            verify.return_value = "AoC User"
            self.assertEqual(aoc.main(["auth", "--manual"]), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "old-cookie\n")

    def test_init_only_fetches_missing_released_days_and_can_resume(self) -> None:
        cached = aoc.Puzzle(2024, 1)
        missing = aoc.Puzzle(2024, 2)
        other_year = aoc.Puzzle(2025, 1)
        future = aoc.Puzzle(9999, 1)
        for puzzle in (cached, missing, other_year, future):
            aoc.scaffold(puzzle)
        cached.input_path.write_bytes(b"existing\n")
        (self.root / "years" / "2024" / "day03").mkdir()

        with (
            patch.object(aoc, "session_token", return_value="test-token") as session,
            patch.object(aoc, "download_input", return_value=b"  new input  \r\n") as download,
        ):
            self.assertEqual(aoc.main(["init", "2024"]), 0)
            download.assert_called_once_with(2024, 2, "test-token")
            self.assertEqual(aoc.main(["init", "2024"]), 0)
            session.assert_called_once_with()
            self.assertEqual(download.call_count, 1)

        self.assertEqual(cached.input_path.read_bytes(), b"existing\n")
        self.assertEqual(missing.input_path.read_bytes(), b"  new input  \r\n")
        self.assertFalse(other_year.input_path.exists())
        self.assertFalse(future.input_path.exists())
        self.assertFalse(aoc.selection_path().exists())

    def test_init_reports_unavailable_and_stops_on_expired_session(self) -> None:
        for day in (13, 14, 15):
            aoc.scaffold(aoc.Puzzle(2025, day))
        with (
            patch.object(aoc, "session_token", return_value="test-token"),
            patch.object(aoc, "sleep"),
            patch.object(
                aoc, "download_input", side_effect=[None, fetch_day.StopFetching("Expired session")]
            ) as download,
        ):
            self.assertEqual(aoc.main(["init"]), 1)

        self.assertEqual(download.call_args_list, [call(2025, 13, "test-token"), call(2025, 14, "test-token")])
        self.assertIn("1 unavailable, 1 failed, 1 skipped", self.stdout.getvalue())
        self.assertIn("Expired session", self.stderr.getvalue())
        self.assertFalse(aoc.Puzzle(2025, 14).input_path.exists())

    def test_start_before_release_selects_day_and_preserves_edits(self) -> None:
        puzzle = aoc.Puzzle(9999, 8)
        with patch.object(aoc, "session_token") as session:
            self.assertEqual(aoc.main(["start", "9999", "08"]), 0)
            self.assertEqual(aoc.current_selection(), (puzzle, 1))
            self.assertIn(
                "https://adventofcode.com/9999/day/8",
                (puzzle.directory / "README.md").read_text(encoding="utf-8"),
            )
            self.assertFalse(puzzle.input_path.exists())
            sample = puzzle.directory / "examples" / "sample.txt"
            manifest = puzzle.directory / "examples.toml"
            self.assertEqual(sample.read_bytes(), b"")
            self.assertIn('# expected = "answer"', manifest.read_text(encoding="utf-8"))

            sample.unlink()
            self.assertEqual(aoc.main(["start", "9999", "08"]), 0)
            self.assertEqual(sample.read_bytes(), b"")

            sample.write_bytes(b"example input\n")
            answers = '[[part1]]\ninput = "sample.txt"\nexpected = "3"\n'
            manifest.write_text(answers, encoding="utf-8")
            puzzle.solution_path(1).write_text(SYNTHETIC_SOLVER, encoding="utf-8")
            self.assertEqual(aoc.main(["start", "9999", "08"]), 0)
            self.assertEqual(puzzle.solution_path(1).read_text(encoding="utf-8"), SYNTHETIC_SOLVER)
            self.assertEqual(sample.read_bytes(), b"example input\n")
            self.assertEqual(manifest.read_text(encoding="utf-8"), answers)
            self.assertEqual(aoc.main(["part", "2"]), 0)
            self.assertEqual(aoc.current_selection(), (puzzle, 2))
            session.assert_not_called()

    def test_real_input_bypasses_example_checks(self) -> None:
        puzzle = aoc.Puzzle(2025, 1)
        aoc.scaffold(puzzle)
        puzzle.solution_path(1).write_text(SYNTHETIC_SOLVER, encoding="utf-8")
        puzzle.input_path.write_bytes(b" live\r\n")
        (puzzle.directory / "examples" / "sample.txt").write_text("example\n", encoding="utf-8")
        (puzzle.directory / "examples.toml").write_text(
            '[[part1]]\ninput = "sample.txt"\nexpected = "wrong"\n',
            encoding="utf-8",
        )
        aoc.select(puzzle, 1)

        self.assertEqual(aoc.main(["sample"]), 1)
        self.assertIn("Result: sample:example", self.stdout.getvalue())
        self.assertIn("Expected: wrong", self.stderr.getvalue())
        self.assertEqual(aoc.main(["run"]), 0)
        self.assertIn("Result: real: live", self.stdout.getvalue())


class DownloadTests(unittest.TestCase):
    def test_chrome_reader_uses_only_the_live_advent_of_code_session(self) -> None:
        live = SimpleNamespace(domain=".adventofcode.com", name="session", path="/", value="live-cookie")
        live.is_expired = lambda: False
        expired = SimpleNamespace(**(vars(live) | {"value": "expired-cookie", "is_expired": lambda: True}))
        unrelated = SimpleNamespace(**(vars(live) | {"domain": "other-adventofcode.com", "value": "other-cookie"}))
        browser = SimpleNamespace(BrowserCookieError=RuntimeError, chrome=Mock(return_value=[expired, unrelated, live]))
        with patch.dict(sys.modules, {"browser_cookie3": browser}):
            self.assertEqual(fetch_day.chrome_session_token(), "live-cookie")
            browser.chrome.assert_called_once_with(domain_name="adventofcode.com")

            browser.chrome.return_value = [expired, unrelated]
            with self.assertRaisesRegex(fetch_day.StopFetching, "No Advent of Code session"):
                fetch_day.chrome_session_token()

    def test_session_account_reads_settings_and_rejects_a_redirect(self) -> None:
        with patch.object(fetch_day, "HTTPSConnection") as https:
            connection = https.return_value
            response = connection.getresponse.return_value
            response.status = 200
            response.headers.get_content_type.return_value = "text/html"
            response.read.return_value = (
                b'<header><div class="user">A &amp; B <span class="star-count">24*</span></div></header>'
                b"<main><span>Link to https://github.com/example</span></main>"
            )
            self.assertEqual(fetch_day.session_account("test-token"), "A & B (https://github.com/example)")
            self.assertEqual(connection.request.call_args.args, ("GET", "/settings"))

            response.status = 303
            with self.assertRaises(fetch_day.StopFetching):
                fetch_day.session_account("test-token")

    def test_download_keeps_original_bytes(self) -> None:
        with patch.object(fetch_day, "HTTPSConnection") as https:
            connection = https.return_value
            response = connection.getresponse.return_value
            response.status = 200
            response.headers.get_content_type.return_value = "text/plain"
            response.read.return_value = b"  input\r\n"

            self.assertEqual(fetch_day.download_input(2025, 8, "test-token"), b"  input\r\n")
            https.assert_called_once_with("adventofcode.com", timeout=15)
            connection.request.assert_called_once_with(
                "GET",
                "/2025/day/8/input",
                headers={"Cookie": "session=test-token", "User-Agent": fetch_day.USER_AGENT},
            )
            connection.close.assert_called_once_with()

    def test_never_treats_login_responses_as_input(self) -> None:
        with patch.object(fetch_day, "HTTPSConnection") as https:
            response = https.return_value.getresponse.return_value
            for status in (302, 400, 429):
                with self.subTest(status=status):
                    response.status = status
                    with self.assertRaises(fetch_day.StopFetching):
                        fetch_day.download_input(2025, 8, "test-token")
            response.status = 200
            response.headers.get_content_type.return_value = "text/html"
            with self.assertRaises(fetch_day.FetchError):
                fetch_day.download_input(2025, 8, "test-token")
            response.read.assert_not_called()
