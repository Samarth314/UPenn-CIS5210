# CS Gym — Game Trees & Alpha-Beta

Thirteen practice problems building up to Homework 4 (recursion on trees,
minimax, alpha-beta pruning, `get_best_move`). None of them are the homework
problem itself, except the shape of it: `TriominoesGame` is `DominoesGame`
with 1x3 pieces, and `TakeAwayGame` is a from-scratch two-player game with
no `vertical` flag at all.
Python runs in the browser via Pyodide, so solutions execute and get graded
locally — nothing is uploaded anywhere.

This is the sibling of `cs-gym` (uninformed search) and `cs-gym-informed`
(A* and iterative deepening). Same runtime, same controls, different problem
bank.

## Running it

```bash
python3 cs-gym-alphabeta/serve.py
```

Then open <http://localhost:5179>. The port differs from the other two gyms
(5177, 5178) so all three can run side by side. The first load pulls Pyodide
(~10 MB) from the jsDelivr CDN and caches it; after that only the style
checker needs network access.

`serve.py` is a static file server plus one extra endpoint, `/progress`,
which is what saves your work to disk. It binds to localhost only, since it
accepts writes.

## Saving your work

Every edit is written to `cs-gym-alphabeta/progress.json` about half a second
after you stop typing, along with which problems you have solved. The header
shows `saved to disk` when that lands. Clearing your browser storage,
switching browsers, or closing the tab costs you nothing — the next load
reads the file back.

Writes are **additive**: the server merges each snapshot into what is
already saved rather than replacing the file, so a browser with empty
storage can never wipe out work saved from somewhere else. The previous
version is kept alongside as `progress.json.bak`.

Note that this repository is public, so committed solutions are publicly
readable. Add `progress.json` to `cs-gym-alphabeta/.gitignore` if you would
rather keep them local.

## The problems

**Recursion on Trees** — Counting Nodes, Counting Leaves; How Deep It Goes,
and What It Holds; Leaves, One at a Time; The Route to the Best Leaf; Where a
Depth Limit Stops.

**Minimax** — Whose Turn Is It at This Level?; The Best Move Changes With
the Horizon.

**Alpha-Beta in Code** — Pruning You Can Actually See; Counting What the
Search Evaluated; `get_best_move` on a Bare Tree; Name the Leaves It Never
Read.

**Homework-Style Games** — Dominoes, One Square Longer (`TriominoesGame`,
1x3 pieces); Last Stone Wins (a take-away game with no `vertical` flag).

220 points across 65 tests.

Every problem in Alpha-Beta in Code and Homework-Style Games hands you
instrumented `Node`/game objects that record exactly which leaves your
search reads, or checks the search's move/value/leaf-count triple against
known wrong answers (no pruning, strict cut-offs, ties breaking the wrong
way, an off-by-one depth) — so a search that happens to return the right
number for the wrong reason still fails, and the failure names the mistake.

## What the problems are actually teaching

- **Counting Nodes, Counting Leaves** — why `count_nodes` needs no explicit
  base case but `count_leaves` does.
- **How Deep It Goes, and What It Holds** — `max()` over children is a MAX
  node in disguise; a leaf has no children to take the max over.
- **Leaves, One at a Time** — `yield from`, and why a search that stops
  early should never pay for the rest of the tree.
- **The Route to the Best Leaf** — carrying the *move* back up alongside
  the value, with strict `>` for the homework's left-to-right tie-break.
- **Where a Depth Limit Stops** — the leaf count from `get_best_move`, with
  pruning switched off, so you see what alpha-beta is saving you from.
- **Whose Turn Is It at This Level?** — the one flipped argument that makes
  minimax alternate instead of collapsing into a single max or min.
- **The Best Move Changes With the Horizon** — `(move, value, leaves)`
  exactly as the homework returns it, at three different search depths.
- **Pruning You Can Actually See** — instrumented nodes catch a search that
  gets the right value while reading every leaf anyway.
- **Counting What the Search Evaluated** — the leaf count is the number
  that exposes a broken alpha/beta update when the value still looks right.
- **`get_best_move` on a Bare Tree** — the homework's exact recursive
  structure, isolated from `DominoesGame` so only the search can be wrong.
- **Name the Leaves It Never Read** — tracking pruned leaves by identity,
  not value, since two different leaves can hold the same number.
- **Dominoes, One Square Longer** — every bound in `is_legal_move` moves by
  one square, and the evaluation must stay pinned to the caller's side.
- **Last Stone Wins** — a game with no `vertical` flag, where the
  evaluation's sign depends on whether the empty pile lands on a MAX or MIN
  node.

## Working on the problem bank

`build_problems.py` holds each problem's statement, starter code, hints,
tests and a reference solution. It runs every reference solution against its
own tests before writing `problems.json`, so a broken problem cannot ship:

```bash
python3 cs-gym-alphabeta/build_problems.py
```

Every oracle — minimax values, leaf counts, which leaves alpha-beta reads —
runs against plain nested-list tree specs (`build()`/`build_tracked()` turn
those into `Node` objects at test time), never against a learner's own
`Node` class, so a broken solution attempt can't corrupt an expected answer.

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
- **Run** — execute the editor as a plain script; `print` goes to the
  console.
- **Style** — run `pycodestyle` on default settings, the same check the
  Gradescope autograder uses for the style points.
- **Stop** — the Run tests button becomes Stop while something is running.
  It kills the interpreter, which is the only way out of an infinite loop —
  worth knowing on `TakeAwayGame`/`TriominoesGame` if `get_best_move` never
  reaches its base case.
