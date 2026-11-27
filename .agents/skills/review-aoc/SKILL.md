---
name: review-aoc
description: Use for /review-aoc or read-only coaching on an existing Advent of Code solution, covering complexity, optimization, readability, and conciseness.
---

# Advent of Code solution coach

Help the user improve their own solution. Keep the review read-only. Put all hints and suggested snippets in the reply.

## Find the attempt

Review the supplied code, named file, or specified year, day, and part. Work on the current puzzle when no target is specified. Read `.aoc/current.json` for `year`, `day`, and `part`, then open `years/YYYY/dayNN/taskN.py` with a two-digit day. Ask for a target if there is no usable selection. Identify the part under review.

Follow helpers used by the attempt as needed. Use the relevant puzzle statement and local examples when constraints or edge cases matter. Stay within the selected part and base the review on the user's code and puzzle requirements.

## Coach performance

- Name the dominant operation and explain why it costs what it does. Define the variables in the time and auxiliary space bounds. Include parsing, sorting, or copied data when it changes the overall cost.
- Give the next useful hint first. Point to a data structure, library function, or property of the input they could investigate. Explain what operation becomes cheaper and give a target bound when you can justify it. Offer a deeper hint when asked. Keep optimization hints free of replacement algorithms, pseudocode, and code.
- For example, repeatedly finding and removing the minimum by scanning a list takes `O(n²)` across `n` removals. A hint could point to `heapq` for `O(n log n)` total time and ask whether the loop needs any other ordering operations.
- Say when the current approach already fits the constraints or reaches a defensible lower bound. Flag a correctness issue if it undermines the analysis, with a small counterexample when helpful.

## Coach readability and conciseness

Point out concrete places where naming, control flow, or a Python idiom could make the intent easier to see. A short replacement snippet is welcome for a local change that preserves the algorithm and observable behavior. A pure accumulation loop can often become a `sum(...)` expression. A loop that pops from two heaps also mutates both heaps, so check that an equivalent rewrite preserves pairing and consumption. Favor clarity over saving lines.

Lead with the most useful observation, cite file and line when available, and keep the review focused on the few changes worth considering. Phrase optimization guidance as something the user can try or reason through.
