"""Build the CS Gym problem bank.

Every problem carries a reference solution and a test suite.  This script runs
each reference solution against its own tests before emitting problems.json, so
a broken problem can never reach the site.  Some tests need constants that are
themselves search results (optimal move counts, provably unsolvable boards);
those are computed here and spliced into the test source at build time.
"""

import json
import os
from collections import deque
from itertools import product
from math import comb, factorial

PROBLEMS = []


def problem(**kwargs):
    PROBLEMS.append(kwargs)


def T(name, src, **consts):
    """A single test.  ``@@NAME@@`` markers are replaced by build-time constants."""
    for key, value in consts.items():
        marker = "@@%s@@" % key
        assert marker in src, "unused constant %s in test %r" % (key, name)
        src = src.replace(marker, repr(value))
    assert "@@" not in src, "unresolved constant in test %r" % name
    return {"name": name, "src": src.strip("\n")}


# --------------------------------------------------------------------------
# Track 1 -- placement counting and depth-first backtracking
# --------------------------------------------------------------------------

problem(
    id="placement-counting",
    track="Counting & Backtracking",
    title="Sizing the Search Space",
    difficulty="warmup",
    points=5,
    blurb="Count board configurations three ways and watch the search space collapse.",
    statement="""
<p>Before writing a search, it pays to know how big the space you are
searching actually is. Implement three counting functions for an
<em>n</em> &times; <em>n</em> board. All pieces are indistinguishable, and
for these functions pieces <strong>are</strong> allowed to attack each other
unless stated otherwise.</p>

<ul>
  <li><code>num_placements_all(n, k)</code> &mdash; the number of ways to drop
      <code>k</code> pieces onto the <code>n * n</code> squares, no
      restrictions at all.</li>
  <li><code>num_placements_one_per_row(n)</code> &mdash; the number of ways to
      place <code>n</code> pieces so that every row holds exactly one.</li>
  <li><code>num_placements_rooks(n)</code> &mdash; the number of ways to place
      <code>n</code> <em>non-attacking</em> rooks, i.e. exactly one per row
      <em>and</em> exactly one per column.</li>
</ul>

<p>Compare the three numbers for <code>n = 8</code>. The gap between the first
and the second is the entire reason the rest of this track represents a board
as a list of column indices.</p>
""",
    examples="""
>>> num_placements_all(3, 3)
84
>>> num_placements_all(8, 8)
4426165368
>>> num_placements_one_per_row(3)
27
>>> num_placements_one_per_row(8)
16777216
>>> num_placements_rooks(3)
6
>>> num_placements_rooks(8)
40320
""",
    starter="""
def num_placements_all(n, k):
    pass


def num_placements_one_per_row(n):
    pass


def num_placements_rooks(n):
    pass
""",
    hints=[
        "Choosing k squares out of n*n with no order and no repetition is a "
        "binomial coefficient. math.comb does it exactly, without floats.",
        "One piece per row means n independent choices of column, one per row.",
        "Non-attacking rooks pin down a bijection from rows to columns -- that "
        "is exactly a permutation of the columns.",
    ],
    solution="""
from math import comb, factorial


def num_placements_all(n, k):
    return comb(n * n, k)


def num_placements_one_per_row(n):
    return n ** n


def num_placements_rooks(n):
    return factorial(n)
""",
    tests=[
        T("num_placements_all matches n*n choose k", """
from math import comb
assert num_placements_all(3, 3) == comb(9, 3) == 84
assert num_placements_all(8, 8) == comb(64, 8) == 4426165368
assert num_placements_all(4, 0) == 1
assert num_placements_all(4, 1) == 16
assert num_placements_all(2, 4) == 1
assert num_placements_all(2, 5) == 0
"""),
        T("num_placements_one_per_row counts n**n", """
assert num_placements_one_per_row(1) == 1
assert num_placements_one_per_row(3) == 27
assert num_placements_one_per_row(8) == 16777216
assert num_placements_one_per_row(12) == 12 ** 12
"""),
        T("num_placements_rooks counts permutations", """
from math import factorial
assert num_placements_rooks(1) == 1
assert num_placements_rooks(3) == 6
assert num_placements_rooks(8) == 40320
assert num_placements_rooks(20) == factorial(20)
"""),
        T("results are exact integers, not floats", """
for value in (num_placements_all(30, 4), num_placements_one_per_row(30),
              num_placements_rooks(30)):
    assert isinstance(value, int), "expected an int, got %r" % type(value)
"""),
    ],
)


problem(
    id="n-rooks-valid",
    track="Counting & Backtracking",
    title="N-Rooks: Legal Position?",
    difficulty="easy",
    points=10,
    blurb="The goal test for a rook placement, on complete and partial boards alike.",
    statement="""
<p>A board is represented as a list of integers, where the <code>i</code>-th
entry is the column of the rook sitting in row <code>i</code>. A list of
length <code>n</code> describes a complete board; a shorter list describes a
<strong>partial</strong> board where only the first few rows have been
filled.</p>

<p>Write <code>n_rooks_valid(board)</code>, which returns <code>True</code> if
no rook can attack another and <code>False</code> otherwise. A rook attacks
along its row and its column only &mdash; diagonals are irrelevant, which is
exactly what makes this an easier cousin of n-queens.</p>

<p>Note that the representation already guarantees one rook per row, so the
row constraint is satisfied for free. The board size is <em>not</em> passed in;
infer whatever you need from the list itself.</p>
""",
    examples="""
>>> n_rooks_valid([0, 0])
False
>>> n_rooks_valid([0, 1])
True
>>> n_rooks_valid([1, 0, 2])
True
>>> n_rooks_valid([2, 0, 2])
False
>>> n_rooks_valid([])
True
""",
    starter="""
def n_rooks_valid(board):
    pass
""",
    hints=[
        "Only one thing can go wrong: two rooks sharing a column.",
        "A set of the columns is shorter than the board exactly when some "
        "column repeats.",
        "The empty board and a one-rook board are both trivially valid -- make "
        "sure your code does not special-case them into a crash.",
    ],
    solution="""
def n_rooks_valid(board):
    return len(set(board)) == len(board)
""",
    tests=[
        T("small hand-checked positions", """
assert not n_rooks_valid([0, 0])
assert n_rooks_valid([0, 1])
assert n_rooks_valid([1, 0, 2])
assert not n_rooks_valid([2, 0, 2])
assert n_rooks_valid([3, 1, 0, 2])
"""),
        T("empty and single-row boards are valid", """
assert n_rooks_valid([])
assert n_rooks_valid([0])
assert n_rooks_valid([7])
"""),
        T("diagonals do not matter", """
assert n_rooks_valid([0, 1, 2, 3])
assert n_rooks_valid([3, 2, 1, 0])
assert n_rooks_valid([0, 1, 2])
"""),
        T("agrees with brute force on every board up to n=4", """
from itertools import product


def _expected(board):
    return len(set(board)) == len(board)


for n in range(1, 5):
    for size in range(1, n + 1):
        for board in product(range(n), repeat=size):
            got = n_rooks_valid(list(board))
            assert bool(got) == _expected(board), \\
                "n_rooks_valid(%r) returned %r" % (list(board), got)
"""),
    ],
)


problem(
    id="n-rooks-solutions",
    track="Counting & Backtracking",
    title="N-Rooks: Enumerate by DFS",
    difficulty="medium",
    points=15,
    blurb="Depth-first search over rows, extending one partial board at a time.",
    statement="""
<p>Write <code>n_rooks_solutions(n)</code>, returning a list of every valid
placement of <code>n</code> non-attacking rooks on an <code>n</code> &times;
<code>n</code> board, using the list-of-columns representation from the
previous problem. Any ordering of the results is accepted.</p>

<p>Implement it as a <strong>depth-first search</strong>: start from the empty
board and repeatedly extend the partial solution by placing a rook in the next
empty row. A recursive helper makes this natural &mdash; a module-level
generator, a closure that appends to a list, anything you like. Only
<code>n_rooks_valid</code> and <code>n_rooks_solutions</code> are graded, so
shape the recursion however you find clearest.</p>

<p>Sanity check: there are exactly <code>n!</code> solutions, so
<code>len(n_rooks_solutions(6)) == 720</code>. Resist the urge to call
<code>itertools.permutations</code> &mdash; the point is the recursion, and the
next two problems have no such shortcut.</p>
""",
    examples="""
>>> n_rooks_solutions(2)
[[0, 1], [1, 0]]
>>> n_rooks_solutions(3)
[[0, 1, 2], [0, 2, 1], [1, 0, 2], [1, 2, 0], [2, 0, 1], [2, 1, 0]]
>>> len(n_rooks_solutions(6))
720
""",
    starter="""
def n_rooks_valid(board):
    pass


def n_rooks_solutions(n):
    pass
""",
    hints=[
        "Base case: len(board) == n means board is already a full solution, so "
        "yield it (yield a copy, not the list you keep mutating).",
        "Recursive case: for each column, append it, recurse if the extended "
        "board is still valid, then pop it back off.",
        "Checking validity of the whole board each step is O(n) work per node "
        "and still fast enough -- but carrying a set of used columns down the "
        "recursion is the version you want for n-queens later.",
    ],
    solution="""
def n_rooks_valid(board):
    return len(set(board)) == len(board)


def n_rooks_helper(n, board):
    if len(board) == n:
        yield list(board)
        return
    for col in range(n):
        board.append(col)
        if n_rooks_valid(board):
            yield from n_rooks_helper(n, board)
        board.pop()


def n_rooks_solutions(n):
    return list(n_rooks_helper(n, []))
""",
    tests=[
        T("returns a list of lists of the right shape", """
sols = n_rooks_solutions(3)
assert isinstance(sols, list), "expected a list, got %r" % type(sols)
for board in sols:
    assert len(board) == 3
    assert all(isinstance(c, int) for c in board)
"""),
        T("counts match n! for n = 0..6", """
from math import factorial
for n in range(0, 7):
    sols = n_rooks_solutions(n)
    assert len(sols) == factorial(n), \\
        "n=%d gave %d solutions, expected %d" % (n, len(sols), factorial(n))
"""),
        T("every board is a permutation, and none repeat", """
from math import factorial
for n in range(1, 7):
    seen = set()
    for board in n_rooks_solutions(n):
        assert sorted(board) == list(range(n)), "%r is not a permutation" % (board,)
        seen.add(tuple(board))
    assert len(seen) == factorial(n), "n=%d produced duplicate boards" % n
"""),
        T("each solution is its own list, not a shared reference", """
sols = n_rooks_solutions(4)
assert len(sols) == 24
sols[0][0] = 99
shared = sum(1 for board in sols if board[0] == 99)
assert shared == 1, \
    "%d boards changed at once -- append a copy, not the board you mutate" % shared
"""),
        T("repeated calls do not leak state into each other", """
first = [list(b) for b in n_rooks_solutions(4)]
second = [list(b) for b in n_rooks_solutions(4)]
assert first == second, "two identical calls disagreed"
scratch = n_rooks_solutions(4)
scratch[0][0] = 99
scratch.append([0, 0, 0, 0])
third = [list(b) for b in n_rooks_solutions(4)]
assert third == first, "editing one result changed a later call"
"""),
    ],
)


