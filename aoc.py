"""Prepare and run Advent of Code puzzles."""

import argparse
import importlib.util
import inspect
import json
import os
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from getpass import GetPassWarning, getpass
from pathlib import Path
from tempfile import TemporaryDirectory
from time import sleep
from typing import TYPE_CHECKING
from warnings import catch_warnings, simplefilter

from scripts.fetch_day import (
    FetchError,
    StopFetching,
    chrome_session_token,
    download_input,
    session_account,
    session_token,
    session_token_path,
    validate_token,
)

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parent
RELEASE_TIMEZONE = timezone(timedelta(hours=-5))
SOLUTION_TEMPLATE = """def solve(input_data: str) -> int | str:
    raise NotImplementedError("Solution not yet implemented")
"""
EXAMPLE_TEMPLATE = """# Save the example as examples/sample.txt and set the answer for each part.
[[part1]]
input = "sample.txt"
# expected = "answer"

[[part2]]
input = "sample.txt"
# expected = "answer"
"""


class HarnessError(RuntimeError):
    """The requested operation cannot be performed with the current files."""


@dataclass(frozen=True)
class Puzzle:
    year: int
    day: int

    def __post_init__(self) -> None:
        if not 2015 <= self.year <= 9999 or not 1 <= self.day <= 25:
            raise HarnessError("Use an Advent of Code year (2015 or later) and a day from 1 to 25.")

    @property
    def directory(self) -> Path:
        return ROOT / "years" / str(self.year) / f"day{self.day:02}"

    @property
    def released(self) -> bool:
        return date(self.year, 12, self.day) <= datetime.now(RELEASE_TIMEZONE).date()

    @property
    def label(self) -> str:
        return f"{self.year} Day {self.day:02}"

    @property
    def input_path(self) -> Path:
        return self.directory / "input.txt"

    def solution_path(self, part: int) -> Path:
        return self.directory / f"task{part}.py"


def write_file(path: Path, contents: bytes, *, replace: bool = False, mode: int | None = None) -> bool:
    """Write atomically and preserve existing files unless replacement is requested."""
    with TemporaryDirectory(dir=path.parent) as temporary:
        candidate = Path(temporary) / path.name
        candidate.write_bytes(contents)
        if mode is not None:
            candidate.chmod(mode)
        if replace:
            candidate.replace(path)
        else:
            try:
                path.hardlink_to(candidate)
            except FileExistsError:
                return False
    return True


def authenticate(*, manual: bool) -> int:
    try:
        if manual:
            with catch_warnings():
                simplefilter("error", GetPassWarning)
                token = validate_token(getpass("Paste the Advent of Code session cookie value: "))
        else:
            print("Looking for your Advent of Code session in Chrome...")
            token = chrome_session_token()
        account = session_account(token)
        confirmation = input(f"Save the session for {account}? [y/N] ").strip().lower()
    except GetPassWarning:
        raise HarnessError("Run just auth-manual in an interactive terminal.") from None
    except (EOFError, KeyboardInterrupt):
        print("\nAuthentication cancelled.")
        return 1
    if confirmation not in ("y", "yes"):
        print("Authentication cancelled.")
        return 0

    path = session_token_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    write_file(path, (token + "\n").encode(), replace=True, mode=0o600)
    print(f"Saved the session for {account} in {path}.")
    if os.environ.get("AOC_SESSION", "").strip():
        print("Unset AOC_SESSION to use the saved session.")
    return 0


def scaffold(puzzle: Puzzle) -> None:
    puzzle.directory.mkdir(parents=True, exist_ok=True)
    examples = puzzle.directory / "examples"
    examples.mkdir(exist_ok=True)
    readme = f"# {puzzle.label}\n\n[Advent of Code puzzle](https://adventofcode.com/{puzzle.year}/day/{puzzle.day})\n"
    write_file(puzzle.directory / "README.md", readme.encode())
    for part in (1, 2):
        write_file(puzzle.solution_path(part), SOLUTION_TEMPLATE.encode())
    manifest = puzzle.directory / "examples.toml"
    template = EXAMPLE_TEMPLATE.encode()
    write_file(manifest, template)
    sample = examples / "sample.txt"
    if not sample.exists() and manifest.read_bytes() == template:
        write_file(sample, b"")


def selection_path() -> Path:
    return ROOT / ".aoc" / "current.json"


