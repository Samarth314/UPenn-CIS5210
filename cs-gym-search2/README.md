# CS Gym — Expectimax & Alpha-Beta II

Sixteen problems, four tracks: expectimax fundamentals, new angles on
alpha-beta (not a repeat of `cs-gym-alphabeta`), then homework-level
versions of both. Python runs in the browser via Pyodide — nothing is
uploaded anywhere.

## Running it

```bash
python3 cs-gym-search2/serve.py
```

Then open <http://localhost:5181>. Port differs from the other three gyms
(5177, 5178, 5179/5180) so they can all run side by side.

## The tracks

**Expectimax Basics** — `chance-node-average` (a chance node is a plain
mean), `expectimax-value` (minimax with CHANCE replacing MIN),
`weighted-expectimax` (non-uniform probabilities, a genuinely different
node type), `expectimax-horizon` (`(move, value, leaves)`, CHANCE nodes
never report a move).

**Alpha-Beta Basics II** — deliberately *not* a repeat of the first
alpha-beta gym: `total-node-visits` (every node, not just leaves),
`cutoff-count` (how many times pruning actually fired, not how many
calls returned), `negamax` (one function instead of two, via negation),
`iterative-deepening-ab` (search depth 1, then 2, then 3, keeping every
result).

**Expectimax, Homework-Style** — `dominoes-vs-random` and
`triominoes-vs-random` (`get_best_move` against an opponent who plays
`get_random_move`, not adversarially), `take-away-vs-random` (the
win/loss value becomes a genuine expectation), `pig-bank-or-roll` (a
real six-sided die — chance nodes as actual randomness, not a stand-in
for an opponent).

**Alpha-Beta, Homework-Style II** — `ltromino-game` (4 rotations, not 2
directions), `blocked-dominoes-game` (a third cell state — occupancy
needs `== EMPTY`, not truthiness), `scoring-dominoes-game` (most pieces
placed wins, not last-to-move — and a player can be stuck in their own
orientation while the game keeps going, which needs an explicit pass
rule the homework never had to define), `free-triominoes-game` (two
earlier variant ideas stacked on top of each other).

340 points across 80 tests. Every homework-style problem hands you
instrumented test cases that recognize known wrong turns (minimax's
worst-case model instead of averaging, a flat move-count formula that's
always zero, no pruning, strict cut-offs, ties breaking the wrong way,
an off-by-one depth) and name the mistake rather than just failing.

## Working on the problem bank

```bash
python3 cs-gym-search2/build_problems.py
```

Runs every reference solution against its own tests before writing
`problems.json` — a broken problem can't ship. Every homework-style
oracle is a plain function operating on board lists, independent of the
class a learner writes, so a broken attempt can't corrupt an expected
answer.