problem(
    id="blocked-queens",
    track="Counting & Backtracking",
    title="Queens on a Damaged Board",
    difficulty="medium",
    points=20,
    blurb="N-queens, except some squares are rubble and cannot hold a queen.",
    statement="""
<p>Same board representation as before: <code>board[i]</code> is the column of
the queen in row <code>i</code>, and a short list is a partial board. A queen
attacks along its row, its column, and both diagonals.</p>

<p>This time a set <code>blocked</code> of <code>(row, col)</code> tuples marks
squares that are damaged &mdash; no queen may stand on them, though queens
attack straight <em>through</em> them as if they were empty.</p>

<ul>
  <li><code>blocked_queens_valid(board, blocked)</code> &mdash; <code>True</code>
      if no queen attacks another and no queen sits on a blocked square.</li>
  <li><code>blocked_queens_solutions(n, blocked)</code> &mdash; a list of every
      complete valid board, found by depth-first search over the rows.</li>
</ul>

<p>With <code>blocked</code> empty this reduces to plain n-queens, so
<code>len(blocked_queens_solutions(8, set())) == 92</code> is a free
regression test. Note that a damaged board can easily have zero solutions;
returning <code>[]</code> is correct in that case.</p>
""",
    examples="""
>>> blocked_queens_valid([0, 2], set())
True
>>> blocked_queens_valid([0, 2], {(1, 2)})
False
>>> blocked_queens_valid([1, 3], set())
True
>>> blocked_queens_solutions(4, set())
[[1, 3, 0, 2], [2, 0, 3, 1]]
>>> blocked_queens_solutions(4, {(0, 1)})
[[2, 0, 3, 1]]
>>> blocked_queens_solutions(4, {(0, 1), (0, 2)})
[]
""",
    starter="""
def blocked_queens_valid(board, blocked):
    pass


def blocked_queens_helper(n, blocked, board):  # optional
    pass


def blocked_queens_solutions(n, blocked):
    pass
""",
    hints=[
        "Two queens in rows i and j attack diagonally exactly when "
        "abs(board[i] - board[j]) == abs(i - j).",
        "The blocked check is per-queen, not per-pair: for each row i, reject "
        "the board if (i, board[i]) is in blocked.",
        "In the DFS you can skip a blocked square before you even append it, "
        "which prunes a little earlier than validating afterwards.",
    ],
    solution="""
def blocked_queens_valid(board, blocked):
    for i, col in enumerate(board):
        if (i, col) in blocked:
            return False
        for j in range(i + 1, len(board)):
            if col == board[j] or abs(col - board[j]) == j - i:
                return False
    return True


def blocked_queens_helper(n, blocked, board):
    if len(board) == n:
        yield list(board)
        return
    row = len(board)
    for col in range(n):
        if (row, col) in blocked:
            continue
        board.append(col)
        if blocked_queens_valid(board, blocked):
            yield from blocked_queens_helper(n, blocked, board)
        board.pop()


def blocked_queens_solutions(n, blocked):
    return list(blocked_queens_helper(n, blocked, []))
""",
    tests=[
        T("validity on hand-checked boards", """
assert blocked_queens_valid([0, 2], set())
assert not blocked_queens_valid([0, 1], set())
assert not blocked_queens_valid([0, 0], set())
assert blocked_queens_valid([0, 3, 1], set())
assert blocked_queens_valid([], set())
assert blocked_queens_valid([0], set())
"""),
        T("blocked squares invalidate a board", """
assert not blocked_queens_valid([0, 2], {(1, 2)})
assert not blocked_queens_valid([0, 2], {(0, 0)})
assert blocked_queens_valid([0, 2], {(0, 1), (1, 1), (2, 2)})
assert not blocked_queens_valid([0], {(0, 0)})
"""),
        T("validity agrees with brute force on boards up to n=4", """
from itertools import product


def _expected(board, blocked):
    for i, col in enumerate(board):
        if (i, col) in blocked:
            return False
        for j in range(i + 1, len(board)):
            if col == board[j] or abs(col - board[j]) == j - i:
                return False
    return True


for blocked in (set(), {(0, 0)}, {(1, 2), (3, 3)}):
    for size in range(0, 5):
        for board in product(range(4), repeat=size):
            got = blocked_queens_valid(list(board), blocked)
            assert bool(got) == _expected(board, blocked), \\
                "blocked_queens_valid(%r, %r) -> %r" % (list(board), blocked, got)
"""),
        T("undamaged boards reproduce the classic n-queens counts", """
expected = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}
for n, count in expected.items():
    got = len(blocked_queens_solutions(n, set()))
    assert got == count, "n=%d gave %d solutions, expected %d" % (n, got, count)
"""),
        T("damaged boards match exhaustive enumeration", """
from itertools import product


def _ok(board, blocked):
    for i, col in enumerate(board):
        if (i, col) in blocked:
            return False
        for j in range(i + 1, len(board)):
            if col == board[j] or abs(col - board[j]) == j - i:
                return False
    return True


cases = [(4, set()), (4, {(0, 1)}), (4, {(0, 1), (0, 2)}),
         (5, {(2, 2)}), (5, {(0, 0), (1, 3), (4, 4)}), (6, {(0, 0)})]
for n, blocked in cases:
    expect = {p for p in product(range(n), repeat=n) if _ok(list(p), blocked)}
    got = [tuple(b) for b in blocked_queens_solutions(n, blocked)]
    assert len(got) == len(set(got)), "duplicate boards for n=%d, %r" % (n, blocked)
    assert set(got) == expect, \\
        "n=%d blocked=%r: missing %r, extra %r" % (
            n, blocked, sorted(expect - set(got))[:3], sorted(set(got) - expect)[:3])
"""),
        T("blocked is never mutated by the solver", """
blocked = {(0, 1), (2, 3)}
snapshot = set(blocked)
blocked_queens_solutions(5, blocked)
assert blocked == snapshot, "the solver modified the blocked set"
"""),
    ],
)


problem(
    id="amazons",
    track="Counting & Backtracking",
    title="Amazons: Queens That Also Leap",
    difficulty="hard",
    points=25,
    blurb="Add knight moves to the queen and almost every board becomes unsolvable.",
    statement="""
<p>An <strong>amazon</strong> (sometimes called a superqueen) moves like a
queen <em>and</em> like a knight: it attacks along its row, its column, both
diagonals, and any square an L-shape away &mdash; two in one direction and one
in the perpendicular direction.</p>

<p>Using the same list-of-columns representation, write
<code>n_amazons_valid(board)</code> and <code>n_amazons_solutions(n)</code>,
enumerating every way to place <code>n</code> mutually non-attacking amazons on
an <code>n</code> &times; <code>n</code> board via depth-first search.</p>

<p>The extra constraint is brutal. Every board from 2 &times; 2 through
9 &times; 9 has <em>zero</em> solutions, and the 10 &times; 10 board has
exactly four. That makes this a good place to notice how much of the work is
done by pruning: a naive generate-and-test over all
<code>10 ** 10</code> one-per-row boards would never finish, while a DFS that
rejects a partial board as soon as it goes bad returns in well under a
second.</p>
""",
    examples="""
>>> n_amazons_valid([0, 2])
False
>>> n_amazons_valid([0, 3])
True
>>> n_amazons_solutions(1)
[[0]]
>>> n_amazons_solutions(5)
[]
>>> len(n_amazons_solutions(10))
4
""",
    starter="""
def n_amazons_valid(board):
    pass


def n_amazons_helper(n, board):  # optional
    pass


def n_amazons_solutions(n):
    pass
""",
    hints=[
        "Start from your n-queens validity check, then add one more rejection: "
        "a knight relationship between rows i and j.",
        "With dr = abs(i - j) and dc = abs(board[i] - board[j]), a knight "
        "attack is (dr, dc) == (1, 2) or (2, 1).",
        "Because every new queen only has to be checked against the queens "
        "already placed, you can validate just the last row instead of the "
        "whole board -- worth doing before you try n = 10.",
    ],
    solution="""
def n_amazons_valid(board):
    for i, col in enumerate(board):
        for j in range(i + 1, len(board)):
            dr = j - i
            dc = abs(col - board[j])
            if dc == 0 or dc == dr or (dr, dc) in ((1, 2), (2, 1)):
                return False
    return True


def n_amazons_helper(n, board):
    if len(board) == n:
        yield list(board)
        return
    row = len(board)
    for col in range(n):
        ok = True
        for i, other in enumerate(board):
            dr = row - i
            dc = abs(col - other)
            if dc == 0 or dc == dr or (dr, dc) in ((1, 2), (2, 1)):
                ok = False
                break
        if ok:
            board.append(col)
            yield from n_amazons_helper(n, board)
            board.pop()


def n_amazons_solutions(n):
    return list(n_amazons_helper(n, []))
""",
    tests=[
        T("validity on hand-checked boards", """
assert n_amazons_valid([])
assert n_amazons_valid([0])
assert not n_amazons_valid([0, 0])
assert not n_amazons_valid([0, 1])
assert not n_amazons_valid([0, 2])
assert n_amazons_valid([0, 3])
assert not n_amazons_valid([0, 4, 1])
"""),
        T("knight relationships are rejected in both orientations", """
assert not n_amazons_valid([2, 0])
assert not n_amazons_valid([2, 4])
assert not n_amazons_valid([0, 4, 1])
assert not n_amazons_valid([1, 4, 0])
assert n_amazons_valid([2, 5, 8])
"""),
        T("validity agrees with brute force on boards up to n=5", """
from itertools import product


def _expected(board):
    for i, col in enumerate(board):
        for j in range(i + 1, len(board)):
            dr, dc = j - i, abs(col - board[j])
            if dc == 0 or dc == dr or (dr, dc) in ((1, 2), (2, 1)):
                return False
    return True


for size in range(0, 6):
    for board in product(range(5), repeat=size):
        got = n_amazons_valid(list(board))
        assert bool(got) == _expected(board), \\
            "n_amazons_valid(%r) -> %r" % (list(board), got)
"""),
        T("small boards have no solutions at all", """
assert [list(b) for b in n_amazons_solutions(1)] == [[0]]
for n in range(2, 8):
    got = n_amazons_solutions(n)
    assert list(got) == [], "n=%d should have no solutions, got %r" % (n, got)
"""),
        T("the 10x10 board has exactly four solutions", """
sols = [tuple(b) for b in n_amazons_solutions(10)]
assert len(sols) == 4, "expected 4 solutions on 10x10, got %d" % len(sols)
assert len(set(sols)) == 4, "solutions are not distinct"
for board in sols:
    assert sorted(board) == list(range(10))
    assert n_amazons_valid(list(board))
"""),
        T("every enumerated board is valid and complete", """
for n in (8, 9, 10):
    for board in n_amazons_solutions(n):
        assert len(board) == n
        assert n_amazons_valid(list(board))
"""),
    ],
)


# --------------------------------------------------------------------------
# Build-time oracles.  These exist only to compute the constants that the
# tests assert against -- optimal move counts, provably unsolvable boards.
# --------------------------------------------------------------------------

def _cross_press(board, row, col):
    rows, cols = len(board), len(board[0])
    grid = [list(r) for r in board]
    for j in range(cols):
        grid[row][j] = not grid[row][j]
    for i in range(rows):
        if i != row:
            grid[i][col] = not grid[i][col]
    return tuple(tuple(r) for r in grid)


def _cross_distances(rows, cols):
    """Presses needed to clear each reachable board of the given size."""
    start = tuple((False,) * cols for _ in range(rows))
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for row in range(rows):
            for col in range(cols):
                nxt = _cross_press(state, row, col)
                if nxt not in dist:
                    dist[nxt] = dist[state] + 1
                    queue.append(nxt)
    return dist


def _cross_scramble(rows, cols, presses):
    board = tuple((False,) * cols for _ in range(rows))
    for row, col in presses:
        board = _cross_press(board, row, col)
    return [list(r) for r in board]


def _cross_unsolvable(rows, cols):
    """A board of this size that no sequence of presses can clear."""
    reachable = _cross_distances(rows, cols)
    for bits in product((False, True), repeat=rows * cols):
        board = tuple(tuple(bits[i * cols:(i + 1) * cols]) for i in range(rows))
        if board not in reachable:
            return [list(r) for r in board]
    return None


_CROSS_33 = _cross_distances(3, 3)
_CROSS_34 = _cross_distances(3, 4)


def _cross_case(rows, cols, presses):
    """(board, optimal number of presses) for a board built from ``presses``."""
    board = _cross_scramble(rows, cols, presses)
    key = tuple(tuple(r) for r in board)
    table = {(3, 3): _CROSS_33, (3, 4): _CROSS_34}[(rows, cols)]
    return board, table[key]


_CROSS_A, _CROSS_A_LEN = _cross_case(3, 3, [(0, 0)])
_CROSS_B, _CROSS_B_LEN = _cross_case(3, 3, [(0, 0), (1, 2), (2, 1)])
_CROSS_C, _CROSS_C_LEN = _cross_case(3, 4, [(0, 1), (2, 3), (1, 0), (0, 1)])
_CROSS_BAD = _cross_unsolvable(3, 3)