def select(puzzle: Puzzle, part: int) -> None:
    if not puzzle.solution_path(part).is_file():
        raise HarnessError(f"No solution file for {puzzle.label} Part {part}.")
    selection = selection_path()
    selection.parent.mkdir(parents=True, exist_ok=True)
    record = {"year": puzzle.year, "day": puzzle.day, "part": part}
    write_file(selection, (json.dumps(record) + "\n").encode(), replace=True)
    print(f"Selected {puzzle.label} Part {part} ({puzzle.directory.relative_to(ROOT)})")


def current_selection() -> tuple[Puzzle, int]:
    path = selection_path()
    if not path.is_file():
        raise HarnessError("Select a day with just start YEAR DAY.")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        year, day, part = record["year"], record["day"], record["part"]
        if type(year) is int and type(day) is int and type(part) is int and part in (1, 2):
            return Puzzle(year, day), part
    except (ValueError, KeyError, TypeError, HarnessError):
        pass
    raise HarnessError("The saved day selection is invalid. Run just start YEAR DAY again.")


def resolve_selection(year: int | None, day: int | None, part: int | None) -> tuple[Puzzle, int]:
    if year is None:
        return current_selection()
    if day is None:
        raise HarnessError("Specify both YEAR and DAY, or use the current selection.")
    return Puzzle(year, day), part or 1


def existing_puzzles(year: int | None) -> list[Puzzle]:
    if year is not None and not 2015 <= year <= 9999:
        raise HarnessError("Use an Advent of Code year (2015 or later).")
    years = ROOT / "years"
    year_pattern = str(year) if year is not None else "[0-9][0-9][0-9][0-9]"
    puzzles = []
    for directory in sorted(years.glob(f"{year_pattern}/day[0-9][0-9]")):
        puzzle_year = int(directory.parent.name)
        day = int(directory.name[3:])
        if puzzle_year >= 2015 and 1 <= day <= 25 and any((directory / f"task{part}.py").is_file() for part in (1, 2)):
            puzzles.append(Puzzle(puzzle_year, day))
    return puzzles


def download_missing(puzzles: list[Puzzle]) -> Counter[str]:
    results: Counter[str] = Counter()
    if not puzzles:
        return results

    try:
        token = session_token()
    except (StopFetching, OSError) as error:
        print(f"Input setup: {error}", file=sys.stderr)
        results["failed"] = len(puzzles)
        return results

    for index, puzzle in enumerate(puzzles):
        if index:
            sleep(1)
        try:
            data = download_input(puzzle.year, puzzle.day, token)
            if data is None:
                print(f"{puzzle.label}: input unavailable")
                results["unavailable"] += 1
            else:
                written = write_file(puzzle.input_path, data)
                status = "downloaded" if written else "present"
                print(f"{puzzle.label}: input {status}")
                results[status] += 1
        except StopFetching as error:
            print(f"{puzzle.label}: {error}", file=sys.stderr)
            results["failed"] += 1
            results["skipped"] += len(puzzles) - index - 1
            break
        except (FetchError, OSError) as error:
            print(f"{puzzle.label}: {error}", file=sys.stderr)
            results["failed"] += 1
    return results


def fetch_inputs(puzzles: list[Puzzle]) -> int:
    results: Counter[str] = Counter()
    pending = []
    for puzzle in puzzles:
        path = puzzle.input_path
        if path.exists() or path.is_symlink():
            if path.is_file() and path.stat().st_size:
                print(f"{puzzle.label}: input present")
                results["present"] += 1
            else:
                print(
                    f"{puzzle.label}: {path.name} is empty or invalid. Move it aside to fetch again.", file=sys.stderr
                )
                results["failed"] += 1
        elif not puzzle.released:
            print(f"{puzzle.label}: not released yet")
            results["unavailable"] += 1
        else:
            pending.append(puzzle)
    results.update(download_missing(pending))
    fields = ("downloaded", "present", "unavailable", "failed", "skipped")
    print("Inputs: " + ", ".join(f"{results[field]} {field}" for field in fields))
    return int(bool(results["failed"]))


def load_solver(path: Path, module_name: str) -> Callable[..., object]:
    if not path.is_file():
        raise HarnessError(f"Solution file missing: {path.relative_to(ROOT)}.")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"Could not load {path.relative_to(ROOT)}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    solver = getattr(module, "solve", None)
    if not callable(solver):
        raise HarnessError(f"{path.relative_to(ROOT)} must define solve(input_data).")
    return solver


def read_input(path: Path) -> str:
    if not path.is_file() or not path.stat().st_size:
        raise HarnessError(f"Input missing or empty: {path.relative_to(ROOT)}.")
    return path.read_bytes().decode("utf-8")


