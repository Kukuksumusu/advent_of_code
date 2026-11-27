# Advent of Code

Python solutions and a shared runner. Each puzzle lives under `years/YYYY/dayNN/`.
Open a day's README for its official puzzle and example descriptions.

## Set up a checkout

Install [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).
Sign in to [Advent of Code](https://adventofcode.com/) in Chrome with the
account you want to use for inputs.

```sh
just auth          # Find your Advent of Code session in Chrome and confirm the account
just init          # Sync dependencies and fetch missing inputs for existing days
just init 2025     # Restore inputs for one year
```

`just auth` checks Chrome's cookie store and may prompt for Keychain access
on macOS. It verifies the session with Advent of Code and saves it in
`~/.config/aocd/token` (or `$XDG_CONFIG_HOME/aocd/token`) after you confirm
the account. Rerun it when the session expires. `AOC_SESSION`, if set, takes precedence.

If Chrome's session is unavailable, open **Application → Storage → Cookies**
in Chrome DevTools, select `https://adventofcode.com`, and copy the value of
the `session` cookie. Run `just auth-manual` and paste it at the hidden prompt.

Inputs go in each day's ignored `input.txt`. Existing files are reused and
unreleased or unavailable days are skipped. Move a cached input aside before
fetching it for a different account. Run `just init` again to resume interrupted
downloads, or use `just fetch YEAR DAY` for one day.

## Work on a puzzle

```sh
just start 2026 1  # Create missing files, select Part 1, and fetch the input
just sample        # Run examples for the selected part
just run           # Run the selected part against its real input
just part 2        # Switch the current day to Part 2
```

`just start` preserves existing files. It can scaffold a day before release.
Run or sample a different puzzle without changing the selection using
`just run YEAR DAY [PART]` or `just sample YEAR DAY [PART]`.

Implement `solve(input_data: str) -> int | str` in `task1.py` or `task2.py`.
Solutions can take an optional `is_test: bool = False` argument.

### Examples

`just start` creates an empty `examples/sample.txt` and an `examples.toml`
template. Paste the example input into `sample.txt`, then uncomment and fill in
`expected` for the relevant part. Both parts can use the same file. If Part 2
has a different example, add its file under `examples/` and update its `input`
entry. Either part can have several cases. Omit `expected` to run a case without
checking its result.

```toml
[[part1]]
input = "sample.txt"
expected = "42"

[[part2]]
input = "sample.txt"
expected = "84"
```

Use `just sample --example sample.txt` to run one case from the terminal.

### VS Code

Open the repository root with the Python and Python Debugger extensions
installed. If you already selected an interpreter for this workspace, use
**Python: Select Interpreter** to select the project's `.venv`.

Select **AoC · Sample** or **AoC · Real Input** in Run and Debug and press **F5**.
Both launch configurations use the selection saved by `just start` and
`just part`. Set breakpoints in the solution as usual. Both configurations run
locally and **AoC · Real Input** runs directly against `input.txt`.
A sample mismatch is reported in the integrated terminal and the debug session
finishes. In the terminal, `just sample` returns a failing exit status on a mismatch.

### Review a solution with Codex

Send this message in the Codex VS Code chat:

```text
/review-aoc
```

The coach uses the puzzle and part selected with `just start` and `just part`.
You can name a solution file or select the skill explicitly with `$review-aoc`.
The coach explains complexity, offers optimization hints, and may suggest
small readability edits in chat.

## Harness checks

```sh
just test  # Harness tests, including input setup and both run modes
just check # Ruff and mypy
```