problem(
    id="cross-out",
    track="Toggle Puzzles",
    title="Cross Out",
    difficulty="hard",
    points=30,
    blurb="Lights Out's louder sibling: one press flips an entire row and column.",
    statement="""
<p><em>Cross Out</em> is played on an <code>m</code> &times; <code>n</code>
grid of lights, each either on (<code>True</code>) or off
(<code>False</code>). Pressing a light toggles <strong>every light in its row
and every light in its column</strong>. The pressed light itself toggles
exactly once, not twice. The goal is to turn every light off.</p>

<p>Build a <code>CrossOutPuzzle</code> class with these members, plus a
top-level <code>create_cross_puzzle(rows, cols)</code> that returns a puzzle of
the given size with every light off:</p>

<ul>
  <li><code>__init__(self, board)</code> and <code>get_board(self)</code> &mdash;
      store and return a two-dimensional list of booleans.</li>
  <li><code>perform_move(self, row, col)</code> &mdash; press one light,
      mutating this puzzle in place.</li>
  <li><code>scramble(self)</code> &mdash; press each light with probability
      1/2, which guarantees the result is still solvable.</li>
  <li><code>is_solved(self)</code> &mdash; are all lights off?</li>
  <li><code>copy(self)</code> &mdash; a new puzzle with an independent board.</li>
  <li><code>successors(self)</code> &mdash; yield
      <code>((row, col), new_puzzle)</code> pairs, one per press, without
      disturbing <code>self</code>.</li>
  <li><code>find_solution(self)</code> &mdash; an <strong>optimal</strong> list
      of <code>(row, col)</code> presses that clears the board, or
      <code>None</code> if the board cannot be cleared.</li>
</ul>

<p><code>find_solution</code> must be a <strong>breadth-first graph
search</strong>: never enqueue a board you have already visited or already
queued. Convert boards to tuples of tuples to use them as set members. Unlike
Lights Out, plenty of Cross Out boards are unreachable, so returning
<code>None</code> is a case you have to get right, and you only discover it
once the frontier runs dry.</p>
""",
    examples="""
>>> p = create_cross_puzzle(3, 4)
>>> p.get_board()
[[False, False, False, False],
 [False, False, False, False],
 [False, False, False, False]]
>>> p.perform_move(1, 1)
>>> p.get_board()
[[False, True, False, False],
 [True, True, True, True],
 [False, True, False, False]]
>>> p.is_solved()
False
>>> p = create_cross_puzzle(2, 2)
>>> p.perform_move(0, 0)
>>> p.get_board()
[[True, True], [True, False]]
>>> for move, new_p in p.successors():
...     print(move, new_p.get_board())
...
(0, 0) [[False, False], [False, False]]
(0, 1) [[False, False], [True, True]]
(1, 0) [[False, True], [False, True]]
(1, 1) [[True, False], [False, True]]
>>> p.find_solution()
[(0, 0)]
""",
    starter="""
import random


class CrossOutPuzzle(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def perform_move(self, row, col):
        pass

    def scramble(self):
        pass

    def is_solved(self):
        pass

    def copy(self):
        pass

    def successors(self):
        pass

    def find_solution(self):
        pass


def create_cross_puzzle(rows, cols):
    pass
""",
    hints=[
        "perform_move: flip the whole row, then flip the column but skip the "
        "cell you already flipped, otherwise the pressed light toggles twice "
        "and stays put.",
        "copy() must build new inner lists. [list(row) for row in self.board] "
        "is enough; self.board[:] is not, since it shares the rows.",
        "In the BFS, store tuple(tuple(row) for row in board) in a visited set "
        "and add a state to it at the moment you enqueue it, not when you pop "
        "it -- otherwise duplicates pile up in the frontier.",
        "Queue entries should carry the move list that produced them, e.g. "
        "deque([(self, [])]). When the frontier empties with nothing solved, "
        "return None.",
    ],
    solution="""
import random
from collections import deque


class CrossOutPuzzle(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0]) if board else 0

    def get_board(self):
        return self.board

    def perform_move(self, row, col):
        for j in range(self.cols):
            self.board[row][j] = not self.board[row][j]
        for i in range(self.rows):
            if i != row:
                self.board[i][col] = not self.board[i][col]

    def scramble(self):
        for row in range(self.rows):
            for col in range(self.cols):
                if random.random() < 0.5:
                    self.perform_move(row, col)

    def is_solved(self):
        return all(not cell for row in self.board for cell in row)

    def copy(self):
        return CrossOutPuzzle([list(row) for row in self.board])

    def successors(self):
        for row in range(self.rows):
            for col in range(self.cols):
                child = self.copy()
                child.perform_move(row, col)
                yield (row, col), child

    def _key(self):
        return tuple(tuple(row) for row in self.board)

    def find_solution(self):
        if self.is_solved():
            return []
        visited = {self._key()}
        frontier = deque([(self, [])])
        while frontier:
            puzzle, moves = frontier.popleft()
            for move, child in puzzle.successors():
                key = child._key()
                if key in visited:
                    continue
                if child.is_solved():
                    return moves + [move]
                visited.add(key)
                frontier.append((child, moves + [move]))
        return None


def create_cross_puzzle(rows, cols):
    return CrossOutPuzzle([[False] * cols for _ in range(rows)])
""",
    tests=[
        T("construction, get_board and create_cross_puzzle", """
board = [[True, False], [False, True]]
p = CrossOutPuzzle(board)
assert p.get_board() == [[True, False], [False, True]]
q = create_cross_puzzle(2, 3)
assert q.get_board() == [[False] * 3 for _ in range(2)]
assert len(create_cross_puzzle(4, 1).get_board()) == 4
assert len(create_cross_puzzle(4, 1).get_board()[0]) == 1
"""),
        T("perform_move flips a full row and column, pressed cell once", """
p = create_cross_puzzle(3, 4)
p.perform_move(1, 1)
assert p.get_board() == [[False, True, False, False],
                        [True, True, True, True],
                        [False, True, False, False]], p.get_board()
p = create_cross_puzzle(2, 2)
p.perform_move(0, 0)
assert p.get_board() == [[True, True], [True, False]], p.get_board()
"""),
        T("pressing the same light twice is a no-op", """
p = create_cross_puzzle(3, 5)
p.perform_move(2, 3)
p.perform_move(2, 3)
assert p.is_solved(), p.get_board()
"""),
        T("presses commute", """
p = create_cross_puzzle(3, 4)
q = create_cross_puzzle(3, 4)
for move in [(0, 1), (2, 2), (1, 0)]:
    p.perform_move(*move)
for move in [(1, 0), (0, 1), (2, 2)]:
    q.perform_move(*move)
assert p.get_board() == q.get_board()
"""),
        T("is_solved", """
assert create_cross_puzzle(3, 3).is_solved()
assert not CrossOutPuzzle([[True, False], [False, False]]).is_solved()
assert CrossOutPuzzle([[False, False], [False, False]]).is_solved()
"""),
        T("copy is deep and independent", """
p = create_cross_puzzle(3, 3)
c = p.copy()
assert p.get_board() == c.get_board()
p.perform_move(1, 1)
assert p.get_board() != c.get_board(), "the copy changed with the original"
c.perform_move(0, 0)
assert p.get_board() != c.get_board(), "the original changed with the copy"
"""),
        T("successors yields one child per light, leaving self alone", """
p = create_cross_puzzle(2, 2)
p.perform_move(0, 0)
before = [list(r) for r in p.get_board()]
found = {move: [list(r) for r in child.get_board()] for move, child in p.successors()}
assert p.get_board() == before, "successors() mutated the original puzzle"
assert sorted(found) == [(0, 0), (0, 1), (1, 0), (1, 1)]
assert found[(0, 0)] == [[False, False], [False, False]], found[(0, 0)]
assert found[(0, 1)] == [[False, False], [True, True]], found[(0, 1)]
assert found[(1, 0)] == [[False, True], [False, True]], found[(1, 0)]
assert found[(1, 1)] == [[True, False], [False, True]], found[(1, 1)]
for i in range(2, 6):
    q = create_cross_puzzle(i, i + 1)
    assert len(list(q.successors())) == i * (i + 1)
"""),
        T("find_solution returns [] on an already-solved board", """
assert create_cross_puzzle(3, 3).find_solution() == []
assert create_cross_puzzle(2, 4).find_solution() == []
"""),
        T("find_solution actually clears the board", """
cases = [@@A@@, @@B@@, @@C@@]
for board in cases:
    p = CrossOutPuzzle([list(r) for r in board])
    moves = p.find_solution()
    assert moves is not None, "no solution found for %r" % (board,)
    check = CrossOutPuzzle([list(r) for r in board])
    for row, col in moves:
        check.perform_move(row, col)
    assert check.is_solved(), "moves %r do not clear %r" % (moves, board)
""", A=_CROSS_A, B=_CROSS_B, C=_CROSS_C),
        T("find_solution is optimal, not merely correct", """
cases = [(@@A@@, @@ALEN@@), (@@B@@, @@BLEN@@), (@@C@@, @@CLEN@@)]
for board, best in cases:
    moves = CrossOutPuzzle([list(r) for r in board]).find_solution()
    assert len(moves) == best, \\
        "solved %r in %d presses, optimum is %d" % (board, len(moves), best)
""", A=_CROSS_A, ALEN=_CROSS_A_LEN, B=_CROSS_B, BLEN=_CROSS_B_LEN,
     C=_CROSS_C, CLEN=_CROSS_C_LEN),
        T("unreachable boards return None", """
p = CrossOutPuzzle(@@BAD@@)
assert p.find_solution() is None, "that board cannot be cleared"
""", BAD=_CROSS_BAD),
        T("scramble leaves the puzzle solvable", """
import random
random.seed(1234)
solvable = 0
for _ in range(12):
    p = create_cross_puzzle(3, 3)
    p.scramble()
    moves = p.find_solution()
    assert moves is not None, "scramble produced an unsolvable board: %r" % p.get_board()
    for row, col in moves:
        p.perform_move(row, col)
    assert p.is_solved()
    solvable += 1
assert solvable == 12
"""),
    ],
)


def _tri_press(board, row, col):
    rows, cols = len(board), len(board[0])
    grid = [list(r) for r in board]
    for dr, dc in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        i, j = row + dr, col + dc
        if 0 <= i < rows and 0 <= j < cols:
            grid[i][j] = (grid[i][j] + 1) % 3
    return tuple(tuple(r) for r in grid)


def _tri_case(rows, cols, presses):
    """(board, optimal presses to clear it) built by pressing from all zeros."""
    board = tuple((0,) * cols for _ in range(rows))
    for row, col in presses:
        board = _tri_press(board, row, col)
    goal = tuple((0,) * cols for _ in range(rows))
    dist = {board: 0}
    queue = deque([board])
    while queue:
        state = queue.popleft()
        if state == goal:
            return [list(r) for r in board], dist[state]
        for row in range(rows):
            for col in range(cols):
                nxt = _tri_press(state, row, col)
                if nxt not in dist:
                    dist[nxt] = dist[state] + 1
                    queue.append(nxt)
    return [list(r) for r in board], None


def _tri_unsolvable(rows, cols):
    goal = tuple((0,) * cols for _ in range(rows))
    reachable = {goal}
    queue = deque([goal])
    while queue:
        state = queue.popleft()
        for row in range(rows):
            for col in range(cols):
                nxt = _tri_press(state, row, col)
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
    for cells in product((0, 1, 2), repeat=rows * cols):
        board = tuple(tuple(cells[i * cols:(i + 1) * cols]) for i in range(rows))
        if board not in reachable:
            return [list(r) for r in board]
    return None


_TRI_A, _TRI_A_LEN = _tri_case(2, 3, [(0, 0)])
_TRI_B, _TRI_B_LEN = _tri_case(2, 3, [(0, 0), (1, 2)])
_TRI_C, _TRI_C_LEN = _tri_case(3, 3, [(1, 1), (0, 2), (0, 2)])
_TRI_BAD = _tri_unsolvable(2, 3)