def examples_for(puzzle: Puzzle, part: int, name: str | None) -> list[tuple[Path, str | None]]:
    manifest = puzzle.directory / "examples.toml"
    if not manifest.is_file():
        raise HarnessError(f"Add example cases in {manifest.relative_to(ROOT)}.")
    with manifest.open("rb") as source:
        entries = tomllib.load(source).get(f"part{part}", [])
    if not isinstance(entries, list):
        raise HarnessError(f"Use [[part{part}]] tables in {manifest.relative_to(ROOT)}.")
    examples = []
    for entry in entries:
        filename = entry.get("input") if isinstance(entry, dict) else None
        if not isinstance(filename, str) or Path(filename).name != filename or filename in ("", ".", ".."):
            raise HarnessError(f"Example entries in {manifest.relative_to(ROOT)} need a filename in examples/.")
        if name is not None and filename != name:
            continue
        expected = entry.get("expected")
        if expected is not None and type(expected) not in (int, str):
            raise HarnessError(f"Expected answer for {filename} must be a string or an integer.")
        examples.append((puzzle.directory / "examples" / filename, None if expected is None else str(expected)))
    if not examples:
        raise HarnessError(f"No matching examples for {puzzle.label} Part {part}. Check {manifest.relative_to(ROOT)}.")
    return examples


def run_solution(puzzle: Puzzle, part: int, *, sample: bool, example: str | None = None) -> int:
    if sample:
        cases = examples_for(puzzle, part, example)
    else:
        if not puzzle.input_path.is_file() or not puzzle.input_path.stat().st_size:
            raise HarnessError(f"Input missing for {puzzle.label}. Run just fetch {puzzle.year} {puzzle.day}.")
        cases = [(puzzle.input_path, None)]

    solver = load_solver(puzzle.solution_path(part), f"aoc_{puzzle.year}_{puzzle.day:02}_{part}")
    kwargs = {"is_test": sample} if "is_test" in inspect.signature(solver).parameters else {}
    failed = False
    for path, expected in cases:
        data = read_input(path)
        print(f"{puzzle.label} Part {part} · {path.relative_to(puzzle.directory)}")
        result = str(solver(data, **kwargs))
        print(f"Result: {result}")
        if expected is not None and result != expected:
            print(f"Sample mismatch. Expected: {expected}", file=sys.stderr)
            failed = True
        elif sample:
            print("Matches expected result." if expected is not None else "No expected answer configured.")
    return int(failed)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    auth = commands.add_parser("auth", help="find and verify the Advent of Code session in Chrome")
    auth.add_argument("--manual", action="store_true", help="paste the session cookie at a hidden prompt")
    init = commands.add_parser("init", help="fetch missing inputs for existing days")
    init.add_argument("year", type=int, nargs="?")
    for name, help_text in [
        ("start", "prepare a day and select its first part"),
        ("fetch", "fetch the input for an existing day"),
    ]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("year", type=int)
        command.add_argument("day", type=int)

    part = commands.add_parser("part", help="select a part of the current day")
    part.add_argument("part", type=int, choices=(1, 2))
    for name, help_text in [("run", "run against real input"), ("sample", "run against examples")]:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("year", type=int, nargs="?")
        command.add_argument("day", type=int, nargs="?")
        command.add_argument("part", type=int, nargs="?", choices=(1, 2))
        if name == "sample":
            command.add_argument("--example", metavar="FILENAME")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        match args.command:
            case "auth":
                return authenticate(manual=args.manual)
            case "init":
                puzzles = existing_puzzles(args.year)
                if not puzzles:
                    raise HarnessError("No day folders found. Create one with just start YEAR DAY.")
                return fetch_inputs(puzzles)
            case "start":
                puzzle = Puzzle(args.year, args.day)
                scaffold(puzzle)
                select(puzzle, 1)
                return fetch_inputs([puzzle])
            case "fetch":
                puzzle = Puzzle(args.year, args.day)
                if not puzzle.directory.is_dir():
                    raise HarnessError(f"Puzzle folder missing. Run just start {puzzle.year} {puzzle.day}.")
                return fetch_inputs([puzzle])
            case "part":
                puzzle, _ = current_selection()
                select(puzzle, args.part)
                return 0
            case _:
                puzzle, part = resolve_selection(args.year, args.day, args.part)
                return run_solution(
                    puzzle, part, sample=args.command == "sample", example=getattr(args, "example", None)
                )
    except (FetchError, HarnessError, OSError, tomllib.TOMLDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
