set positional-arguments

# List the available commands
default:
    @just --list

# Find and verify the Advent of Code session in Chrome
auth:
    @uv run --locked --group chrome-auth python aoc.py auth

# Paste an Advent of Code session cookie at a hidden prompt
auth-manual:
    @uv run --locked python aoc.py auth --manual

# Install dependencies and restore missing inputs (optionally for one year)
init *year:
    @uv run --locked python aoc.py init "$@"

# Prepare a day and select it in the debugger
start year day:
    @uv run --locked python aoc.py start "$@"

# Restore the input for one existing day
fetch year day:
    @uv run --locked python aoc.py fetch "$@"

# Select Part 1 or 2 of the current day
part part:
    @uv run --locked python aoc.py part "$@"

# Run real input for the current selection or an explicit YEAR DAY [PART]
run *args:
    @uv run --locked python aoc.py run "$@"

# Run examples for the current selection or an explicit YEAR DAY [PART]
sample *args:
    @uv run --locked python aoc.py sample "$@"

fix *args:
    @uv run --locked ruff check aoc.py scripts tests years --fix "$@"
    @uv run --locked ruff format aoc.py scripts tests years

check:
    @uv run --locked ruff check aoc.py scripts tests years
    @uv run --locked mypy aoc.py scripts tests --explicit-package-bases
    @for year in years/[0-9][0-9][0-9][0-9]; do \
        [ -d "$year" ] || continue; \
        MYPYPATH="$year" uv run --locked mypy --explicit-package-bases --cache-dir ".mypy_cache/${year##*/}" "$year" || exit; \
    done

test:
    @uv run --locked python -m unittest discover -s tests