problem(
    id="tri-state-lights",
    track="Toggle Puzzles",
    title="Tri-State Lights",
    difficulty="hard",
    points=30,
    blurb="Lights Out with three states per cell, so a press is no longer its own undo.",
    statement="""
<p>Each cell of an <code>m</code> &times; <code>n</code> grid holds a number in
<code>{0, 1, 2}</code>. Pressing a cell adds <code>1</code> modulo
<code>3</code> to that cell and to its neighbours above, below, left and right
&mdash; neighbours off the edge of the board are simply ignored. The board is
solved when every cell reads <code>0</code>.</p>

<p>Build a <code>TriStatePuzzle</code> class with
<code>__init__(self, board)</code>, <code>get_board(self)</code>,
<code>perform_move(self, row, col)</code>, <code>scramble(self)</code>,
<code>is_solved(self)</code>, <code>copy(self)</code>,
<code>successors(self)</code> and <code>find_solution(self)</code>, plus a
top-level <code>create_tri_puzzle(rows, cols)</code> returning an all-zero
board. The contracts match Cross Out: <code>successors</code> yields
<code>((row, col), new_puzzle)</code> pairs, and <code>find_solution</code>
returns an <em>optimal</em> list of presses via breadth-first graph search, or
<code>None</code> when the board cannot be cleared.</p>

<p>One press is no longer its own inverse: undoing a press takes two more
presses of the same cell. That single change triples the state space, and it
means a board one press away from solved is <em>two</em> moves from solved.
Your visited set matters much more here than it did in binary Lights Out.</p>
""",
    examples="""
>>> p = create_tri_puzzle(3, 3)
>>> p.perform_move(1, 1)
>>> p.get_board()
[[0, 1, 0], [1, 1, 1], [0, 1, 0]]
>>> p.perform_move(1, 1)
>>> p.get_board()
[[0, 2, 0], [2, 2, 2], [0, 2, 0]]
>>> p.perform_move(1, 1)
>>> p.is_solved()
True
>>> p = create_tri_puzzle(2, 2)
>>> p.perform_move(0, 0)
>>> p.get_board()
[[1, 1], [1, 0]]
>>> p.find_solution()
[(0, 0), (0, 0)]
""",
    starter="""
import random


class TriStatePuzzle(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def perform_move(self, row, col):
        pass

    def scramble(self):
        pass

    def is_solved(self):
        pass

    def copy(self):
        pass

    def successors(self):
        pass

    def find_solution(self):
        pass


def create_tri_puzzle(rows, cols):
    pass
""",
    hints=[
        "Write the five offsets once -- (0, 0), (-1, 0), (1, 0), (0, -1), "
        "(0, 1) -- and bounds-check each before adding 1 modulo 3.",
        "is_solved is now 'every cell == 0', not 'every cell is falsy' -- "
        "those happen to agree, but say what you mean.",
        "The BFS is identical in shape to the binary version. Only the "
        "successor function changed, which is exactly the point: uninformed "
        "search does not care what the state means.",
        "Solutions can be up to two presses per cell, so a 3x3 board can need "
        "a dozen moves. Make sure you mark states visited when enqueueing.",
    ],
    solution="""
import random
from collections import deque

_OFFSETS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))


class TriStatePuzzle(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0]) if board else 0

    def get_board(self):
        return self.board

    def perform_move(self, row, col):
        for dr, dc in _OFFSETS:
            i, j = row + dr, col + dc
            if 0 <= i < self.rows and 0 <= j < self.cols:
                self.board[i][j] = (self.board[i][j] + 1) % 3

    def scramble(self):
        for row in range(self.rows):
            for col in range(self.cols):
                for _ in range(random.randrange(3)):
                    self.perform_move(row, col)

    def is_solved(self):
        return all(cell == 0 for row in self.board for cell in row)

    def copy(self):
        return TriStatePuzzle([list(row) for row in self.board])

    def successors(self):
        for row in range(self.rows):
            for col in range(self.cols):
                child = self.copy()
                child.perform_move(row, col)
                yield (row, col), child

    def _key(self):
        return tuple(tuple(row) for row in self.board)

    def find_solution(self):
        if self.is_solved():
            return []
        visited = {self._key()}
        frontier = deque([(self, [])])
        while frontier:
            puzzle, moves = frontier.popleft()
            for move, child in puzzle.successors():
                key = child._key()
                if key in visited:
                    continue
                if child.is_solved():
                    return moves + [move]
                visited.add(key)
                frontier.append((child, moves + [move]))
        return None


def create_tri_puzzle(rows, cols):
    return TriStatePuzzle([[0] * cols for _ in range(rows)])
""",
    tests=[
        T("construction and create_tri_puzzle", """
p = TriStatePuzzle([[1, 0], [0, 2]])
assert p.get_board() == [[1, 0], [0, 2]]
assert create_tri_puzzle(2, 3).get_board() == [[0, 0, 0], [0, 0, 0]]
assert create_tri_puzzle(1, 1).get_board() == [[0]]
"""),
        T("perform_move adds one mod three to the plus shape", """
p = create_tri_puzzle(3, 3)
p.perform_move(1, 1)
assert p.get_board() == [[0, 1, 0], [1, 1, 1], [0, 1, 0]], p.get_board()
p = create_tri_puzzle(3, 3)
p.perform_move(0, 0)
assert p.get_board() == [[1, 1, 0], [1, 0, 0], [0, 0, 0]], p.get_board()
p = create_tri_puzzle(2, 4)
p.perform_move(1, 3)
assert p.get_board() == [[0, 0, 0, 1], [0, 0, 1, 1]], p.get_board()
"""),
        T("three presses of one cell restore the board", """
p = create_tri_puzzle(3, 3)
for _ in range(3):
    p.perform_move(1, 2)
assert p.is_solved(), p.get_board()
p = create_tri_puzzle(3, 3)
p.perform_move(1, 2)
p.perform_move(1, 2)
assert not p.is_solved(), "two presses should not cancel"
"""),
        T("is_solved and copy", """
assert create_tri_puzzle(3, 3).is_solved()
assert not TriStatePuzzle([[0, 0], [0, 2]]).is_solved()
p = create_tri_puzzle(2, 2)
c = p.copy()
p.perform_move(0, 0)
assert c.get_board() == [[0, 0], [0, 0]], "copy shares state with the original"
assert p.get_board() != c.get_board()
"""),
        T("successors yields one child per cell and leaves self alone", """
p = create_tri_puzzle(2, 2)
before = [list(r) for r in p.get_board()]
children = dict((m, [list(r) for r in c.get_board()]) for m, c in p.successors())
assert p.get_board() == before, "successors() mutated the original puzzle"
assert sorted(children) == [(0, 0), (0, 1), (1, 0), (1, 1)]
assert children[(0, 0)] == [[1, 1], [1, 0]], children[(0, 0)]
for rows, cols in ((2, 3), (3, 4), (4, 4)):
    assert len(list(create_tri_puzzle(rows, cols).successors())) == rows * cols
"""),
        T("find_solution clears a solved board with no moves", """
assert create_tri_puzzle(2, 3).find_solution() == []
assert create_tri_puzzle(3, 3).find_solution() == []
"""),
        T("find_solution clears real boards", """
for board in [@@A@@, @@B@@, @@C@@]:
    p = TriStatePuzzle([list(r) for r in board])
    moves = p.find_solution()
    assert moves is not None, "no solution found for %r" % (board,)
    check = TriStatePuzzle([list(r) for r in board])
    for row, col in moves:
        check.perform_move(row, col)
    assert check.is_solved(), "moves %r do not clear %r" % (moves, board)
""", A=_TRI_A, B=_TRI_B, C=_TRI_C),
        T("find_solution is optimal", """
for board, best in [(@@A@@, @@ALEN@@), (@@B@@, @@BLEN@@), (@@C@@, @@CLEN@@)]:
    moves = TriStatePuzzle([list(r) for r in board]).find_solution()
    assert len(moves) == best, \\
        "solved %r in %d presses, optimum is %d" % (board, len(moves), best)
""", A=_TRI_A, ALEN=_TRI_A_LEN, B=_TRI_B, BLEN=_TRI_B_LEN,
     C=_TRI_C, CLEN=_TRI_C_LEN),
        T("unsolvable boards return None", """
p = TriStatePuzzle(@@BAD@@)
assert p.find_solution() is None, "that board cannot be cleared"
""", BAD=_TRI_BAD),
        T("scramble leaves the puzzle solvable", """
import random
random.seed(7)
for _ in range(6):
    p = create_tri_puzzle(2, 3)
    p.scramble()
    moves = p.find_solution()
    assert moves is not None, "scramble produced an unsolvable board: %r" % p.get_board()
    for row, col in moves:
        p.perform_move(row, col)
    assert p.is_solved()
"""),
    ],
)


def _ring_press(lights, i):
    n = len(lights)
    bits = list(lights)
    for j in ((i - 1) % n, i, (i + 1) % n):
        bits[j] = not bits[j]
    return tuple(bits)


def _ring_distances(n):
    start = (False,) * n
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for i in range(n):
            nxt = _ring_press(state, i)
            if nxt not in dist:
                dist[nxt] = dist[state] + 1
                queue.append(nxt)
    return dist


def _ring_case(n, presses):
    lights = (False,) * n
    for i in presses:
        lights = _ring_press(lights, i)
    return list(lights), _ring_distances(n)[lights]


_RING_A, _RING_A_LEN = _ring_case(7, [0])
_RING_B, _RING_B_LEN = _ring_case(8, [1, 5])
_RING_C, _RING_C_LEN = _ring_case(10, [0, 3, 4, 9])
_RING_D, _RING_D_LEN = _ring_case(12, [2, 3, 7, 8, 11])


problem(
    id="toggle-ring",
    track="Toggle Puzzles",
    title="Toggle Ring",
    difficulty="medium",
    points=20,
    blurb="Lights in a circle, three flipped per press. Some rings can never be cleared.",
    statement="""
<p><code>n</code> lights sit in a <strong>circle</strong>, indexed
<code>0</code> through <code>n - 1</code>. Pressing light <code>i</code>
toggles lights <code>i - 1</code>, <code>i</code> and <code>i + 1</code>, with
the indices wrapping around, so light <code>0</code> and light
<code>n - 1</code> are neighbours. There are no edges to fall off.</p>

<p>Write <code>solve_toggle_ring(lights)</code>, which takes a list of
booleans and returns a <strong>shortest</strong> list of indices to press that
turns every light off, or <code>None</code> if no sequence does. Presses
commute and pressing twice cancels, so a shortest answer never repeats an
index; return the presses in any order. Use a breadth-first graph search over
ring states.</p>

<p>Watch what happens when <code>n</code> is a multiple of three. On a ring of
3 every press flips all three lights, so the only boards you can ever clear are
all-on and all-off. Larger multiples of three are less obviously broken but
still leave most boards unreachable &mdash; a good reminder that "search found
nothing" is a real answer, not a bug.</p>
""",
    examples="""
>>> solve_toggle_ring([False, False, False, False])
[]
>>> solve_toggle_ring([True, True, True, False, False, False, False])
[1]
>>> solve_toggle_ring([True, False, False])
None
>>> len(solve_toggle_ring([True, True, True]))
1
>>> len(solve_toggle_ring([True] * 8))
8
""",
    starter="""
def solve_toggle_ring(lights):
    pass
""",
    hints=[
        "Modular arithmetic does the wrapping for you: the press at i touches "
        "(i - 1) % n, i and (i + 1) % n.",
        "Represent a state as a tuple of booleans so it can live in a visited "
        "set; convert the input list once at the start.",
        "Queue entries pair a state with the list of presses that reached it. "
        "Return None only after the frontier is completely empty.",
        "Since presses commute, you can cut the branching factor by only ever "
        "considering indices larger than the last one you pressed -- optional, "
        "but it turns an exponential frontier into 2**n subsets in order.",
    ],
    solution="""
from collections import deque


def _press(lights, i):
    n = len(lights)
    bits = list(lights)
    for j in ((i - 1) % n, i, (i + 1) % n):
        bits[j] = not bits[j]
    return tuple(bits)


def solve_toggle_ring(lights):
    start = tuple(bool(light) for light in lights)
    goal = (False,) * len(start)
    if start == goal:
        return []
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        state, presses = frontier.popleft()
        for i in range(len(start)):
            nxt = _press(state, i)
            if nxt in visited:
                continue
            if nxt == goal:
                return presses + [i]
            visited.add(nxt)
            frontier.append((nxt, presses + [i]))
    return None
""",
    tests=[
        T("an already-dark ring needs no presses", """
for n in range(1, 9):
    assert solve_toggle_ring([False] * n) == []
"""),
        T("single-press boards are undone by one press", """
for board, expected in [(@@A@@, @@ALEN@@), (@@B@@, @@BLEN@@)]:
    got = solve_toggle_ring(list(board))
    assert got is not None and len(got) == expected, \\
        "%r solved in %r, optimum is %d" % (board, got, expected)
""", A=_RING_A, ALEN=_RING_A_LEN, B=_RING_B, BLEN=_RING_B_LEN),
        T("returned presses really clear the ring", """
cases = [@@A@@, @@B@@, @@C@@, @@D@@]
for board in cases:
    presses = solve_toggle_ring(list(board))
    assert presses is not None, "no solution found for %r" % (board,)
    n = len(board)
    bits = list(board)
    for i in presses:
        assert 0 <= i < n, "press index %r out of range for n=%d" % (i, n)
        for j in ((i - 1) % n, i, (i + 1) % n):
            bits[j] = not bits[j]
    assert not any(bits), "presses %r left %r" % (presses, bits)
""", A=_RING_A, B=_RING_B, C=_RING_C, D=_RING_D),
        T("solutions are minimal", """
cases = [(@@A@@, @@ALEN@@), (@@B@@, @@BLEN@@), (@@C@@, @@CLEN@@), (@@D@@, @@DLEN@@)]
for board, best in cases:
    presses = solve_toggle_ring(list(board))
    assert len(presses) == best, \\
        "%r solved in %d presses, optimum is %d" % (board, len(presses), best)
""", A=_RING_A, ALEN=_RING_A_LEN, B=_RING_B, BLEN=_RING_B_LEN,
     C=_RING_C, CLEN=_RING_C_LEN, D=_RING_D, DLEN=_RING_D_LEN),
        T("rings of three are almost entirely unsolvable", """
assert solve_toggle_ring([True, False, False]) is None
assert solve_toggle_ring([True, True, False]) is None
assert solve_toggle_ring([False, True, False]) is None
assert len(solve_toggle_ring([True, True, True])) == 1
"""),
        T("unsolvable boards on larger multiples of three", """
assert solve_toggle_ring([True] + [False] * 5) is None
assert solve_toggle_ring([True, True, False, False, False, False]) is None
assert solve_toggle_ring([True] + [False] * 8) is None
assert solve_toggle_ring([True] * 6) is not None
"""),
        T("every solvable ring up to n=7 is solved optimally", """
from collections import deque
from itertools import product


def _press(state, i):
    n = len(state)
    bits = list(state)
    for j in ((i - 1) % n, i, (i + 1) % n):
        bits[j] = not bits[j]
    return tuple(bits)


for n in range(1, 8):
    start = (False,) * n
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for i in range(n):
            nxt = _press(state, i)
            if nxt not in dist:
                dist[nxt] = dist[state] + 1
                queue.append(nxt)
    for bits in product((False, True), repeat=n):
        got = solve_toggle_ring(list(bits))
        if bits not in dist:
            assert got is None, "%r is unsolvable but got %r" % (list(bits), got)
            continue
        assert got is not None, "%r is solvable but got None" % (list(bits),)
        assert len(got) == dist[bits], \\
            "%r solved in %d, optimum is %d" % (list(bits), len(got), dist[bits])
        state = tuple(bits)
        for i in got:
            state = _press(state, i)
        assert state == start, "%r left the ring lit" % (got,)
"""),
    ],
)


