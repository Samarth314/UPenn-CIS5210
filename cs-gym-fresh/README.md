# CS Gym — Uninformed Search (blank copy)

A clean-slate duplicate of `cs-gym/`. Same fourteen problems, same runtime,
same tests — but every editor starts at the starter code and nothing is marked
solved, so you can work the whole set again from scratch.

Your earlier solutions live in `cs-gym/` and are untouched by anything you do
here. The two are completely separate: they run on different ports, so the
browser treats them as different origins and keeps their saved work apart.

Fourteen practice problems in the same shape as Homework 2 (n-queens, Lights
Out, linear disk movement), but none of them are the homework problems. Python
runs in the browser via Pyodide, so solutions execute and get graded locally —
nothing is uploaded anywhere.

## Running it

```bash
python3 cs-gym-fresh/serve.py
```

Then open <http://localhost:5178>. The worked copy runs on 5177, so both can
be open at the same time without their progress mixing. The first load pulls Pyodide (~10 MB) from
the jsDelivr CDN and caches it; after that only the style checker needs
network access.

`serve.py` is a static file server plus one extra endpoint, `/progress`, which
is what saves your work to disk. It binds to localhost only, since it accepts
writes.

Note that the **Solution** tab still holds the reference solutions, same as in
the worked copy — they are one deliberate click away, not filled in.

## Saving your work

Every edit is written to `cs-gym-fresh/progress.json` about half a second after you
stop typing, along with which problems you have solved. The header shows
`saved to disk` when that lands. Clearing your browser storage, switching
browsers, or closing the tab costs you nothing — the next load reads the file
back.

The file is plain JSON and is tracked in git, so committing it versions your
solutions along with the gym itself:

```bash
git add cs-gym-fresh/progress.json && git commit -m "gym progress"
```

Note that this repository is public, so committed solutions are publicly
readable. Add `progress.json` to `cs-gym/.gitignore` if you would rather keep
them local.

Writes are **additive**: the server merges each snapshot into what is already
saved rather than replacing the file, so a browser with empty storage can
never wipe out work saved from somewhere else. Per problem, the newer copy
wins. The previous version is kept alongside as `progress.json.bak`.

**Export** downloads a dated backup, **Import** restores one — use those to
move progress between machines without going through git. If you run the gym under a plain
`python3 -m http.server` instead, there is no `/progress` endpoint; the header
reads `browser only` and everything falls back to localStorage.

## What is in here

| File | Purpose |
| --- | --- |
| `index.html`, `styles.css`, `app.js` | the site: problem list, editor, console |
| `serve.py` | the local server, including the progress-saving endpoint |
| `worker.js` | Pyodide in a web worker, so a runaway search can be killed |
| `progress.json` | your saved code and solved marks |
| `problems.json` | the generated problem bank — do not edit by hand |
| `build_problems.py` | the source of truth for every problem |

## The problems

**Counting & Backtracking** — Sizing the Search Space, N-Rooks: Legal
Position?, N-Rooks: Enumerate by DFS, Queens on a Damaged Board, Amazons.

**Toggle Puzzles** — Cross Out, Tri-State Lights, Toggle Ring.

**Movement Puzzles** — Jumping Disks, Toads and Frogs, Mini Sliding Tiles.

**Classic Searches** — Water Jugs, Knight's Shortest Path, Missionaries and
Cannibals.

Every solver problem demands an *optimal* answer, and the tests check optimal
length against a move count computed at build time — so a search that finds
*a* solution still fails if it is not a *shortest* solution.

## Working on the problem bank

`build_problems.py` holds each problem's statement, starter code, hints, tests
and a reference solution. It runs every reference solution against its own
tests before writing `problems.json`, so a broken problem cannot ship:

```bash
python3 cs-gym/build_problems.py
```

Constants that are themselves search results — optimal move counts, boards
that are provably unsolvable — are computed by oracles at the top of each
section and spliced into the test source through `@@NAME@@` markers, rather
than being hard-coded by hand.

## Controls

- **Run tests** (`Cmd/Ctrl+Enter`) — grade the current problem.
- **Run** — execute the editor as a plain script; `print` goes to the console.
- **Style** — run `pycodestyle` on default settings, the same check the
  Gradescope autograder uses for the style points.
- **Stop** — the Run tests button becomes Stop while something is running.
  It kills the interpreter, which is the only way out of an infinite loop.

Code and solved state are saved per problem, first to `localStorage` and then
to `cs-gym-fresh/progress.json`. To start over, delete `progress.json` and run
`localStorage.clear()` in the browser console.
