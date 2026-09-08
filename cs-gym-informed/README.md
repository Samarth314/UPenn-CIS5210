# CS Gym — Informed Search

Eleven practice problems in the same shape as Homework 3 (A*, admissible
heuristics, iterative deepening). All but one are new problems rather than the
homework itself; the exception is *Every Optimal Way to Solve the Tiles*, which
is deliberately Homework 3's own IDDFS solver, kept for a second pass from a
blank editor.
Python runs in the browser via Pyodide, so solutions execute and get graded
locally — nothing is uploaded anywhere.

This is the sibling of `cs-gym`, which covers the uninformed searches from
Homework 2. Same runtime, same controls, different problem bank.

## Running it

```bash
python3 cs-gym-informed/serve.py
```

Then open <http://localhost:5178>. The port differs from `cs-gym` (5177) so
both gyms can run side by side. The first load pulls Pyodide (~10 MB) from the
jsDelivr CDN and caches it; after that only the style checker needs network
access.

`serve.py` is a static file server plus one extra endpoint, `/progress`, which
is what saves your work to disk. It binds to localhost only, since it accepts
writes.

## Saving your work

Every edit is written to `cs-gym-informed/progress.json` about half a second
after you stop typing, along with which problems you have solved. The header
shows `saved to disk` when that lands. Clearing your browser storage, switching
browsers, or closing the tab costs you nothing — the next load reads the file
back.

Writes are **additive**: the server merges each snapshot into what is already
saved rather than replacing the file, so a browser with empty storage can never
wipe out work saved from somewhere else. The previous version is kept alongside
as `progress.json.bak`.

Note that this repository is public, so committed solutions are publicly
readable. Add `progress.json` to `cs-gym-informed/.gitignore` if you would
rather keep them local.

## The problems

**Heuristics** — Counting What Is Out of Place, Manhattan Distance to an
Arbitrary Goal, Does This Heuristic Overestimate?

**A\* Machinery** — A Queue That Never Compares Payloads, Cheapest Crossing (No
Heuristic Yet).

**A\* Solvers** — The Route Itself With a Heuristic, Knight Across a Damaged
Board, Sorting Pancakes by the Spatula.

**Iterative Deepening** — Every Shortest Way to Open the Lock, Hanoi Between
Two Arbitrary Piles, Every Optimal Way to Solve the Tiles.

190 points across 58 tests.

Every solver problem demands an *optimal* answer, and the tests check optimal
cost against a value computed at build time — so a search that finds *a*
solution still fails if it is not a *cheapest* one. Several problems also
verify directly that the suggested heuristic never overestimates, by
brute-forcing the true distance across an entire small state space.

## What the problems are actually teaching

Each one isolates a mistake that is easy to make and hard to see:

- **Counting What Is Out of Place** — why the blank tile is excluded. Count it
  and the heuristic overestimates, and A* stops being optimal.
- **Manhattan Distance to an Arbitrary Goal** — the goal is a parameter, so you
  cannot hard-code row-major arithmetic. Build the lookup once, outside the
  loop.
- **Does This Heuristic Overestimate?** — the mistake that produces no error
  message: an inadmissible heuristic just quietly returns a longer path. On a
  small puzzle you can settle it by brute force, and the tests use the two real
  cases — counting the blank in Manhattan distance, and forgetting to halve the
  disk-distance sum.
- **A Queue That Never Compares Payloads** — ties on `f` are the norm, and a
  bare `(cost, state)` tuple raises `TypeError` the moment two costs match.
- **Cheapest Crossing** — on uneven terrain the shortest route and the cheapest
  route are different, so BFS gives the wrong answer.
- **The Route Itself** — scaling a step-counting heuristic to a cost model, and
  rebuilding a path from parent pointers instead of copying lists.
- **Knight Across a Damaged Board** — a three-way max that stays a lower bound
  however the board is damaged.
- **Sorting Pancakes** — the gap heuristic, where the admissibility argument is
  the interesting part.
- **Every Shortest Way to Open the Lock** — iterative deepening that collects
  *all* optimal solutions, and why you must not carry a visited set across
  depths.
- **Hanoi Between Two Arbitrary Piles** — the `2**n - 1` formula does not apply
  once the endpoints are arbitrary.
- **Every Optimal Way to Solve the Tiles** — the homework problem itself. Two
  traps decide whether it terminates: the helper must recurse on the successor
  board, and no visited set may be carried across depths.

## Working on the problem bank

`build_problems.py` holds each problem's statement, starter code, hints, tests
and a reference solution. It runs every reference solution against its own
tests before writing `problems.json`, so a broken problem cannot ship:

```bash
python3 cs-gym-informed/build_problems.py
```

Constants that are themselves search results — optimal flip counts, knight
distances, how many shortest lock combinations exist — are computed by oracles
at the top of each section and spliced into the test source through `@@NAME@@`
markers, rather than being hard-coded by hand.

## What is in here

| File | Purpose |
| --- | --- |
| `index.html`, `styles.css`, `app.js` | the site: problem list, editor, console |
| `serve.py` | the local server, including the progress-saving endpoint |
| `worker.js` | Pyodide in a web worker, so a runaway search can be killed |
| `progress.json` | your saved code and solved marks |
| `problems.json` | the generated problem bank — do not edit by hand |
| `build_problems.py` | the source of truth for every problem |

## Controls

- **Run tests** (`Cmd/Ctrl+Enter`) — grade the current problem.
- **Run** — execute the editor as a plain script; `print` goes to the console.
- **Style** — run `pycodestyle` on default settings, the same check the
  Gradescope autograder uses for the style points.
- **Stop** — the Run tests button becomes Stop while something is running. It
  kills the interpreter, which is the only way out of an infinite loop. Worth
  knowing on the iterative-deepening problems, where a missing depth bound runs
  forever.