def _jump_moves(cells):
    """Legal (from, to) moves for the jumping-disks rules."""
    length = len(cells)
    for i in range(length):
        if not cells[i]:
            continue
        for step in (1, 2, 3):
            for target in (i - step, i + step):
                if not 0 <= target < length or cells[target]:
                    continue
                lo, hi = min(i, target), max(i, target)
                if all(cells[k] for k in range(lo + 1, hi)):
                    yield i, target


def _jump_optimal(length, n):
    start = tuple(i < n for i in range(length))
    goal = tuple(i >= length - n for i in range(length))
    if start == goal:
        return 0
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cells = queue.popleft()
        for src, dst in _jump_moves(cells):
            nxt = list(cells)
            nxt[src], nxt[dst] = False, True
            nxt = tuple(nxt)
            if nxt in dist:
                continue
            if nxt == goal:
                return dist[cells] + 1
            dist[nxt] = dist[cells] + 1
            queue.append(nxt)
    return None


_JUMP_CASES = [(4, 2), (5, 2), (4, 3), (5, 3), (6, 3), (7, 3), (8, 4), (9, 4)]
_JUMP_OPT = {case: _jump_optimal(*case) for case in _JUMP_CASES}


problem(
    id="jumping-disks",
    track="Movement Puzzles",
    title="Jumping Disks",
    difficulty="medium",
    points=20,
    blurb="Slide disks down a row, hopping over one or two of their neighbours.",
    statement="""
<p>A row of <code>length</code> cells is numbered <code>0</code> through
<code>length - 1</code>. Disks start on cells <code>0</code> through
<code>n - 1</code>, and the goal is to get all <code>n</code> disks onto the
<em>last</em> <code>n</code> cells. The disks are identical, so only the set of
occupied cells matters, not which disk is where.</p>

<p>From cell <code>i</code>, a disk may move to an empty cell that is:</p>
<ul>
  <li>one step away (<code>i - 1</code> or <code>i + 1</code>);</li>
  <li>two steps away, if the single cell in between is occupied;</li>
  <li>three steps away, if <em>both</em> cells in between are occupied.</li>
</ul>

<p>In other words a disk may hop over a run of one or two disks, but never over
a gap and never over three. Write
<code>solve_jumping_disks(length, n)</code>, returning a
<strong>shortest</strong> list of <code>(from, to)</code> moves that reaches
the goal, or <code>None</code> if the goal is unreachable. Use a breadth-first
graph search.</p>

<p>Think about your state representation before you write the loop: a tuple of
booleans, a frozenset of occupied cells, and a sorted tuple of positions all
work, but only some of them are hashable and cheap to copy. That choice is
worth more to your runtime than any micro-optimisation inside the loop.</p>
""",
    examples="""
>>> solve_jumping_disks(4, 4)
[]
>>> solve_jumping_disks(4, 2)
[(0, 2), (1, 3)]
>>> solve_jumping_disks(5, 2)
[(0, 2), (1, 3), (2, 4)]
>>> len(solve_jumping_disks(6, 3))
3
>>> len(solve_jumping_disks(9, 4))
10
""",
    starter="""
def solve_jumping_disks(length, n):
    pass
""",
    hints=[
        "A state is just which cells are occupied. tuple(bool) of length "
        "`length` is hashable and easy to copy with a slice.",
        "Generate successors by looping over occupied cells and over the six "
        "candidate targets (plus and minus 1, 2, 3), rejecting any target that "
        "is off the row or already occupied.",
        "The 'jump over' condition is: every cell strictly between source and "
        "target is occupied. Write that as an all() over a range and all three "
        "step sizes collapse into one rule.",
        "Standard BFS bookkeeping: a deque of (state, moves), a visited set, "
        "and a goal test on children before enqueueing them.",
    ],
    solution="""
from collections import deque


def _successors(cells):
    length = len(cells)
    for i in range(length):
        if not cells[i]:
            continue
        for step in (1, 2, 3):
            for target in (i - step, i + step):
                if not 0 <= target < length or cells[target]:
                    continue
                lo, hi = min(i, target), max(i, target)
                if all(cells[k] for k in range(lo + 1, hi)):
                    nxt = list(cells)
                    nxt[i], nxt[target] = False, True
                    yield (i, target), tuple(nxt)


def solve_jumping_disks(length, n):
    start = tuple(i < n for i in range(length))
    goal = tuple(i >= length - n for i in range(length))
    if start == goal:
        return []
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        cells, moves = frontier.popleft()
        for move, nxt in _successors(cells):
            if nxt in visited:
                continue
            if nxt == goal:
                return moves + [move]
            visited.add(nxt)
            frontier.append((nxt, moves + [move]))
    return None
""",
    tests=[
        T("a row that is already full needs no moves", """
for n in range(1, 5):
    assert solve_jumping_disks(n, n) == []
"""),
        T("moves are legal and reach the goal", """
def _check(length, n, moves):
    cells = [i < n for i in range(length)]
    for src, dst in moves:
        assert 0 <= src < length and 0 <= dst < length, "off the row: %r" % ((src, dst),)
        assert cells[src], "no disk on cell %d" % src
        assert not cells[dst], "cell %d is occupied" % dst
        assert 1 <= abs(dst - src) <= 3, "%r is not a legal step" % ((src, dst),)
        lo, hi = min(src, dst), max(src, dst)
        assert all(cells[k] for k in range(lo + 1, hi)), \\
            "%r hops over an empty cell" % ((src, dst),)
        cells[src], cells[dst] = False, True
    assert cells == [i >= length - n for i in range(length)], \\
        "final row %r is not the goal" % (cells,)


for length, n in @@CASES@@:
    moves = solve_jumping_disks(length, n)
    assert moves is not None, "no solution for (%d, %d)" % (length, n)
    _check(length, n, moves)
""", CASES=_JUMP_CASES),
        T("solutions are of minimal length", """
for (length, n), best in @@OPT@@.items():
    moves = solve_jumping_disks(length, n)
    assert len(moves) == best, \\
        "(%d, %d) solved in %d moves, optimum is %d" % (length, n, len(moves), best)
""", OPT=_JUMP_OPT),
        T("small cases match the worked examples", """
assert len(solve_jumping_disks(4, 2)) == 2
assert len(solve_jumping_disks(5, 2)) == 3
assert len(solve_jumping_disks(4, 3)) == 1
"""),
        T("moves are (from, to) tuples of plain ints", """
moves = solve_jumping_disks(7, 3)
assert isinstance(moves, list)
for move in moves:
    assert isinstance(move, tuple) and len(move) == 2, "bad move %r" % (move,)
    assert all(isinstance(x, int) for x in move), "bad move %r" % (move,)
"""),
    ],
)


def _tf_moves(cells):
    """Legal (from, to) moves for toads ('T' move right) and frogs ('F' left)."""
    length = len(cells)
    for i, piece in enumerate(cells):
        if piece == '.':
            continue
        step = 1 if piece == 'T' else -1
        one = i + step
        if 0 <= one < length and cells[one] == '.':
            yield i, one
        two = i + 2 * step
        other = 'F' if piece == 'T' else 'T'
        if 0 <= two < length and cells[two] == '.' and cells[one] == other:
            yield i, two


def _tf_optimal(n):
    start = tuple(['T'] * n + ['.'] + ['F'] * n)
    goal = tuple(['F'] * n + ['.'] + ['T'] * n)
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cells = queue.popleft()
        if cells == goal:
            return dist[cells]
        for src, dst in _tf_moves(cells):
            nxt = list(cells)
            nxt[dst], nxt[src] = nxt[src], '.'
            nxt = tuple(nxt)
            if nxt not in dist:
                dist[nxt] = dist[cells] + 1
                queue.append(nxt)
    return None


_TF_OPT = {n: _tf_optimal(n) for n in range(1, 6)}


problem(
    id="toads-and-frogs",
    track="Movement Puzzles",
    title="Toads and Frogs",
    difficulty="hard",
    points=25,
    blurb="Two columns of pieces must pass through each other through a single gap.",
    statement="""
<p>A row of <code>2n + 1</code> cells holds <code>n</code> <strong>toads</strong>
on the left (cells <code>0 .. n-1</code>), a single empty cell in the middle
(cell <code>n</code>), and <code>n</code> <strong>frogs</strong> on the right
(cells <code>n+1 .. 2n</code>).</p>

<p>Toads only ever move right; frogs only ever move left. Neither species can
back up. A piece may:</p>
<ul>
  <li><strong>slide</strong> one cell forward, if that cell is empty; or</li>
  <li><strong>jump</strong> two cells forward, if the cell it passes over holds
      a piece of the <em>other</em> species and the landing cell is empty.</li>
</ul>
<p>A piece may never jump over one of its own kind.</p>

<p>Write <code>solve_toads_and_frogs(n)</code>, returning a shortest list of
<code>(from, to)</code> moves that ends with the frogs on the left, the toads
on the right, and the gap back in the middle. Use a breadth-first graph
search.</p>

<p>The optimum is <code>n * n + 2 * n</code> moves, which is a satisfying thing
to confirm empirically. It also grows fast enough that <code>n = 5</code> is
already a decent stress test of your visited set: get it wrong and the search
re-expands the same positions until it crawls.</p>
""",
    examples="""
>>> solve_toads_and_frogs(1)
[(0, 1), (2, 0), (1, 2)]
>>> len(solve_toads_and_frogs(2))
8
>>> len(solve_toads_and_frogs(3))
15
>>> len(solve_toads_and_frogs(4))
24
""",
    starter="""
def solve_toads_and_frogs(n):
    pass
""",
    hints=[
        "Represent the row as a tuple of characters, say 'T', 'F' and '.', so "
        "states are hashable and printing one tells you instantly what went "
        "wrong.",
        "Direction is a property of the piece, not the move: step = +1 for a "
        "toad and -1 for a frog, then slide is i + step and jump is i + 2 * "
        "step.",
        "The jump condition needs the middle cell to hold the OTHER species. "
        "Allowing jumps over your own kind quietly makes the puzzle easier and "
        "your move count too small.",
        "The goal is the exact mirror of the start: 'F' * n + '.' + 'T' * n.",
    ],
    solution="""
from collections import deque


def _successors(cells):
    length = len(cells)
    for i, piece in enumerate(cells):
        if piece == '.':
            continue
        step = 1 if piece == 'T' else -1
        other = 'F' if piece == 'T' else 'T'
        one = i + step
        if 0 <= one < length and cells[one] == '.':
            nxt = list(cells)
            nxt[one], nxt[i] = piece, '.'
            yield (i, one), tuple(nxt)
        two = i + 2 * step
        if 0 <= two < length and cells[two] == '.' and cells[one] == other:
            nxt = list(cells)
            nxt[two], nxt[i] = piece, '.'
            yield (i, two), tuple(nxt)


def solve_toads_and_frogs(n):
    start = tuple(['T'] * n + ['.'] + ['F'] * n)
    goal = tuple(['F'] * n + ['.'] + ['T'] * n)
    if start == goal:
        return []
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        cells, moves = frontier.popleft()
        for move, nxt in _successors(cells):
            if nxt in visited:
                continue
            if nxt == goal:
                return moves + [move]
            visited.add(nxt)
            frontier.append((nxt, moves + [move]))
    return None
""",
    tests=[
        T("n = 0 is already solved", """
assert solve_toads_and_frogs(0) == []
"""),
        T("every move obeys the direction and jump rules", """
def _check(n, moves):
    cells = ['T'] * n + ['.'] + ['F'] * n
    for src, dst in moves:
        assert 0 <= src < len(cells) and 0 <= dst < len(cells), "off the row"
        piece = cells[src]
        assert piece in 'TF', "no piece on cell %d" % src
        assert cells[dst] == '.', "cell %d is not empty" % dst
        step = dst - src
        forward = 1 if piece == 'T' else -1
        assert step in (forward, 2 * forward), \\
            "%s on cell %d cannot move to %d" % (piece, src, dst)
        if abs(step) == 2:
            middle = cells[src + forward]
            assert middle not in ('.', piece), \\
                "jump from %d must pass over the other species, saw %r" % (src, middle)
        cells[dst], cells[src] = piece, '.'
    assert cells == ['F'] * n + ['.'] + ['T'] * n, "ended at %r" % (''.join(cells),)


for n in range(1, 5):
    moves = solve_toads_and_frogs(n)
    assert moves is not None, "no solution for n=%d" % n
    _check(n, moves)
"""),
        T("solution length is exactly n*n + 2*n", """
for n, best in @@OPT@@.items():
    assert best == n * n + 2 * n
    moves = solve_toads_and_frogs(n)
    assert len(moves) == best, \\
        "n=%d solved in %d moves, optimum is %d" % (n, len(moves), best)
""", OPT=_TF_OPT),
        T("n = 1 has one of the two mirror solutions", """
moves = [tuple(m) for m in solve_toads_and_frogs(1)]
assert moves in ([(0, 1), (2, 0), (1, 2)], [(2, 1), (0, 2), (1, 0)]), moves
"""),
        T("pieces never move backwards", """
for n in (2, 3, 4):
    cells = ['T'] * n + ['.'] + ['F'] * n
    for src, dst in solve_toads_and_frogs(n):
        piece = cells[src]
        assert (dst > src) == (piece == 'T'), \\
            "n=%d: %s moved the wrong way (%d -> %d)" % (n, piece, src, dst)
        cells[dst], cells[src] = piece, '.'
"""),
    ],
)


def _slide_neighbours(board):
    rows, cols = len(board), len(board[0])
    blank = next((r, c) for r in range(rows) for c in range(cols)
                 if board[r][c] == 0)
    br, bc = blank
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = br + dr, bc + dc
        if 0 <= r < rows and 0 <= c < cols:
            grid = [list(row) for row in board]
            grid[br][bc], grid[r][c] = grid[r][c], 0
            yield (r, c), tuple(tuple(row) for row in grid)


def _slide_goal(rows, cols):
    values = list(range(1, rows * cols)) + [0]
    return tuple(tuple(values[r * cols:(r + 1) * cols]) for r in range(rows))


def _slide_optimal(board):
    board = tuple(tuple(row) for row in board)
    goal = _slide_goal(len(board), len(board[0]))
    if board == goal:
        return 0
    dist = {board: 0}
    queue = deque([board])
    while queue:
        state = queue.popleft()
        for _, nxt in _slide_neighbours(state):
            if nxt in dist:
                continue
            if nxt == goal:
                return dist[state] + 1
            dist[nxt] = dist[state] + 1
            queue.append(nxt)
    return None


def _slide_scramble(rows, cols, moves):
    board = _slide_goal(rows, cols)
    for tile in moves:
        board = dict(_slide_neighbours(board))[tile]
    return [list(row) for row in board]


_SLIDE_A = _slide_scramble(2, 3, [(1, 1), (1, 0), (0, 0)])
_SLIDE_B = _slide_scramble(2, 3, [(0, 2), (0, 1), (1, 1), (1, 0), (0, 0), (0, 1)])
_SLIDE_C = _slide_scramble(3, 2, [(1, 1), (1, 0), (0, 0), (0, 1), (1, 1), (2, 1)])
_SLIDE_A_LEN = _slide_optimal(_SLIDE_A)
_SLIDE_B_LEN = _slide_optimal(_SLIDE_B)
_SLIDE_C_LEN = _slide_optimal(_SLIDE_C)


problem(
    id="sliding-tiles",
    track="Movement Puzzles",
    title="Mini Sliding Tiles",
    difficulty="medium",
    points=20,
    blurb="The 8-puzzle's small cousin, where half of all boards are unsolvable.",
    statement="""
<p>A sliding-tile board is a tuple of tuples of integers. Tile <code>0</code>
is the blank. A move slides one tile that is orthogonally adjacent to the blank
into the blank's square. The goal state numbers the tiles
<code>1, 2, 3, ...</code> in row-major order with the blank last, so for a
2 &times; 3 board the goal is <code>((1, 2, 3), (4, 5, 0))</code>.</p>

<p>Write <code>solve_sliding_puzzle(board)</code>, returning a
<strong>shortest</strong> list of moves that reaches the goal, where each move
is the <code>(row, col)</code> of the tile being slid <em>at the moment it
moves</em>. Return <code>None</code> if the board cannot be solved, and
<code>[]</code> if it is already solved. Use a breadth-first graph search.</p>

<p>Exactly half of all scrambled boards are unsolvable, and BFS discovers this
the expensive way: by exhausting every state reachable from the start. That is
the honest cost of an uninformed search, and it is why the next unit is about
heuristics.</p>
""",
    examples="""
>>> solve_sliding_puzzle(((1, 2, 3), (4, 5, 0)))
[]
>>> solve_sliding_puzzle(((1, 2, 3), (4, 0, 5)))
[(1, 2)]
>>> solve_sliding_puzzle(((1, 2, 3), (0, 4, 5)))
[(1, 1), (1, 2)]
>>> solve_sliding_puzzle(((2, 1, 3), (4, 5, 0))) is None
True
>>> len(solve_sliding_puzzle(((4, 1, 2), (0, 5, 3))))
4
""",
    starter="""
def solve_sliding_puzzle(board):
    pass
""",
    hints=[
        "Do not hard-code the board size. rows = len(board) and "
        "cols = len(board[0]) let the same code solve 2x2, 2x3 and 3x2.",
        "Find the blank once per state, then the successors are the up to four "
        "in-bounds neighbours of the blank -- each swap gives you both the "
        "child state and the (row, col) of the tile that moved.",
        "Keep states as tuples of tuples so they hash. Convert lists to tuples "
        "once, at the top of the function.",
        "The unsolvable half is detected for free: BFS drains its frontier and "
        "falls out of the while loop. Just make sure you return None there "
        "instead of falling off the end and returning it by accident.",
    ],
    solution="""
from collections import deque


def _successors(board):
    rows, cols = len(board), len(board[0])
    br, bc = next((r, c) for r in range(rows) for c in range(cols)
                  if board[r][c] == 0)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = br + dr, bc + dc
        if 0 <= r < rows and 0 <= c < cols:
            grid = [list(row) for row in board]
            grid[br][bc], grid[r][c] = grid[r][c], 0
            yield (r, c), tuple(tuple(row) for row in grid)


def solve_sliding_puzzle(board):
    start = tuple(tuple(row) for row in board)
    rows, cols = len(start), len(start[0])
    values = list(range(1, rows * cols)) + [0]
    goal = tuple(tuple(values[r * cols:(r + 1) * cols]) for r in range(rows))
    if start == goal:
        return []
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        state, moves = frontier.popleft()
        for move, nxt in _successors(state):
            if nxt in visited:
                continue
            if nxt == goal:
                return moves + [move]
            visited.add(nxt)
            frontier.append((nxt, moves + [move]))
    return None
""",
    tests=[
        T("solved boards of several shapes need no moves", """
assert solve_sliding_puzzle(((1, 2, 3), (4, 5, 0))) == []
assert solve_sliding_puzzle(((1, 2), (3, 0))) == []
assert solve_sliding_puzzle(((1, 2), (3, 4), (5, 0))) == []
"""),
        T("one and two move boards", """
assert solve_sliding_puzzle(((1, 2, 3), (4, 0, 5))) == [(1, 2)]
assert solve_sliding_puzzle(((1, 2, 3), (0, 4, 5))) == [(1, 1), (1, 2)]
assert solve_sliding_puzzle(((1, 2, 0), (4, 5, 3))) == [(1, 2)]
"""),
        T("moves are legal and reach the goal", """
def _check(board, moves):
    grid = [list(row) for row in board]
    rows, cols = len(grid), len(grid[0])
    for r, c in moves:
        assert 0 <= r < rows and 0 <= c < cols, "move %r off the board" % ((r, c),)
        assert grid[r][c] != 0, "move %r slides the blank itself" % ((r, c),)
        br, bc = [(i, j) for i in range(rows) for j in range(cols)
                  if grid[i][j] == 0][0]
        assert abs(br - r) + abs(bc - c) == 1, \\
            "tile %r is not next to the blank at %r" % ((r, c), (br, bc))
        grid[br][bc], grid[r][c] = grid[r][c], 0
    values = list(range(1, rows * cols)) + [0]
    goal = [values[i * cols:(i + 1) * cols] for i in range(rows)]
    assert grid == goal, "ended at %r" % (grid,)


for board in [@@A@@, @@B@@, @@C@@]:
    board = tuple(tuple(row) for row in board)
    moves = solve_sliding_puzzle(board)
    assert moves is not None, "no solution for %r" % (board,)
    _check(board, moves)
""", A=_SLIDE_A, B=_SLIDE_B, C=_SLIDE_C),
        T("solutions are optimal", """
cases = [(@@A@@, @@ALEN@@), (@@B@@, @@BLEN@@), (@@C@@, @@CLEN@@)]
for board, best in cases:
    moves = solve_sliding_puzzle(tuple(tuple(row) for row in board))
    assert len(moves) == best, \\
        "%r solved in %d moves, optimum is %d" % (board, len(moves), best)
""", A=_SLIDE_A, ALEN=_SLIDE_A_LEN, B=_SLIDE_B, BLEN=_SLIDE_B_LEN,
     C=_SLIDE_C, CLEN=_SLIDE_C_LEN),
        T("unsolvable boards return None", """
assert solve_sliding_puzzle(((2, 1, 3), (4, 5, 0))) is None
assert solve_sliding_puzzle(((1, 2, 3), (5, 4, 0))) is None
assert solve_sliding_puzzle(((2, 1), (3, 0))) is None
"""),
        T("agrees with exhaustive search on a sample of 2x3 boards", """
from collections import deque
from itertools import permutations

goal = ((1, 2, 3), (4, 5, 0))


def _children(state):
    br, bc = [(r, c) for r in range(2) for c in range(3) if state[r][c] == 0][0]
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = br + dr, bc + dc
        if 0 <= r < 2 and 0 <= c < 3:
            grid = [list(row) for row in state]
            grid[br][bc], grid[r][c] = grid[r][c], 0
            yield tuple(tuple(row) for row in grid)


dist = {goal: 0}
queue = deque([goal])
while queue:
    state = queue.popleft()
    for nxt in _children(state):
        if nxt not in dist:
            dist[nxt] = dist[state] + 1
            queue.append(nxt)

checked = 0
for index, perm in enumerate(permutations(range(6))):
    if index % 9:
        continue
    board = (perm[:3], perm[3:])
    got = solve_sliding_puzzle(board)
    if board not in dist:
        assert got is None, "%r is unsolvable but got %r" % (board, got)
    else:
        assert got is not None and len(got) == dist[board], \\
            "%r solved in %r, optimum is %d" % (board, got, dist[board])
    checked += 1
assert checked == 80
"""),
    ],
)


def _jug_successors(state, capacities):
    for i, amount in enumerate(state):
        if amount < capacities[i]:
            nxt = list(state)
            nxt[i] = capacities[i]
            yield ("fill", i), tuple(nxt)
        if amount > 0:
            nxt = list(state)
            nxt[i] = 0
            yield ("empty", i), tuple(nxt)
        for j in range(len(state)):
            if i == j or amount == 0 or state[j] == capacities[j]:
                continue
            moved = min(amount, capacities[j] - state[j])
            nxt = list(state)
            nxt[i] -= moved
            nxt[j] += moved
            yield ("pour", i, j), tuple(nxt)


def _jug_optimal(capacities, target):
    start = tuple(0 for _ in capacities)
    if target in start:
        return 0
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for _, nxt in _jug_successors(state, capacities):
            if nxt in dist:
                continue
            if target in nxt:
                return dist[state] + 1
            dist[nxt] = dist[state] + 1
            queue.append(nxt)
    return None


_JUG_CASES = [((3, 5), 4), ((5, 3), 4), ((4, 9), 6), ((2, 6), 5),
              ((3, 5, 8), 7), ((7, 11), 2), ((6, 10), 3)]
_JUG_OPT = {case: _jug_optimal(*case) for case in _JUG_CASES}


problem(
    id="water-jugs",
    track="Classic Searches",
    title="Water Jugs",
    difficulty="medium",
    points=20,
    blurb="Unmarked jugs, three actions, and a target volume to hit exactly.",
    statement="""
<p>You are given a tuple of jug <code>capacities</code> in litres. Every jug
starts empty, the jugs have no markings, and you have unlimited water and a
drain. Three actions are available:</p>

<ul>
  <li><code>("fill", i)</code> &mdash; fill jug <code>i</code> to its capacity.</li>
  <li><code>("empty", i)</code> &mdash; pour jug <code>i</code> out.</li>
  <li><code>("pour", i, j)</code> &mdash; pour jug <code>i</code> into jug
      <code>j</code> until <code>j</code> is full or <code>i</code> is empty.</li>
</ul>

<p>Write <code>solve_water_jugs(capacities, target)</code>, returning a
shortest list of actions after which <strong>some</strong> jug holds exactly
<code>target</code> litres, or <code>None</code> if that is impossible. Use a
breadth-first graph search over tuples of jug contents.</p>

<p>An action that changes nothing &mdash; filling a full jug, emptying an empty
one, pouring into a jug that is already full &mdash; is a wasted branch. You
can either skip generating it or let the visited set absorb it; try both and
watch what happens to the number of states you expand.</p>
""",
    examples="""
>>> solve_water_jugs((3, 5), 0)
[]
>>> solve_water_jugs((3, 5), 3)
[('fill', 0)]
>>> len(solve_water_jugs((3, 5), 4))
6
>>> solve_water_jugs((2, 6), 5) is None
True
>>> len(solve_water_jugs((4, 9), 6))
8
""",
    starter="""
def solve_water_jugs(capacities, target):
    pass
""",
    hints=[
        "A state is a tuple of current volumes, one per jug -- already "
        "hashable, so it drops straight into a visited set.",
        "The amount that actually moves in a pour is "
        "min(state[i], capacities[j] - state[j]).",
        "The goal test is 'target in state', not 'state[0] == target'. Any jug "
        "counts.",
        "target is reachable only if it is a multiple of the gcd of the "
        "capacities and no larger than the biggest jug -- worth knowing, but "
        "let the search discover it so you also get the move list.",
    ],
    solution="""
from collections import deque


def _successors(state, capacities):
    for i, amount in enumerate(state):
        if amount < capacities[i]:
            nxt = list(state)
            nxt[i] = capacities[i]
            yield ("fill", i), tuple(nxt)
        if amount > 0:
            nxt = list(state)
            nxt[i] = 0
            yield ("empty", i), tuple(nxt)
        for j in range(len(state)):
            if i == j or amount == 0 or state[j] == capacities[j]:
                continue
            moved = min(amount, capacities[j] - state[j])
            nxt = list(state)
            nxt[i] -= moved
            nxt[j] += moved
            yield ("pour", i, j), tuple(nxt)


def solve_water_jugs(capacities, target):
    start = tuple(0 for _ in capacities)
    if target in start:
        return []
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        state, actions = frontier.popleft()
        for action, nxt in _successors(state, capacities):
            if nxt in visited:
                continue
            if target in nxt:
                return actions + [action]
            visited.add(nxt)
            frontier.append((nxt, actions + [action]))
    return None
""",
    tests=[
        T("an empty jug already holds zero litres", """
assert solve_water_jugs((3, 5), 0) == []
assert solve_water_jugs((7,), 0) == []
"""),
        T("one fill is enough when the target is a capacity", """
assert solve_water_jugs((3, 5), 3) == [("fill", 0)]
assert solve_water_jugs((3, 5), 5) == [("fill", 1)]
"""),
        T("actions are legal and end on the target", """
def _replay(capacities, actions):
    state = [0] * len(capacities)
    for action in actions:
        action = tuple(action)
        kind = action[0]
        if kind == "fill":
            (_, i) = action
            state[i] = capacities[i]
        elif kind == "empty":
            (_, i) = action
            state[i] = 0
        elif kind == "pour":
            (_, i, j) = action
            moved = min(state[i], capacities[j] - state[j])
            state[i] -= moved
            state[j] += moved
        else:
            raise AssertionError("unknown action %r" % (action,))
    return state


for capacities, target in @@CASES@@:
    actions = solve_water_jugs(capacities, target)
    if actions is None:
        continue
    state = _replay(capacities, actions)
    assert target in state, \\
        "%r on %r ended at %r, target %d" % (actions, capacities, state, target)
""", CASES=_JUG_CASES),
        T("solutions are of minimal length", """
for (capacities, target), best in @@OPT@@.items():
    actions = solve_water_jugs(capacities, target)
    if best is None:
        assert actions is None, "%r/%d is impossible but got %r" % (
            capacities, target, actions)
        continue
    assert actions is not None, "%r/%d has a solution" % (capacities, target)
    assert len(actions) == best, "%r/%d solved in %d actions, optimum is %d" % (
        capacities, target, len(actions), best)
""", OPT=_JUG_OPT),
        T("impossible targets return None", """
assert solve_water_jugs((2, 6), 5) is None
assert solve_water_jugs((4, 6), 3) is None
assert solve_water_jugs((3, 5), 9) is None
assert solve_water_jugs((6, 10), 4) is not None
"""),
        T("three jugs still work", """
actions = solve_water_jugs((3, 5, 8), 7)
assert actions is not None
assert len(actions) == @@BEST@@
""", BEST=_JUG_OPT[((3, 5, 8), 7)]),
    ],
)


def _knight_optimal(n, start, end, blocked):
    blocked = set(blocked)
    if start in blocked or end in blocked:
        return None
    if start == end:
        return 1
    deltas = ((1, 2), (2, 1), (-1, 2), (-2, 1),
              (1, -2), (2, -1), (-1, -2), (-2, -1))
    dist = {start: 1}
    queue = deque([start])
    while queue:
        r, c = queue.popleft()
        for dr, dc in deltas:
            nxt = (r + dr, c + dc)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if nxt in blocked or nxt in dist:
                continue
            dist[nxt] = dist[(r, c)] + 1
            if nxt == end:
                return dist[nxt]
            queue.append(nxt)
    return None


_KNIGHT_CASES = [
    (8, (0, 0), (7, 7), []),
    (8, (0, 0), (1, 1), []),
    (8, (0, 0), (0, 1), []),
    (5, (0, 0), (4, 4), [(1, 2), (2, 1)]),
    (6, (0, 0), (5, 5), [(1, 2), (2, 1), (3, 4), (4, 3)]),
    (4, (0, 0), (3, 3), []),
    (3, (0, 0), (1, 1), []),
]
_KNIGHT_OPT = {(n, s, e, tuple(b)): _knight_optimal(n, s, e, b)
               for n, s, e, b in _KNIGHT_CASES}


problem(
    id="knight-path",
    track="Classic Searches",
    title="Knight's Shortest Path",
    difficulty="easy",
    points=15,
    blurb="BFS on a chessboard graph, with rubble in the way and dead ends to detect.",
    statement="""
<p>A knight stands on an <code>n</code> &times; <code>n</code> board at
<code>start</code>, given as a <code>(row, col)</code> tuple. It moves in the
usual L: two squares one way and one square perpendicular, eight candidate
moves in all, and it may not land outside the board or on any square listed in
<code>blocked</code>.</p>

<p>Write <code>knight_shortest_path(n, start, end, blocked)</code>, returning a
shortest path as a list of squares <strong>including both endpoints</strong>,
or <code>None</code> if the knight cannot reach <code>end</code>. A knight
already standing on the target returns <code>[start]</code>. If either endpoint
is itself blocked, there is no path.</p>

<p>This is the purest breadth-first search in the gym: the state <em>is</em> a
square, so the graph is small and the whole exercise is bookkeeping. Get the
path reconstruction right here &mdash; storing a parent pointer per square and
walking backwards is the pattern you will reuse everywhere.</p>
""",
    examples="""
>>> knight_shortest_path(8, (0, 0), (0, 0), [])
[(0, 0)]
>>> knight_shortest_path(8, (0, 0), (1, 2), [])
[(0, 0), (1, 2)]
>>> len(knight_shortest_path(8, (0, 0), (7, 7), []))
7
>>> len(knight_shortest_path(8, (0, 0), (1, 1), []))
5
>>> knight_shortest_path(3, (0, 0), (1, 1), []) is None
True
""",
    starter="""
def knight_shortest_path(n, start, end, blocked):
    pass
""",
    hints=[
        "Write the eight offsets out once as a tuple of (dr, dc) pairs; "
        "generating them from products of (1, 2) and signs is cute but easy to "
        "get subtly wrong.",
        "Check three things before enqueueing a square: on the board, not "
        "blocked, not already visited.",
        "Keep a dict mapping each square to the square you came from, then "
        "rebuild the path by walking back from end and reversing.",
        "The centre of a 3x3 board is unreachable from anywhere -- a useful "
        "reminder to handle 'frontier empty' as a real outcome.",
    ],
    solution="""
from collections import deque

_DELTAS = ((1, 2), (2, 1), (-1, 2), (-2, 1),
           (1, -2), (2, -1), (-1, -2), (-2, -1))


def knight_shortest_path(n, start, end, blocked):
    blocked = set(blocked)
    start, end = tuple(start), tuple(end)
    if start in blocked or end in blocked:
        return None
    if start == end:
        return [start]
    parent = {start: None}
    frontier = deque([start])
    while frontier:
        square = frontier.popleft()
        row, col = square
        for dr, dc in _DELTAS:
            nxt = (row + dr, col + dc)
            if not (0 <= nxt[0] < n and 0 <= nxt[1] < n):
                continue
            if nxt in blocked or nxt in parent:
                continue
            parent[nxt] = square
            if nxt == end:
                path = [nxt]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                return path[::-1]
            frontier.append(nxt)
    return None
""",
    tests=[
        T("a knight already on the target", """
assert knight_shortest_path(8, (0, 0), (0, 0), []) == [(0, 0)]
assert knight_shortest_path(5, (2, 2), (2, 2), []) == [(2, 2)]
assert knight_shortest_path(8, (3, 3), (3, 3), [(0, 0)]) == [(3, 3)]
"""),
        T("single hops", """
assert knight_shortest_path(8, (0, 0), (1, 2), []) == [(0, 0), (1, 2)]
assert knight_shortest_path(8, (4, 4), (2, 3), []) == [(4, 4), (2, 3)]
"""),
        T("paths are legal knight moves inside the board", """
def _check(n, start, end, blocked, path):
    blocked = set(blocked)
    assert path[0] == tuple(start), "path starts at %r" % (path[0],)
    assert path[-1] == tuple(end), "path ends at %r" % (path[-1],)
    for square in path:
        assert 0 <= square[0] < n and 0 <= square[1] < n, "%r is off the board" % (square,)
        assert square not in blocked, "%r is blocked" % (square,)
    for a, b in zip(path, path[1:]):
        step = sorted((abs(a[0] - b[0]), abs(a[1] - b[1])))
        assert step == [1, 2], "%r -> %r is not a knight move" % (a, b)


for n, start, end, blocked in @@CASES@@:
    path = knight_shortest_path(n, start, end, list(blocked))
    if path is None:
        continue
    _check(n, start, end, blocked, [tuple(sq) for sq in path])
""", CASES=_KNIGHT_CASES),
        T("paths are shortest", """
for (n, start, end, blocked), best in @@OPT@@.items():
    path = knight_shortest_path(n, start, end, list(blocked))
    if best is None:
        assert path is None, "(%d, %r, %r) is unreachable but got %r" % (
            n, start, end, path)
        continue
    assert path is not None, "(%d, %r, %r) is reachable" % (n, start, end)
    assert len(path) == best, "(%d, %r, %r) gave %d squares, shortest is %d" % (
        n, start, end, len(path), best)
""", OPT=_KNIGHT_OPT),
        T("blocked squares are respected", """
path = knight_shortest_path(8, (0, 0), (1, 1), [(2, 2)])
assert path is not None
assert (2, 2) not in [tuple(sq) for sq in path]
assert knight_shortest_path(8, (0, 0), (7, 7), [(7, 7)]) is None
assert knight_shortest_path(8, (0, 0), (7, 7), [(0, 0)]) is None
"""),
        T("unreachable targets return None", """
assert knight_shortest_path(3, (0, 0), (1, 1), []) is None
assert knight_shortest_path(1, (0, 0), (0, 0), []) == [(0, 0)]
assert knight_shortest_path(4, (0, 0), (1, 1), [(2, 2), (1, 2), (2, 1), (2, 3), (3, 2)]) is None
"""),
        T("agrees with an independent BFS across a whole board", """
from collections import deque

DELTAS = ((1, 2), (2, 1), (-1, 2), (-2, 1),
          (1, -2), (2, -1), (-1, -2), (-2, -1))
n = 6
blocked = {(2, 2), (3, 3)}
start = (0, 0)
dist = {start: 1}
queue = deque([start])
while queue:
    r, c = queue.popleft()
    for dr, dc in DELTAS:
        nxt = (r + dr, c + dc)
        if 0 <= nxt[0] < n and 0 <= nxt[1] < n and nxt not in blocked \\
                and nxt not in dist:
            dist[nxt] = dist[(r, c)] + 1
            queue.append(nxt)

for r in range(n):
    for c in range(n):
        end = (r, c)
        path = knight_shortest_path(n, start, end, list(blocked))
        if end in blocked or end not in dist:
            assert path is None, "%r should be unreachable, got %r" % (end, path)
        else:
            assert path is not None, "%r should be reachable" % (end,)
            assert len(path) == dist[end], \\
                "%r gave %d squares, shortest is %d" % (end, len(path), dist[end])
"""),
    ],
)


def _river_safe(m, c, total_m, total_c):
    if m < 0 or c < 0 or m > total_m or c > total_c:
        return False
    if m and m < c:
        return False
    right_m, right_c = total_m - m, total_c - c
    if right_m and right_m < right_c:
        return False
    return True


def _river_successors(state, total_m, total_c, capacity):
    m, c, boat = state
    sign = -1 if boat == 0 else 1
    for dm in range(capacity + 1):
        for dc in range(capacity + 1 - dm):
            if dm + dc == 0:
                continue
            if boat == 0 and (dm > m or dc > c):
                continue
            if boat == 1 and (dm > total_m - m or dc > total_c - c):
                continue
            if dm and dm < dc:
                continue
            nm, nc = m + sign * dm, c + sign * dc
            if not _river_safe(nm, nc, total_m, total_c):
                continue
            yield (dm, dc), (nm, nc, 1 - boat)


def _river_optimal(m, c, capacity):
    start = (m, c, 0)
    goal = (0, 0, 1)
    if start == goal:
        return 0
    if not _river_safe(m, c, m, c):
        return None
    dist = {start: 0}
    queue = deque([start])
    while queue:
        state = queue.popleft()
        for _, nxt in _river_successors(state, m, c, capacity):
            if nxt in dist:
                continue
            if nxt == goal:
                return dist[state] + 1
            dist[nxt] = dist[state] + 1
            queue.append(nxt)
    return None


_RIVER_CASES = [(3, 3, 2), (3, 3, 3), (2, 2, 2), (1, 1, 1),
                (4, 4, 2), (4, 4, 3), (5, 5, 3), (5, 5, 2), (0, 3, 2)]
_RIVER_OPT = {case: _river_optimal(*case) for case in _RIVER_CASES}


problem(
    id="river-crossing",
    track="Classic Searches",
    title="Missionaries and Cannibals",
    difficulty="hard",
    points=25,
    blurb="A tiny state space with a constraint that has to hold on both banks at once.",
    statement="""
<p><code>missionaries</code> missionaries and <code>cannibals</code> cannibals
stand on the left bank with one boat that seats <code>capacity</code> people.
Everyone must end up on the right bank.</p>

<p>Rules:</p>
<ul>
  <li>The boat carries between 1 and <code>capacity</code> people per crossing
      and cannot cross empty.</li>
  <li>On <strong>either</strong> bank, if any missionaries are present they must
      not be outnumbered by cannibals. A bank with zero missionaries is always
      fine.</li>
  <li>The rule is checked after each crossing lands, counting the people who
      just stepped off the boat as being on that bank. It is also checked on
      the bank the boat just left.</li>
  <li>The boat itself must be safe while crossing: it may not carry more
      cannibals than missionaries unless it carries no missionaries at all.</li>
</ul>

<p>Write <code>solve_river_crossing(missionaries, cannibals, capacity)</code>,
returning a shortest list of crossings, each a
<code>(missionaries_moved, cannibals_moved)</code> tuple, or <code>None</code>
if there is no safe schedule. Crossings alternate direction, starting left to
right, so the direction is implied by the index and does not appear in the
move.</p>

<p>The classic 3-3-2 instance takes 11 crossings; 4-4-2 is famously impossible
no matter how you shuffle. Both answers fall out of the same search, which is
the whole point of encoding constraints into the successor function rather than
into clever case analysis.</p>
""",
    examples="""
>>> solve_river_crossing(0, 0, 2)
[]
>>> solve_river_crossing(1, 1, 2)
[(1, 1)]
>>> len(solve_river_crossing(3, 3, 2))
11
>>> len(solve_river_crossing(3, 3, 3))
5
>>> solve_river_crossing(4, 4, 2) is None
True
""",
    starter="""
def solve_river_crossing(missionaries, cannibals, capacity):
    pass
""",
    hints=[
        "Three numbers describe the world completely: missionaries on the "
        "left, cannibals on the left, and which side the boat is on. Everything "
        "else is implied by subtraction.",
        "Enumerate boat loads as pairs (dm, dc) with dm + dc between 1 and "
        "capacity, then filter: enough people on the departing bank, a safe "
        "boat, and a safe state on both banks afterwards.",
        "A bank is safe when it has no missionaries, or at least as many "
        "missionaries as cannibals. Write that as one helper and call it for "
        "both banks.",
        "Do not forget the boat load itself must be safe -- (1, 2) is never a "
        "legal load even when both banks would survive it.",
    ],
    solution="""
from collections import deque


def _safe(m, c, total_m, total_c):
    if m < 0 or c < 0 or m > total_m or c > total_c:
        return False
    if m and m < c:
        return False
    right_m, right_c = total_m - m, total_c - c
    if right_m and right_m < right_c:
        return False
    return True


def solve_river_crossing(missionaries, cannibals, capacity):
    total_m, total_c = missionaries, cannibals
    start = (total_m, total_c, 0)
    goal = (0, 0, 1)
    if start[:2] == (0, 0):
        return []
    if not _safe(total_m, total_c, total_m, total_c):
        return None
    visited = {start}
    frontier = deque([(start, [])])
    while frontier:
        (m, c, boat), moves = frontier.popleft()
        sign = -1 if boat == 0 else 1
        for dm in range(capacity + 1):
            for dc in range(capacity + 1 - dm):
                if dm + dc == 0:
                    continue
                if dm and dm < dc:
                    continue
                if boat == 0 and (dm > m or dc > c):
                    continue
                if boat == 1 and (dm > total_m - m or dc > total_c - c):
                    continue
                nxt = (m + sign * dm, c + sign * dc, 1 - boat)
                if not _safe(nxt[0], nxt[1], total_m, total_c):
                    continue
                if nxt in visited:
                    continue
                if nxt == goal:
                    return moves + [(dm, dc)]
                visited.add(nxt)
                frontier.append((nxt, moves + [(dm, dc)]))
    return None
""",
    tests=[
        T("nobody to move", """
assert solve_river_crossing(0, 0, 2) == []
assert solve_river_crossing(0, 0, 1) == []
"""),
        T("one crossing is enough for small parties", """
assert solve_river_crossing(1, 1, 2) == [(1, 1)]
assert solve_river_crossing(0, 2, 2) == [(0, 2)]
assert solve_river_crossing(2, 2, 4) == [(2, 2)]
"""),
        T("crossings are legal and land everyone safely", """
def _check(total_m, total_c, capacity, moves):
    m, c, boat = total_m, total_c, 0
    for dm, dc in moves:
        assert dm >= 0 and dc >= 0 and 1 <= dm + dc <= capacity, \\
            "illegal boat load %r" % ((dm, dc),)
        assert not (dm and dm < dc), "boat load %r is unsafe" % ((dm, dc),)
        if boat == 0:
            assert dm <= m and dc <= c, "not enough people on the left bank"
            m, c = m - dm, c - dc
        else:
            assert dm <= total_m - m and dc <= total_c - c, \\
                "not enough people on the right bank"
            m, c = m + dm, c + dc
        boat = 1 - boat
        for bm, bc in ((m, c), (total_m - m, total_c - c)):
            assert not (bm and bm < bc), \\
                "bank (%d, %d) is unsafe after %r" % (bm, bc, (dm, dc))
    assert (m, c, boat) == (0, 0, 1), \\
        "ended with %d missionaries and %d cannibals on the left" % (m, c)


for total_m, total_c, capacity in @@CASES@@:
    moves = solve_river_crossing(total_m, total_c, capacity)
    if moves is None:
        continue
    _check(total_m, total_c, capacity, [tuple(x) for x in moves])
""", CASES=_RIVER_CASES),
        T("schedules are shortest", """
for (total_m, total_c, capacity), best in @@OPT@@.items():
    moves = solve_river_crossing(total_m, total_c, capacity)
    label = "(%d, %d, %d)" % (total_m, total_c, capacity)
    if best is None:
        assert moves is None, "%s is impossible but got %r" % (label, moves)
        continue
    assert moves is not None, "%s has a solution" % label
    assert len(moves) == best, "%s took %d crossings, optimum is %d" % (
        label, len(moves), best)
""", OPT=_RIVER_OPT),
        T("the classic instances", """
assert len(solve_river_crossing(3, 3, 2)) == 11
assert solve_river_crossing(4, 4, 2) is None
assert solve_river_crossing(4, 4, 3) is not None
"""),
        T("cannibals alone are never a problem", """
for c in range(1, 6):
    moves = solve_river_crossing(0, c, 2)
    assert moves is not None, "0 missionaries and %d cannibals is always fine" % c
    assert all(dm == 0 for dm, dc in moves)
"""),
    ],
)


# --------------------------------------------------------------------------
# Verification and output
# --------------------------------------------------------------------------

TRACKS = [
    ("Counting & Backtracking",
     "Size the space, then walk it with depth-first search."),
    ("Toggle Puzzles",
     "Grid states, commuting moves, and breadth-first graph search."),
    ("Movement Puzzles",
     "Pieces sliding around a board under awkward movement rules."),
    ("Classic Searches",
     "The textbook problems, stated so that BFS solves them directly."),
]


def run_tests(source, tests):
    """Run one problem's tests against `source`.  Returns a list of failures."""
    namespace = {"__name__": "__solution__"}
    exec(compile(source, "<solution>", "exec"), namespace)
    failures = []
    for test in tests:
        scope = dict(namespace)
        try:
            exec(compile(test["src"], "<test:%s>" % test["name"], "exec"), scope)
        except Exception as exc:
            failures.append((test["name"], "%s: %s" % (type(exc).__name__, exc)))
    return failures


def main():
    import time
    total_tests = 0
    bad = 0
    for prob in PROBLEMS:
        started = time.time()
        failures = run_tests(prob["solution"], prob["tests"])
        elapsed = time.time() - started
        total_tests += len(prob["tests"])
        status = "ok  " if not failures else "FAIL"
        print("%s %-20s %2d tests  %5.2fs" %
              (status, prob["id"], len(prob["tests"]), elapsed))
        for name, message in failures:
            bad += 1
            print("       - %s -> %s" % (name, message))
        ids = [p["id"] for p in PROBLEMS]
        assert len(ids) == len(set(ids)), "duplicate problem id"
        assert prob["track"] in dict(TRACKS), \
            "%s has unknown track %r" % (prob["id"], prob["track"])
        compile(prob["starter"], "<starter>", "exec")

    print("\n%d problems, %d tests, %d failures" %
          (len(PROBLEMS), total_tests, bad))
    if bad:
        raise SystemExit(1)

    payload = {
        "tracks": [{"name": name, "blurb": blurb} for name, blurb in TRACKS],
        "problems": [
            {
                "id": p["id"],
                "track": p["track"],
                "title": p["title"],
                "difficulty": p["difficulty"],
                "points": p["points"],
                "blurb": p["blurb"],
                "statement": p["statement"].strip(),
                "examples": p["examples"].strip("\n"),
                "starter": p["starter"].strip("\n"),
                "hints": p["hints"],
                "solution": p["solution"].strip("\n"),
                "tests": p["tests"],
            }
            for p in PROBLEMS
        ],
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "problems.json")
    with open(out, "w") as handle:
        json.dump(payload, handle, indent=1)
    print("wrote %s (%.1f KB)" % (out, os.path.getsize(out) / 1024.0))


if __name__ == "__main__":
    main()
