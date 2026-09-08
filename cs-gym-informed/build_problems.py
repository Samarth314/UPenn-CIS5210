"""Build the CS Gym (Informed Search) problem bank.

Same contract as the uninformed gym: every problem carries a reference
solution and a test suite, and this script runs each reference solution
against its own tests before emitting problems.json, so a broken problem can
never reach the site.  Constants that are themselves search results -- optimal
costs, expansion counts, solution tallies -- are computed by oracles here and
spliced into the test source through ``@@NAME@@`` markers rather than being
hard-coded by hand.
"""

import doctest
import heapq
import io
import json
import os
from collections import deque

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
# Track 1 -- heuristics: estimating what is left, and proving it is safe
# --------------------------------------------------------------------------

problem(
    id="misplaced-tiles",
    track="Heuristics",
    title="Counting What Is Out of Place",
    difficulty="warmup",
    points=5,
    blurb="The simplest admissible heuristic for a sliding puzzle, and why the blank is excluded.",
    statement="""
<p>A sliding puzzle is a two-dimensional list holding the values
<code>0</code> through <code>r * c - 1</code>, where <code>0</code> is the
empty space. The solved board has <code>1</code> through <code>r * c - 1</code>
in row-major order with <code>0</code> in the lower-right corner.</p>

<p>Write <code>misplaced_tiles(board)</code>, returning the number of
<strong>numbered</strong> tiles that are not sitting where the solved board
would put them. The empty space is never counted.</p>

<p>That exclusion is the whole point of the exercise. Every legal move slides
exactly one numbered tile, so a board with <code>k</code> misplaced tiles needs
at least <code>k</code> more moves &mdash; the heuristic is admissible. Count
the blank too and a board one move from solved scores 2, which overestimates,
and A* built on it can return a path that is not shortest.</p>

<p>Your function must work for any rectangular board, not just 3 &times; 3.</p>
""",
    examples="""
>>> misplaced_tiles([[1, 2, 3], [4, 5, 6], [7, 8, 0]])
0
>>> misplaced_tiles([[1, 2, 3], [4, 5, 6], [7, 0, 8]])
1
>>> misplaced_tiles([[0, 1], [3, 2]])
2
>>> misplaced_tiles([[1, 2, 3, 4], [5, 6, 7, 0]])
0
""",
    starter="""
def misplaced_tiles(board):
    pass
""",
    hints=[
        "Walk the board with two nested loops and keep a running count. You "
        "need the row and column of each value, so iterate over indices "
        "rather than over the rows directly.",
        "The solved position of tile v is row (v - 1) // cols and column "
        "(v - 1) % cols. divmod(v - 1, cols) gives you both at once. Note "
        "that the divisor is the number of COLUMNS, which only matters once "
        "the board stops being square.",
        "Skip the cell holding 0 before you compare anything, otherwise the "
        "blank contributes a count of its own and the heuristic stops being "
        "admissible.",
    ],
    solution="""
def misplaced_tiles(board):
    rows, cols = len(board), len(board[0])
    count = 0
    for row in range(rows):
        for col in range(cols):
            value = board[row][col]
            if value == 0:
                continue
            goal_row, goal_col = divmod(value - 1, cols)
            if (row, col) != (goal_row, goal_col):
                count += 1
    return count
""",
    tests=[
        T("solved boards score zero", """
assert misplaced_tiles([[1, 2, 3], [4, 5, 6], [7, 8, 0]]) == 0
assert misplaced_tiles([[1, 2], [3, 0]]) == 0
assert misplaced_tiles([[1, 2, 3, 4], [5, 6, 7, 0]]) == 0
assert misplaced_tiles([[0]]) == 0
"""),
        T("the blank is never counted", """
# One move from solved: exactly one numbered tile moved, so the answer is 1.
assert misplaced_tiles([[1, 2, 3], [4, 5, 6], [7, 0, 8]]) == 1
assert misplaced_tiles([[1, 2, 3], [4, 5, 0], [7, 8, 6]]) == 1
# The blank sitting far from its home changes nothing on its own -- only
# tile 1 is actually out of place here.
assert misplaced_tiles([[0, 2, 3], [4, 5, 6], [7, 8, 1]]) == 1
"""),
        T("non-square boards use the column count", """
assert misplaced_tiles([[1, 2], [3, 4], [5, 0]]) == 0
assert misplaced_tiles([[2, 1], [3, 4], [5, 0]]) == 2
assert misplaced_tiles([[1, 2, 3, 4, 5], [6, 7, 8, 9, 0]]) == 0
assert misplaced_tiles([[5, 2, 3, 4, 1], [6, 7, 8, 9, 0]]) == 2
"""),
        T("scrambled boards, checked against a direct recount", """
import random
random.seed(11)
for trial in range(200):
    rows = random.randint(1, 4)
    cols = random.randint(1, 4)
    values = list(range(1, rows * cols)) + [0]
    random.shuffle(values)
    board = [values[r * cols:(r + 1) * cols] for r in range(rows)]
    expected = 0
    for r in range(rows):
        for c in range(cols):
            v = board[r][c]
            if v != 0 and (r * cols + c) != v - 1:
                expected += 1
    got = misplaced_tiles(board)
    assert got == expected, (board, got, expected)
"""),
        T("never overestimates the true distance", """
from collections import deque
# Brute-force every board reachable in a 2x3 puzzle and confirm the heuristic
# is a lower bound on the real number of moves remaining.
GOAL = (1, 2, 3, 4, 5, 0)
R, C = 2, 3


def neighbours(state):
    i = state.index(0)
    r, c = divmod(i, C)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C:
            j = nr * C + nc
            lst = list(state)
            lst[i], lst[j] = lst[j], lst[i]
            yield tuple(lst)


dist = {GOAL: 0}
queue = deque([GOAL])
while queue:
    cur = queue.popleft()
    for nxt in neighbours(cur):
        if nxt not in dist:
            dist[nxt] = dist[cur] + 1
            queue.append(nxt)

assert len(dist) == 360
for state, true_cost in dist.items():
    board = [list(state[r * C:(r + 1) * C]) for r in range(R)]
    h = misplaced_tiles(board)
    assert h <= true_cost, (board, h, true_cost)
"""),
    ],
)


problem(
    id="manhattan-any-goal",
    track="Heuristics",
    title="Manhattan Distance to an Arbitrary Goal",
    difficulty="easy",
    points=10,
    blurb="Manhattan distance when the goal board is handed to you instead of assumed.",
    statement="""
<p>Manhattan distance is the standard sliding-puzzle heuristic: for every
numbered tile, add the row distance plus the column distance between where it
sits and where it belongs, then sum over all tiles. It dominates the
misplaced-tile count &mdash; it is never smaller &mdash; while staying
admissible, because one move changes one tile's distance by exactly 1.</p>

<p>Write <code>manhattan(board, goal)</code>. Both arguments are rectangular
two-dimensional lists holding the same set of values, and <code>0</code> is
the empty space. Unlike the textbook version, <strong>the goal is a
parameter</strong>, so you cannot assume row-major order &mdash; the target
layout might be column-major, spiral, or arbitrary.</p>

<p>As before, the empty space contributes nothing.</p>
""",
    examples="""
>>> goal = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
>>> manhattan([[1, 2, 3], [4, 5, 6], [7, 8, 0]], goal)
0
>>> manhattan([[1, 2, 3], [4, 5, 6], [7, 0, 8]], goal)
1
>>> manhattan([[3, 2, 1], [4, 5, 6], [7, 8, 0]], goal)
4
>>> snake = [[1, 2, 3], [6, 5, 4], [7, 8, 0]]
>>> manhattan([[1, 2, 3], [4, 5, 6], [7, 8, 0]], snake)
4
""",
    starter="""
def manhattan(board, goal):
    pass
""",
    hints=[
        "You cannot compute the goal position arithmetically any more, so "
        "build a lookup first: one pass over goal producing {value: (row, "
        "col)}. A dict comprehension over both indices does it in a line.",
        "With that dict in hand, the second pass is the familiar one -- for "
        "each numbered tile at (r, c), add abs(r - gr) + abs(c - gc).",
        "Build the lookup once, before the loop. Calling goal-searching code "
        "inside the inner loop turns an O(n) heuristic into O(n^2), and this "
        "function runs at every node of a search.",
    ],
    solution="""
def manhattan(board, goal):
    homes = {}
    for row in range(len(goal)):
        for col in range(len(goal[0])):
            homes[goal[row][col]] = (row, col)

    total = 0
    for row in range(len(board)):
        for col in range(len(board[0])):
            value = board[row][col]
            if value == 0:
                continue
            goal_row, goal_col = homes[value]
            total += abs(row - goal_row) + abs(col - goal_col)
    return total
""",
    tests=[
        T("matches the row-major textbook cases", """
goal = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
assert manhattan([[1, 2, 3], [4, 5, 6], [7, 8, 0]], goal) == 0
assert manhattan([[1, 2, 3], [4, 5, 6], [7, 0, 8]], goal) == 1
assert manhattan([[1, 2, 3], [4, 0, 5], [7, 8, 6]], goal) == 2
assert manhattan([[3, 2, 1], [4, 5, 6], [7, 8, 0]], goal) == 4
"""),
        T("the goal really is honoured", """
snake = [[1, 2, 3], [6, 5, 4], [7, 8, 0]]
# Against the snake goal, the row-major board is NOT solved.
assert manhattan([[1, 2, 3], [6, 5, 4], [7, 8, 0]], snake) == 0
assert manhattan([[1, 2, 3], [4, 5, 6], [7, 8, 0]], snake) == 4
# A goal that is a pure transpose.
col_major = [[1, 3, 5], [2, 4, 6], [7, 8, 0]]
assert manhattan(col_major, col_major) == 0
assert manhattan([[1, 2, 3], [4, 5, 6], [7, 8, 0]], col_major) == 6
"""),
        T("blank excluded, non-square boards fine", """
goal = [[1, 2, 3, 4], [5, 6, 7, 0]]
assert manhattan([[1, 2, 3, 4], [5, 6, 7, 0]], goal) == 0
# Moving only the blank is impossible in isolation, but as a raw board the
# tile that swapped with it is the only contributor.
assert manhattan([[1, 2, 3, 4], [5, 6, 0, 7]], goal) == 1
assert manhattan([[0, 1], [2, 3]], [[1, 2], [3, 0]]) == 4
"""),
        T("dominates misplaced-tile count but stays admissible", """
from collections import deque
GOAL = (1, 2, 3, 4, 5, 0)
R, C = 2, 3
goal_board = [list(GOAL[r * C:(r + 1) * C]) for r in range(R)]


def neighbours(state):
    i = state.index(0)
    r, c = divmod(i, C)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C:
            j = nr * C + nc
            lst = list(state)
            lst[i], lst[j] = lst[j], lst[i]
            yield tuple(lst)


dist = {GOAL: 0}
queue = deque([GOAL])
while queue:
    cur = queue.popleft()
    for nxt in neighbours(cur):
        if nxt not in dist:
            dist[nxt] = dist[cur] + 1
            queue.append(nxt)

for state, true_cost in dist.items():
    board = [list(state[r * C:(r + 1) * C]) for r in range(R)]
    h = manhattan(board, goal_board)
    misplaced = sum(1 for i, v in enumerate(state)
                    if v != 0 and v - 1 != i)
    assert h <= true_cost, ("overestimates", board, h, true_cost)
    assert h >= misplaced, ("weaker than misplaced count", board, h, misplaced)
"""),
        T("random boards against a straightforward recount", """
import random
random.seed(5)
for trial in range(150):
    rows = random.randint(1, 4)
    cols = random.randint(1, 4)
    values = list(range(rows * cols))
    goal_vals = values[:]
    random.shuffle(goal_vals)
    board_vals = values[:]
    random.shuffle(board_vals)
    goal = [goal_vals[r * cols:(r + 1) * cols] for r in range(rows)]
    board = [board_vals[r * cols:(r + 1) * cols] for r in range(rows)]
    homes = {}
    for r in range(rows):
        for c in range(cols):
            homes[goal[r][c]] = (r, c)
    expected = 0
    for r in range(rows):
        for c in range(cols):
            v = board[r][c]
            if v == 0:
                continue
            gr, gc = homes[v]
            expected += abs(r - gr) + abs(c - gc)
    assert manhattan(board, goal) == expected, (board, goal)
"""),
    ],
)


problem(
    id="does-it-overestimate",
    track="Heuristics",
    title="Does This Heuristic Overestimate?",
    difficulty="medium",
    points=15,
    blurb="Prove a candidate heuristic admissible by brute-forcing the true distances.",
    statement="""
<p>A* only returns optimal answers if its heuristic is <strong>admissible</strong>
&mdash; it must never claim more moves than are really needed. Get that wrong
and nothing raises; the search simply returns a longer solution than the best
one, and you may not notice.</p>

<p>On a puzzle small enough to enumerate, you can settle the question by brute
force. Write <code>is_admissible(goal, successors, h)</code>, returning
<code>True</code> if <code>h(state) &le; </code> the true number of moves from
<code>state</code> to <code>goal</code>, for <strong>every</strong> state that
can reach the goal.</p>

<ul>
  <li><code>goal</code> &mdash; a hashable state, typically a tuple.</li>
  <li><code>successors(state)</code> &mdash; a function yielding the states one
      move away. Every move costs 1.</li>
  <li><code>h(state)</code> &mdash; a function returning a number.</li>
</ul>

<p>You may assume every move is <strong>reversible</strong>, which is true of
the sliding and disk puzzles this is aimed at. That means a single search
outward from <code>goal</code> reaches every relevant state at its true
distance, and you never have to search separately from each one.</p>

<p>Because every move costs exactly 1, a plain breadth-first search is the
right tool &mdash; no priority queue needed here.</p>
""",
    examples="""
>>> def line(state):            # states 0..4 in a row
...     for nxt in (state - 1, state + 1):
...         if 0 <= nxt <= 4:
...             yield nxt
...
>>> is_admissible(0, line, lambda s: s)
True
>>> is_admissible(0, line, lambda s: s + 1)
False
>>> is_admissible(0, line, lambda s: 0)
True
>>> is_admissible(0, line, lambda s: 2 * s)
False
""",
    starter="""
def is_admissible(goal, successors, h):
    pass
""",
    hints=[
        "Breadth-first search outward from goal, recording the depth at which "
        "each state is first reached. That depth IS the true distance, "
        "because every move costs 1 and moves are reversible.",
        "Use a dict rather than a set for the visited states -- you need the "
        "distance, not just the fact that you have been there.",
        "Check every state you found, not only the ones far from the goal. A "
        "heuristic that overestimates at a single state is still "
        "inadmissible, and h(goal) itself must not exceed 0.",
    ],
    solution="""
from collections import deque


def is_admissible(goal, successors, h):
    distance = {goal: 0}
    frontier = deque([goal])
    while frontier:
        state = frontier.popleft()
        for nxt in successors(state):
            if nxt not in distance:
                distance[nxt] = distance[state] + 1
                frontier.append(nxt)

    for state, true_cost in distance.items():
        if h(state) > true_cost:
            return False
    return True
""",
    tests=[
        T("the worked line example", """
def line(state):
    for nxt in (state - 1, state + 1):
        if 0 <= nxt <= 4:
            yield nxt


assert is_admissible(0, line, lambda s: s) is True
assert is_admissible(0, line, lambda s: s + 1) is False
assert is_admissible(0, line, lambda s: 0) is True
assert is_admissible(0, line, lambda s: 2 * s) is False
# The zero heuristic is admissible for anything.
assert is_admissible(3, line, lambda s: 0) is True
# Negative estimates are silly but never overestimate.
assert is_admissible(3, line, lambda s: -5) is True
"""),
        T("h at the goal itself must not exceed zero", """
def line(state):
    for nxt in (state - 1, state + 1):
        if 0 <= nxt <= 4:
            yield nxt


# True distance at the goal is 0, so any positive estimate there fails.
assert is_admissible(2, line, lambda s: 1 if s == 2 else 0) is False
assert is_admissible(2, line, lambda s: 0) is True
"""),
        T("a single bad state anywhere is enough to fail", """
def line(state):
    for nxt in (state - 1, state + 1):
        if 0 <= nxt <= 8:
            yield nxt


# Correct everywhere except state 7, which is deep in the space.
def sneaky(s):
    return 99 if s == 7 else abs(s)


assert is_admissible(0, line, lambda s: abs(s)) is True
assert is_admissible(0, line, sneaky) is False
"""),
        T("sliding puzzle: Manhattan yes, blank-counting Manhattan no", """
R, C = 2, 3
GOAL = (1, 2, 3, 4, 5, 0)


def slide(state):
    i = state.index(0)
    r, c = divmod(i, C)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C:
            j = nr * C + nc
            lst = list(state)
            lst[i], lst[j] = lst[j], lst[i]
            yield tuple(lst)


def manhattan(state):
    total = 0
    for i, v in enumerate(state):
        if v == 0:
            continue
        total += (abs(i // C - (v - 1) // C) + abs(i % C - (v - 1) % C))
    return total


def manhattan_with_blank(state):
    total = manhattan(state)
    i = state.index(0)
    total += abs(i // C - (R - 1)) + abs(i % C - (C - 1))
    return total


def misplaced(state):
    return sum(1 for i, v in enumerate(state) if v != 0 and v - 1 != i)


assert is_admissible(GOAL, slide, manhattan) is True
assert is_admissible(GOAL, slide, misplaced) is True
# Counting the blank is exactly the mistake that breaks admissibility.
assert is_admissible(GOAL, slide, manhattan_with_blank) is False
# Doubling an admissible heuristic overshoots.
assert is_admissible(GOAL, slide, lambda s: 2 * manhattan(s)) is False
"""),
        T("disk puzzle: the raw distance sum overestimates, halved it does not", """
LENGTH, N = 5, 3
GOAL = tuple([0] * (LENGTH - N) + list(range(N, 0, -1)))


def disks(state):
    for i in range(LENGTH):
        if state[i] == 0:
            continue
        for d in (1, 2, -1, -2):
            j = i + d
            if not (0 <= j < LENGTH) or state[j] != 0:
                continue
            if abs(d) == 2 and state[i + d // 2] == 0:
                continue
            lst = list(state)
            lst[i], lst[j] = lst[j], lst[i]
            yield tuple(lst)


def raw(state):
    return sum(abs(i - (LENGTH - v)) for i, v in enumerate(state) if v != 0)


def halved(state):
    return raw(state) / 2


# A single move shifts one disk by up to two cells, so the raw sum can be
# nearly double the real move count.
assert is_admissible(GOAL, disks, raw) is False
assert is_admissible(GOAL, disks, halved) is True
assert is_admissible(GOAL, disks, lambda s: 0) is True
"""),
        T("agrees with a direct recount over the whole state space", """
from collections import deque
import random
random.seed(13)

R, C = 2, 3
GOAL = (1, 2, 3, 4, 5, 0)


def slide(state):
    i = state.index(0)
    r, c = divmod(i, C)
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C:
            j = nr * C + nc
            lst = list(state)
            lst[i], lst[j] = lst[j], lst[i]
            yield tuple(lst)


truth = {GOAL: 0}
q = deque([GOAL])
while q:
    cur = q.popleft()
    for nxt in slide(cur):
        if nxt not in truth:
            truth[nxt] = truth[cur] + 1
            q.append(nxt)
assert len(truth) == 360

states = sorted(truth)
for trial in range(60):
    bumped = random.choice(states)
    delta = random.choice([-2, -1, 0, 1, 3])
    table = {s: truth[s] for s in states}
    table[bumped] = truth[bumped] + delta
    expected = all(table[s] <= truth[s] for s in states)
    got = is_admissible(GOAL, slide, lambda s: table[s])
    assert got == expected, (bumped, delta, got, expected)
"""),
    ],
)# --------------------------------------------------------------------------
# Track 2 -- the machinery A* is built out of
# --------------------------------------------------------------------------

problem(
    id="priority-tiebreak",
    track="A* Machinery",
    title="A Queue That Never Compares Payloads",
    difficulty="easy",
    points=10,
    blurb="Ties on f-cost are the norm, not the exception. Break them without touching the states.",
    statement="""
<p>Push <code>(cost, state)</code> tuples into a heap and the first time two
states share a cost, Python reaches for the second element and tries
<code>state &lt; state</code>. For anything without an ordering &mdash; a
board object, a dict, a set &mdash; that is a <code>TypeError</code> in the
middle of your search. Ties on <code>f</code> are extremely common in A*, so
this bites almost immediately.</p>

<p>Build a <code>SearchQueue</code> that sidesteps it entirely:</p>

<ul>
  <li><code>push(priority, item)</code> &mdash; add an item.</li>
  <li><code>pop()</code> &mdash; remove and return the item with the smallest
      priority. Among equal priorities, return the one pushed
      <strong>earliest</strong> (first in, first out).</li>
  <li><code>__len__</code> &mdash; how many items are queued, so
      <code>while queue:</code> works.</li>
</ul>

<p>The payloads are arbitrary and must never be compared with
<code>&lt;</code>. Popping from an empty queue should raise
<code>IndexError</code>.</p>
""",
    examples="""
>>> q = SearchQueue()
>>> q.push(5, "five")
>>> q.push(1, "one")
>>> q.push(5, "five again")
>>> len(q)
3
>>> q.pop()
'one'
>>> q.pop()
'five'
>>> q.pop()
'five again'
>>> len(q)
0
""",
    starter="""
class SearchQueue:

    def __init__(self):
        pass

    def push(self, priority, item):
        pass

    def pop(self):
        pass

    def __len__(self):
        pass
""",
    hints=[
        "Keep a monotonically increasing integer counter on the instance. "
        "Push (priority, counter, item) and bump the counter every time.",
        "Because no two entries ever share a counter, tuple comparison always "
        "resolves at the second element and the item in slot three is never "
        "reached. That is the whole trick.",
        "An increasing counter also gives you the FIFO tie-break for free -- "
        "earlier pushes carry smaller counters. heapq.heappush and "
        "heapq.heappop over a plain list are all you need.",
    ],
    solution="""
import heapq


class SearchQueue:

    def __init__(self):
        self._heap = []
        self._counter = 0

    def push(self, priority, item):
        heapq.heappush(self._heap, (priority, self._counter, item))
        self._counter += 1

    def pop(self):
        if not self._heap:
            raise IndexError("pop from an empty SearchQueue")
        return heapq.heappop(self._heap)[2]

    def __len__(self):
        return len(self._heap)
""",
    tests=[
        T("ordering and FIFO tie-breaking", """
q = SearchQueue()
q.push(5, "five")
q.push(1, "one")
q.push(5, "five again")
assert len(q) == 3
assert q.pop() == "one"
assert q.pop() == "five"
assert q.pop() == "five again"
assert len(q) == 0
"""),
        T("payloads are never compared", """
class Unorderable:
    def __init__(self, tag):
        self.tag = tag

    def __lt__(self, other):
        raise AssertionError("the queue compared two payloads")

    def __gt__(self, other):
        raise AssertionError("the queue compared two payloads")


q = SearchQueue()
items = [Unorderable(i) for i in range(40)]
for it in items:
    q.push(7, it)          # every single priority identical
seen = [q.pop().tag for _ in range(40)]
assert seen == list(range(40)), seen
"""),
        T("dicts, sets and lists as payloads", """
q = SearchQueue()
q.push(2, {"a": 1})
q.push(2, {1, 2, 3})
q.push(1, [9, 9])
assert q.pop() == [9, 9]
assert q.pop() == {"a": 1}
assert q.pop() == {1, 2, 3}
"""),
        T("empty pop raises IndexError", """
q = SearchQueue()
try:
    q.pop()
except IndexError:
    pass
else:
    raise AssertionError("expected IndexError from an empty queue")
q.push(1, "x")
assert q.pop() == "x"
try:
    q.pop()
except IndexError:
    pass
else:
    raise AssertionError("expected IndexError after draining the queue")
"""),
        T("interleaved pushes and pops stay sorted", """
import random
random.seed(17)
q = SearchQueue()
reference = []
tick = 0
for step in range(600):
    if reference and random.random() < 0.45:
        reference.sort(key=lambda pair: (pair[0], pair[1]))
        expected = reference.pop(0)
        assert q.pop() == expected[2], (step, expected)
    else:
        p = random.randint(0, 5)
        payload = {"n": tick}
        q.push(p, payload)
        reference.append((p, tick, payload))
        tick += 1
    assert len(q) == len(reference)
"""),
        T("float and negative priorities work", """
q = SearchQueue()
q.push(2.5, "b")
q.push(-1, "a")
q.push(10, "c")
q.push(2.5, "b2")
assert [q.pop() for _ in range(4)] == ["a", "b", "b2", "c"]
"""),
    ],
)


# -- oracles for the grid problems -----------------------------------------

TERRAIN = [
    [1, 1, 1, 9, 1, 1, 1],
    [1, 9, 1, 9, 1, 9, 1],
    [1, 9, 1, 1, 1, 9, 1],
    [1, 9, 9, 9, 9, 9, 1],
    [1, 1, 1, 0, 1, 1, 1],
    [9, 9, 1, 0, 1, 9, 9],
    [1, 1, 1, 0, 1, 1, 1],
]

MAZE = [
    [1, 0, 1, 1, 1],
    [1, 0, 1, 0, 1],
    [1, 1, 1, 0, 1],
    [0, 0, 1, 0, 1],
    [1, 1, 1, 0, 1],
]


def _grid_cost(grid, start, goal):
    """Cheapest total cost, paying grid[r][c] to ENTER a cell.  None if stuck."""
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == 0 or grid[goal[0]][goal[1]] == 0:
        return None
    dist = {start: 0}
    queue = [(0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if node == goal:
            return cost
        if cost > dist.get(node, float("inf")):
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = node[0] + dr, node[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 0:
                nxt = cost + grid[nr][nc]
                if nxt < dist.get((nr, nc), float("inf")):
                    dist[(nr, nc)] = nxt
                    heapq.heappush(queue, (nxt, (nr, nc)))
    return None


TERRAIN_CORNER = _grid_cost(TERRAIN, (0, 0), (6, 6))
TERRAIN_MID = _grid_cost(TERRAIN, (0, 0), (2, 4))
TERRAIN_WALLED = _grid_cost(TERRAIN, (0, 0), (4, 3))
MAZE_CORNER = _grid_cost(MAZE, (0, 0), (4, 4))
MAZE_BLOCKED = _grid_cost(MAZE, (0, 0), (3, 0))


def _knight_dist(n, start, goal, blocked):
    blocked = set(map(tuple, blocked))
    if tuple(start) in blocked or tuple(goal) in blocked:
        return None
    jumps = ((1, 2), (2, 1), (-1, 2), (-2, 1),
             (1, -2), (2, -1), (-1, -2), (-2, -1))
    seen = {tuple(start)}
    frontier = deque([(tuple(start), 0)])
    while frontier:
        (r, c), d = frontier.popleft()
        if (r, c) == tuple(goal):
            return d
        for dr, dc in jumps:
            nr, nc = r + dr, c + dc
            if (0 <= nr < n and 0 <= nc < n
                    and (nr, nc) not in blocked and (nr, nc) not in seen):
                seen.add((nr, nc))
                frontier.append(((nr, nc), d + 1))
    return None


KNIGHT_OPEN = _knight_dist(8, (0, 0), (7, 7), [])
KNIGHT_CORNER = _knight_dist(8, (0, 0), (1, 1), [])
KNIGHT_WALLED = _knight_dist(
    5, (0, 0), (4, 4), [(1, 2), (2, 1), (2, 3), (3, 2)])


problem(
    id="uniform-cost-grid",
    track="A* Machinery",
    title="Cheapest Crossing, No Heuristic Yet",
    difficulty="medium",
    points=15,
    blurb="Uniform-cost search over terrain, the h = 0 baseline every A* is measured against.",
    statement="""
<p>A grid of non-negative integers describes terrain. Moving costs you the
value of the cell you <strong>enter</strong> &mdash; you do not pay for the
cell you start on. A value of <code>0</code> is a wall you cannot enter at
all. Movement is four-way: up, down, left, right. No diagonals.</p>

<p>Write <code>min_travel_cost(grid, start, goal)</code>, returning the
smallest total cost of any route, or <code>None</code> if the goal is
unreachable or either endpoint sits on a wall.</p>

<p>This is A* with <code>h = 0</code>, better known as uniform-cost search or
Dijkstra's algorithm. Building it first is worth the trouble: it is the
baseline the next problem's heuristic has to beat, and it is what your A*
degenerates into when a heuristic returns nothing useful.</p>

<p>A plain breadth-first search will <em>not</em> work here. BFS finds the
route with the fewest steps, which on uneven terrain is frequently not the
cheapest one.</p>
""",
    examples="""
>>> flat = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
>>> min_travel_cost(flat, (0, 0), (2, 2))
4
>>> pricey = [[1, 9, 1], [1, 9, 1], [1, 1, 1]]
>>> min_travel_cost(pricey, (0, 0), (0, 2))
6
>>> walled = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
>>> print(min_travel_cost(walled, (0, 0), (0, 2)))
None
""",
    starter="""
def min_travel_cost(grid, start, goal):
    pass
""",
    hints=[
        "Use a heap of (cost_so_far, cell). Pop the cheapest cell, and if it "
        "is the goal you are done -- the first time a cell comes off the heap "
        "you already hold its cheapest cost.",
        "Do the goal test when you POP, not when you push. Testing on push "
        "returns the first route you stumble across rather than the cheapest.",
        "Add grid[nr][nc] -- the cost of the cell you are moving INTO -- and "
        "skip any cell whose value is 0. Keep a dict of best-known costs so a "
        "cell is not expanded again through a worse route.",
    ],
    solution="""
import heapq


def min_travel_cost(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == 0 or grid[goal[0]][goal[1]] == 0:
        return None

    best = {tuple(start): 0}
    queue = [(0, tuple(start))]
    while queue:
        cost, node = heapq.heappop(queue)
        if node == tuple(goal):
            return cost
        if cost > best.get(node, float("inf")):
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = node[0] + dr, node[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 0:
                nxt = cost + grid[nr][nc]
                if nxt < best.get((nr, nc), float("inf")):
                    best[(nr, nc)] = nxt
                    heapq.heappush(queue, (nxt, (nr, nc)))
    return None
""",
    tests=[
        T("the worked examples", """
flat = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
assert min_travel_cost(flat, (0, 0), (2, 2)) == 4
pricey = [[1, 9, 1], [1, 9, 1], [1, 1, 1]]
assert min_travel_cost(pricey, (0, 0), (0, 2)) == 6
walled = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
assert min_travel_cost(walled, (0, 0), (0, 2)) is None
"""),
        T("start equals goal costs nothing", """
flat = [[1, 1], [1, 1]]
assert min_travel_cost(flat, (0, 0), (0, 0)) == 0
assert min_travel_cost([[7]], (0, 0), (0, 0)) == 0
"""),
        T("endpoints on walls give None", """
grid = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
assert min_travel_cost(grid, (1, 1), (0, 0)) is None
assert min_travel_cost(grid, (0, 0), (1, 1)) is None
assert min_travel_cost(grid, (0, 0), (2, 2)) == 4
"""),
        T("cheapest is not the shortest -- BFS would fail", """
# The direct two-step route costs 20; going the long way round costs 5.
grid = [
    [1, 10, 1],
    [1, 10, 1],
    [1, 1, 1],
]
assert min_travel_cost(grid, (0, 0), (0, 2)) == 6
"""),
        T("terrain map against a Dijkstra oracle", """
TERRAIN = @@TERRAIN@@
assert min_travel_cost(TERRAIN, (0, 0), (6, 6)) == @@CORNER@@
assert min_travel_cost(TERRAIN, (0, 0), (2, 4)) == @@MID@@
assert min_travel_cost(TERRAIN, (0, 0), (4, 3)) is None
""", TERRAIN=TERRAIN, CORNER=TERRAIN_CORNER, MID=TERRAIN_MID),
        T("random grids against a reference implementation", """
import heapq
import random
random.seed(23)


def reference(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == 0 or grid[goal[0]][goal[1]] == 0:
        return None
    dist = {start: 0}
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist.get(u, float("inf")):
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = u[0] + dr, u[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 0:
                nd = d + grid[nr][nc]
                if nd < dist.get((nr, nc), float("inf")):
                    dist[(nr, nc)] = nd
                    heapq.heappush(pq, (nd, (nr, nc)))
    return None


for trial in range(120):
    rows = random.randint(1, 6)
    cols = random.randint(1, 6)
    grid = [[random.choice([0, 1, 1, 2, 5, 9]) for _ in range(cols)]
            for _ in range(rows)]
    start = (random.randrange(rows), random.randrange(cols))
    goal = (random.randrange(rows), random.randrange(cols))
    assert min_travel_cost(grid, start, goal) == reference(grid, start, goal), \\
        (grid, start, goal)
"""),
    ],
)


# --------------------------------------------------------------------------
# Track 3 -- full A* solvers
# --------------------------------------------------------------------------

problem(
    id="weighted-grid-path",
    track="A* Solvers",
    title="The Route Itself, With a Heuristic",
    difficulty="medium",
    points=20,
    blurb="Same terrain, but return the path -- and scale the heuristic so it stays admissible.",
    statement="""
<p>Same terrain model as the previous problem: four-way movement, entering a
cell costs <code>grid[r][c]</code>, and <code>0</code> is a wall. This time
return the route.</p>

<p>Write <code>cheapest_path(grid, start, goal)</code>, returning the list of
<code>(row, col)</code> tuples along a cheapest route, including both the
start and the goal. If several routes tie, any of them is fine. Return
<code>None</code> when there is no route, or when an endpoint is a wall.</p>

<p>Now use a heuristic &mdash; and be careful scaling it. Manhattan distance
counts <em>steps</em>, but a step here costs terrain, so raw Manhattan
distance is wrong in both directions depending on the map. Multiply it by the
smallest passable value anywhere on the grid and it becomes a genuine lower
bound on the remaining cost, since no step can ever be cheaper than that.</p>

<p>Reconstruct the route from a dict of predecessors rather than carrying a
growing list in every queue entry. Copying a path per successor turns a linear
search into a quadratic one.</p>
""",
    examples="""
>>> flat = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
>>> path = cheapest_path(flat, (0, 0), (0, 2))
>>> path[0], path[-1], len(path)
((0, 0), (0, 2), 3)
>>> pricey = [[1, 9, 1], [1, 9, 1], [1, 1, 1]]
>>> cheapest_path(pricey, (0, 0), (0, 2))
[(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2)]
>>> print(cheapest_path([[1, 0, 1]], (0, 0), (0, 2)))
None
""",
    starter="""
def cheapest_path(grid, start, goal):
    pass
""",
    hints=[
        "Let step = the minimum non-zero value in the whole grid.  Then "
        "h(cell) = step * (|dr| + |dc|) to the goal is admissible: every "
        "remaining move costs at least `step`.",
        "Push (g + h, counter, cell) and keep g in a separate dict. The "
        "counter is what stops Python comparing two cells when f ties.",
        "Keep parents[child] = parent, set when the child is first pushed "
        "with a strictly better g. When you pop the goal, walk the chain "
        "backwards and reverse it.",
    ],
    solution="""
import heapq


def cheapest_path(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    start, goal = tuple(start), tuple(goal)
    if grid[start[0]][start[1]] == 0 or grid[goal[0]][goal[1]] == 0:
        return None

    step = min(v for row in grid for v in row if v != 0)

    def h(cell):
        return step * (abs(cell[0] - goal[0]) + abs(cell[1] - goal[1]))

    best = {start: 0}
    parents = {start: None}
    counter = 0
    queue = [(h(start), counter, start)]
    seen = set()

    while queue:
        _, _, node = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == goal:
            path = []
            cur = node
            while cur is not None:
                path.append(cur)
                cur = parents[cur]
            path.reverse()
            return path
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = node[0] + dr, node[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols) or grid[nr][nc] == 0:
                continue
            child = (nr, nc)
            if child in seen:
                continue
            candidate = best[node] + grid[nr][nc]
            if candidate < best.get(child, float("inf")):
                best[child] = candidate
                parents[child] = node
                counter += 1
                heapq.heappush(queue, (candidate + h(child), counter, child))
    return None
""",
    tests=[
        T("paths are legal, connected and correctly ended", """
def check(grid, start, goal, path):
    assert path[0] == tuple(start), path
    assert path[-1] == tuple(goal), path
    for (r, c) in path:
        assert grid[r][c] != 0, ("walks through a wall", path)
    for a, b in zip(path, path[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, ("not adjacent", a, b)
    return sum(grid[r][c] for (r, c) in path[1:])


flat = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
assert check(flat, (0, 0), (2, 2), cheapest_path(flat, (0, 0), (2, 2))) == 4
pricey = [[1, 9, 1], [1, 9, 1], [1, 1, 1]]
assert check(pricey, (0, 0), (0, 2), cheapest_path(pricey, (0, 0), (0, 2))) == 6
"""),
        T("degenerate and impossible cases", """
assert cheapest_path([[1, 1], [1, 1]], (0, 0), (0, 0)) == [(0, 0)]
assert cheapest_path([[1, 0, 1]], (0, 0), (0, 2)) is None
grid = [[1, 1, 1], [1, 0, 1], [1, 1, 1]]
assert cheapest_path(grid, (1, 1), (0, 0)) is None
assert cheapest_path(grid, (0, 0), (1, 1)) is None
"""),
        T("terrain and maze maps hit the oracle cost", """
def total(grid, path):
    return sum(grid[r][c] for (r, c) in path[1:])


TERRAIN = @@TERRAIN@@
MAZE = @@MAZE@@
p = cheapest_path(TERRAIN, (0, 0), (6, 6))
assert total(TERRAIN, p) == @@CORNER@@, total(TERRAIN, p)
p = cheapest_path(TERRAIN, (0, 0), (2, 4))
assert total(TERRAIN, p) == @@MID@@
assert cheapest_path(TERRAIN, (0, 0), (4, 3)) is None
p = cheapest_path(MAZE, (0, 0), (4, 4))
assert total(MAZE, p) == @@MAZECORNER@@
assert cheapest_path(MAZE, (0, 0), (3, 0)) is None
""", TERRAIN=TERRAIN, MAZE=MAZE, CORNER=TERRAIN_CORNER, MID=TERRAIN_MID,
             MAZECORNER=MAZE_CORNER),
        T("random grids: legal and provably optimal", """
import heapq
import random
random.seed(31)


def oracle(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == 0 or grid[goal[0]][goal[1]] == 0:
        return None
    dist = {start: 0}
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            return d
        if d > dist.get(u, float("inf")):
            continue
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = u[0] + dr, u[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] != 0:
                nd = d + grid[nr][nc]
                if nd < dist.get((nr, nc), float("inf")):
                    dist[(nr, nc)] = nd
                    heapq.heappush(pq, (nd, (nr, nc)))
    return None


for trial in range(150):
    rows = random.randint(1, 6)
    cols = random.randint(1, 6)
    grid = [[random.choice([0, 1, 1, 3, 7]) for _ in range(cols)]
            for _ in range(rows)]
    start = (random.randrange(rows), random.randrange(cols))
    goal = (random.randrange(rows), random.randrange(cols))
    want = oracle(grid, start, goal)
    got = cheapest_path(grid, start, goal)
    if want is None:
        assert got is None, (grid, start, goal, got)
        continue
    assert got is not None, (grid, start, goal)
    assert got[0] == start and got[-1] == goal
    for a, b in zip(got, got[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
    for (r, c) in got:
        assert grid[r][c] != 0
    assert sum(grid[r][c] for (r, c) in got[1:]) == want, (grid, start, goal)
"""),
    ],
)


problem(
    id="knight-shortest-path",
    track="A* Solvers",
    title="Knight Across a Damaged Board",
    difficulty="medium",
    points=20,
    blurb="Chess-knight distance with squares removed, and a heuristic that survives the holes.",
    statement="""
<p>A knight sits on an <code>n</code> &times; <code>n</code> board and moves in
the usual L: two squares one way, one square the other, eight options in all.
Some squares are damaged and cannot be landed on. A knight may jump
<em>over</em> a damaged square &mdash; only the landing square matters.</p>

<p>Write <code>knight_distance(n, start, goal, blocked)</code>, returning the
fewest moves needed, or <code>None</code> if the goal cannot be reached or
either endpoint is damaged. <code>blocked</code> is a list of
<code>(row, col)</code> tuples.</p>

<p>Every move costs 1, so an admissible heuristic must never claim more moves
than are really needed. With <code>dr</code> and <code>dc</code> the row and
column gaps, a safe estimate is</p>

<pre>max(ceil(dr / 2), ceil(dc / 2), ceil((dr + dc) / 3))</pre>

<p>No single knight move closes more than 2 in either axis, nor more than 3
across both combined &mdash; which is exactly why each of those three terms is
a lower bound. Damaged squares only ever make the true distance larger, so
the estimate stays admissible however the board is chewed up.</p>
""",
    examples="""
>>> knight_distance(8, (0, 0), (0, 0), [])
0
>>> knight_distance(8, (0, 0), (1, 2), [])
1
>>> knight_distance(8, (0, 0), (1, 1), [])
4
>>> print(knight_distance(3, (0, 0), (1, 1), []))
None
""",
    starter="""
def knight_distance(n, start, goal, blocked):
    pass
""",
    hints=[
        "Turn blocked into a set of tuples first. Membership tests run at "
        "every generated move, and scanning a list each time is what makes a "
        "search like this crawl.",
        "The eight offsets are the pairs (+-1, +-2) and (+-2, +-1). Generate "
        "them once outside the loop.",
        "Because every move costs 1, plain BFS already returns the optimum "
        "here -- A* with the heuristic above simply gets there having "
        "expanded fewer squares. Either earns the points, but do the goal "
        "test when you dequeue.",
    ],
    solution="""
import heapq
from math import ceil


def knight_distance(n, start, goal, blocked):
    start, goal = tuple(start), tuple(goal)
    walls = set(map(tuple, blocked))
    if start in walls or goal in walls:
        return None
    if not (0 <= start[0] < n and 0 <= start[1] < n):
        return None
    if not (0 <= goal[0] < n and 0 <= goal[1] < n):
        return None

    jumps = ((1, 2), (2, 1), (-1, 2), (-2, 1),
             (1, -2), (2, -1), (-1, -2), (-2, -1))

    def h(cell):
        dr = abs(cell[0] - goal[0])
        dc = abs(cell[1] - goal[1])
        return max(ceil(dr / 2), ceil(dc / 2), ceil((dr + dc) / 3))

    best = {start: 0}
    counter = 0
    queue = [(h(start), counter, start)]
    seen = set()
    while queue:
        _, _, node = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == goal:
            return best[node]
        for dr, dc in jumps:
            nr, nc = node[0] + dr, node[1] + dc
            child = (nr, nc)
            if not (0 <= nr < n and 0 <= nc < n) or child in walls:
                continue
            candidate = best[node] + 1
            if candidate < best.get(child, float("inf")):
                best[child] = candidate
                counter += 1
                heapq.heappush(queue, (candidate + h(child), counter, child))
    return None
""",
    tests=[
        T("the worked examples", """
assert knight_distance(8, (0, 0), (0, 0), []) == 0
assert knight_distance(8, (0, 0), (1, 2), []) == 1
assert knight_distance(8, (0, 0), (1, 1), []) == 4
assert knight_distance(3, (0, 0), (1, 1), []) is None
"""),
        T("open-board distances", """
assert knight_distance(8, (0, 0), (7, 7), []) == @@OPEN@@
assert knight_distance(8, (0, 0), (1, 1), []) == @@CORNER@@
assert knight_distance(8, (3, 3), (3, 3), []) == 0
assert knight_distance(8, (0, 0), (2, 1), []) == 1
""", OPEN=KNIGHT_OPEN, CORNER=KNIGHT_CORNER),
        T("damaged squares", """
assert knight_distance(5, (0, 0), (4, 4),
                       [(1, 2), (2, 1), (2, 3), (3, 2)]) == @@WALLED@@
# Endpoints on damage are rejected outright.
assert knight_distance(8, (0, 0), (4, 4), [(0, 0)]) is None
assert knight_distance(8, (0, 0), (4, 4), [(4, 4)]) is None
# Sealing off every square the knight could first reach traps it.
assert knight_distance(8, (0, 0), (7, 7), [(1, 2), (2, 1)]) is None
""", WALLED=KNIGHT_WALLED),
        T("agrees with breadth-first search everywhere", """
from collections import deque
import random
random.seed(41)

JUMPS = ((1, 2), (2, 1), (-1, 2), (-2, 1),
         (1, -2), (2, -1), (-1, -2), (-2, -1))


def bfs(n, start, goal, blocked):
    walls = set(map(tuple, blocked))
    if tuple(start) in walls or tuple(goal) in walls:
        return None
    seen = {tuple(start)}
    q = deque([(tuple(start), 0)])
    while q:
        (r, c), d = q.popleft()
        if (r, c) == tuple(goal):
            return d
        for dr, dc in JUMPS:
            nr, nc = r + dr, c + dc
            if (0 <= nr < n and 0 <= nc < n
                    and (nr, nc) not in walls and (nr, nc) not in seen):
                seen.add((nr, nc))
                q.append(((nr, nc), d + 1))
    return None


for trial in range(120):
    n = random.randint(3, 7)
    cells = [(r, c) for r in range(n) for c in range(n)]
    blocked = random.sample(cells, k=random.randint(0, n))
    start = random.choice(cells)
    goal = random.choice(cells)
    assert knight_distance(n, start, goal, blocked) == bfs(n, start, goal, blocked), \\
        (n, start, goal, blocked)
"""),
        T("the suggested heuristic really is admissible", """
from collections import deque
from math import ceil

JUMPS = ((1, 2), (2, 1), (-1, 2), (-2, 1),
         (1, -2), (2, -1), (-1, -2), (-2, -1))
n = 8
goal = (5, 4)
dist = {goal: 0}
q = deque([goal])
while q:
    r, c = q.popleft()
    for dr, dc in JUMPS:
        nr, nc = r + dr, c + dc
        if 0 <= nr < n and 0 <= nc < n and (nr, nc) not in dist:
            dist[(nr, nc)] = dist[(r, c)] + 1
            q.append((nr, nc))

for (r, c), true_cost in dist.items():
    dr, dc = abs(r - goal[0]), abs(c - goal[1])
    h = max(ceil(dr / 2), ceil(dc / 2), ceil((dr + dc) / 3))
    assert h <= true_cost, ((r, c), h, true_cost)
    assert knight_distance(n, (r, c), goal, []) == true_cost
"""),
    ],
)


def _pancake_min(stack):
    """Fewest prefix reversals that sort `stack` ascending."""
    start = tuple(stack)
    goal = tuple(sorted(start))
    if start == goal:
        return 0
    seen = {start}
    frontier = deque([(start, 0)])
    while frontier:
        state, depth = frontier.popleft()
        for k in range(2, len(state) + 1):
            nxt = state[:k][::-1] + state[k:]
            if nxt == goal:
                return depth + 1
            if nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, depth + 1))
    return None


PANCAKE_A = _pancake_min([3, 1, 2])
PANCAKE_B = _pancake_min([4, 3, 2, 1])
PANCAKE_C = _pancake_min([2, 5, 3, 1, 4])
PANCAKE_D = _pancake_min([6, 2, 4, 1, 5, 3])


def _lock_moves(state):
    for i in range(len(state)):
        for delta in (1, -1):
            digit = (int(state[i]) + delta) % 10
            yield (i, delta), state[:i] + str(digit) + state[i + 1:]


def _lock_all_optimal(start, target, deadends):
    dead = set(deadends)
    if start in dead or target in dead:
        return []
    if start == target:
        return [[]]
    layer = {start: [[]]}
    seen = {start}
    while layer:
        nxt_layer = {}
        for state, routes in layer.items():
            for move, other in _lock_moves(state):
                if other in dead or other in seen:
                    continue
                nxt_layer.setdefault(other, [])
                for route in routes:
                    nxt_layer[other].append(route + [move])
        if target in nxt_layer:
            return nxt_layer[target]
        seen.update(nxt_layer)
        layer = nxt_layer
    return []


LOCK_A = len(_lock_all_optimal("000", "012", []))
LOCK_B = len(_lock_all_optimal("000", "111", []))
LOCK_C = len(_lock_all_optimal("000", "012", ["010", "001"]))
LOCK_D = _lock_all_optimal("00", "11", [])


def _hanoi_moves(state):
    """Yield (move, next_state) for a tuple where index i is disk i+1's peg."""
    tops = {}
    for disk, peg in enumerate(state):
        tops.setdefault(peg, disk)
    for peg, disk in tops.items():
        for dest in range(3):
            if dest == peg:
                continue
            if dest in tops and tops[dest] < disk:
                continue
            lst = list(state)
            lst[disk] = dest
            yield (peg, dest), tuple(lst)


def _hanoi_min(start, goal):
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return 0
    seen = {start}
    frontier = deque([(start, 0)])
    while frontier:
        state, depth = frontier.popleft()
        for _, nxt in _hanoi_moves(state):
            if nxt == goal:
                return depth + 1
            if nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, depth + 1))
    return None


HANOI_CLASSIC = _hanoi_min((0, 0, 0, 0), (2, 2, 2, 2))
HANOI_SPLIT = _hanoi_min((0, 1, 2, 0), (1, 1, 1, 1))
HANOI_FIVE = _hanoi_min((0, 0, 0, 0, 0), (1, 1, 1, 1, 1))
HANOI_MIXED = _hanoi_min((2, 0, 1, 1), (0, 2, 2, 0))


problem(
    id="pancake-flip",
    track="A* Solvers",
    title="Sorting Pancakes by the Spatula",
    difficulty="hard",
    points=25,
    blurb="Prefix reversals, and the gap heuristic that makes the search tractable.",
    statement="""
<p>A stack of pancakes is a list of distinct sizes, <code>1</code> smallest,
read top to bottom. The only tool is a spatula: slide it under the top
<code>k</code> pancakes and flip that whole prefix over. The goal is
ascending order, smallest on top.</p>

<p>Write <code>pancake_sort(stack)</code>, returning a list of prefix lengths
&mdash; each between <code>2</code> and <code>len(stack)</code> &mdash; that
sorts the stack in the <strong>fewest possible flips</strong>. Any minimal
answer is accepted. An already-sorted stack returns <code>[]</code>.</p>

<p>The branching factor is only <code>n - 1</code>, but depth grows fast, so
you want a real heuristic. The standard one is the <strong>gap
heuristic</strong>: append a virtual pancake of size <code>n + 1</code> below
the stack, then count adjacent pairs whose sizes differ by more than 1. A
single flip can repair at most one such gap, so the count never overestimates
&mdash; it is admissible.</p>
""",
    examples="""
>>> pancake_sort([1, 2, 3])
[]
>>> pancake_sort([2, 1])
[2]
>>> pancake_sort([3, 1, 2])
[3, 2]
>>> len(pancake_sort([4, 3, 2, 1]))
1
""",
    starter="""
def pancake_sort(stack):
    pass
""",
    hints=[
        "A flip of length k maps state to state[:k][::-1] + state[k:]. "
        "Tuples make good states: hashable, so they drop straight into a "
        "visited set.",
        "Gap count: walk the sequence tuple(stack) + (n + 1,) and count "
        "positions where abs(a[i] - a[i+1]) != 1. That is your h.",
        "Store parents rather than whole flip lists in the queue, then walk "
        "the chain back from the goal. And keep the usual counter in the "
        "heap tuple so two states with equal f never get compared.",
    ],
    solution="""
import heapq


def _gaps(state):
    n = len(state)
    extended = tuple(state) + (n + 1,)
    return sum(1 for i in range(n)
               if abs(extended[i] - extended[i + 1]) != 1)


def pancake_sort(stack):
    start = tuple(stack)
    goal = tuple(sorted(start))
    if start == goal:
        return []

    n = len(start)
    best = {start: 0}
    parents = {start: None}
    counter = 0
    queue = [(_gaps(start), counter, start)]
    seen = set()

    while queue:
        _, _, state = heapq.heappop(queue)
        if state in seen:
            continue
        seen.add(state)
        if state == goal:
            flips = []
            cur = state
            while parents[cur] is not None:
                prev, k = parents[cur]
                flips.append(k)
                cur = prev
            flips.reverse()
            return flips
        for k in range(2, n + 1):
            child = state[:k][::-1] + state[k:]
            if child in seen:
                continue
            candidate = best[state] + 1
            if candidate < best.get(child, float("inf")):
                best[child] = candidate
                parents[child] = (state, k)
                counter += 1
                heapq.heappush(
                    queue, (candidate + _gaps(child), counter, child))
    return None
""",
    tests=[
        T("worked examples and the trivial case", """
def replay(stack, flips):
    cur = list(stack)
    for k in flips:
        assert 2 <= k <= len(cur), ("illegal flip length", k)
        cur[:k] = cur[:k][::-1]
    return cur


assert pancake_sort([1, 2, 3]) == []
assert pancake_sort([1]) == []
assert pancake_sort([]) == []
assert replay([2, 1], pancake_sort([2, 1])) == [1, 2]
assert len(pancake_sort([2, 1])) == 1
assert replay([3, 1, 2], pancake_sort([3, 1, 2])) == [1, 2, 3]
assert len(pancake_sort([3, 1, 2])) == @@A@@
""", A=PANCAKE_A),
        T("a fully reversed stack takes a single flip", """
def replay(stack, flips):
    cur = list(stack)
    for k in flips:
        cur[:k] = cur[:k][::-1]
    return cur


flips = pancake_sort([4, 3, 2, 1])
assert replay([4, 3, 2, 1], flips) == [1, 2, 3, 4]
assert len(flips) == @@B@@ == 1
""", B=PANCAKE_B),
        T("larger stacks reach the oracle's optimum", """
def replay(stack, flips):
    cur = list(stack)
    for k in flips:
        assert 2 <= k <= len(cur)
        cur[:k] = cur[:k][::-1]
    return cur


for stack, want in (([2, 5, 3, 1, 4], @@C@@), ([6, 2, 4, 1, 5, 3], @@D@@)):
    flips = pancake_sort(stack)
    assert replay(stack, flips) == sorted(stack), (stack, flips)
    assert len(flips) == want, (stack, len(flips), want)
""", C=PANCAKE_C, D=PANCAKE_D),
        T("every permutation of five, against breadth-first search", """
from collections import deque
from itertools import permutations


def oracle(stack):
    start = tuple(stack)
    goal = tuple(sorted(start))
    if start == goal:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        state, d = q.popleft()
        for k in range(2, len(state) + 1):
            nxt = state[:k][::-1] + state[k:]
            if nxt == goal:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None


for perm in permutations(range(1, 6)):
    flips = pancake_sort(list(perm))
    cur = list(perm)
    for k in flips:
        assert 2 <= k <= 5, ("illegal flip length", k)
        cur[:k] = cur[:k][::-1]
    assert cur == sorted(perm), (perm, flips)
    assert len(flips) == oracle(perm), (perm, len(flips), oracle(perm))
"""),
        T("the gap heuristic never overestimates", """
from collections import deque
from itertools import permutations


def gaps(state):
    n = len(state)
    ext = tuple(state) + (n + 1,)
    return sum(1 for i in range(n) if abs(ext[i] - ext[i + 1]) != 1)


goal = (1, 2, 3, 4, 5)
dist = {goal: 0}
q = deque([goal])
while q:
    state = q.popleft()
    for k in range(2, 6):
        nxt = state[:k][::-1] + state[k:]
        if nxt not in dist:
            dist[nxt] = dist[state] + 1
            q.append(nxt)

assert len(dist) == 120
for state, true_cost in dist.items():
    assert gaps(state) <= true_cost, (state, gaps(state), true_cost)
"""),
    ],
)


# --------------------------------------------------------------------------
# Track 4 -- iterative deepening
# --------------------------------------------------------------------------

problem(
    id="lock-all-optimal",
    track="Iterative Deepening",
    title="Every Shortest Way to Open the Lock",
    difficulty="medium",
    points=20,
    blurb="Iterative deepening that collects all optimal solutions, not just the first one found.",
    statement="""
<p>A combination lock has several wheels, each showing a digit
<code>0</code>&ndash;<code>9</code> and wrapping around, so
<code>9 + 1 = 0</code> and <code>0 - 1 = 9</code>. One move turns exactly one
wheel by one click. Some codes are jammed and the lock seizes if you ever
land on one.</p>

<p>States are strings such as <code>"000"</code>. A move is a tuple
<code>(index, delta)</code> where <code>delta</code> is <code>1</code> or
<code>-1</code>.</p>

<p>Write <code>all_shortest_unlocks(start, target, deadends)</code>, returning
a list of <strong>every</strong> shortest move sequence from
<code>start</code> to <code>target</code>. Order among the sequences does not
matter. Return <code>[]</code> when the target is unreachable or when either
endpoint is jammed; return <code>[[]]</code> when start and target are already
equal, since the empty sequence is the one optimal answer.</p>

<p>Use iterative deepening: run a depth-limited search at depth 0, then 1,
then 2, and stop at the first depth that yields anything &mdash; collecting
everything found at that depth. Stopping there is what makes the answers
optimal; carrying on to the next depth would sweep up longer solutions too.</p>
""",
    examples="""
>>> all_shortest_unlocks("000", "000", [])
[[]]
>>> all_shortest_unlocks("000", "001", [])
[[(2, 1)]]
>>> sorted(map(tuple, all_shortest_unlocks("00", "11", [])))
[((0, 1), (1, 1)), ((1, 1), (0, 1))]
>>> all_shortest_unlocks("000", "111", ["000"])
[]
""",
    starter="""
def all_shortest_unlocks(start, target, deadends):
    pass
""",
    hints=[
        "Write a recursive helper taking (state, limit, moves). When "
        "len(moves) == limit, check whether state is the target and record a "
        "copy of moves if so; otherwise recurse on each legal successor.",
        "Do not carry a visited set across depths -- a state reachable in "
        "four moves along one route may be on a different optimal route, and "
        "pruning it would lose solutions. Depth alone bounds the work.",
        "The outer loop resets the results list at each new limit, runs the "
        "helper, and returns as soon as the list is non-empty. Guard the "
        "endpoints against deadends before you start.",
    ],
    solution="""
def all_shortest_unlocks(start, target, deadends):
    dead = set(deadends)
    if start in dead or target in dead:
        return []

    def successors(state):
        for i in range(len(state)):
            for delta in (1, -1):
                digit = (int(state[i]) + delta) % 10
                nxt = state[:i] + str(digit) + state[i + 1:]
                if nxt not in dead:
                    yield (i, delta), nxt

    def walk(state, limit, moves):
        if len(moves) == limit:
            if state == target:
                found.append(list(moves))
            return
        for move, nxt in successors(state):
            moves.append(move)
            walk(nxt, limit, moves)
            moves.pop()

    limit = 0
    ceiling = 5 * len(start) + 1
    while limit <= ceiling:
        found = []
        walk(start, limit, [])
        if found:
            return found
        limit += 1
    return []
""",
    tests=[
        T("trivial and impossible cases", """
assert all_shortest_unlocks("000", "000", []) == [[]]
assert all_shortest_unlocks("000", "111", ["000"]) == []
assert all_shortest_unlocks("000", "111", ["111"]) == []
assert all_shortest_unlocks("00", "00", []) == [[]]
"""),
        T("single clicks, including the wrap-around", """
assert all_shortest_unlocks("000", "001", []) == [[(2, 1)]]
assert all_shortest_unlocks("000", "009", []) == [[(2, -1)]]
assert all_shortest_unlocks("090", "000", []) == [[(1, 1)]]
assert all_shortest_unlocks("900", "000", []) == [[(0, 1)]]
"""),
        T("all orderings of independent clicks are returned", """
got = sorted(map(tuple, all_shortest_unlocks("00", "11", [])))
assert got == @@D@@, got
assert len(all_shortest_unlocks("000", "012", [])) == @@A@@
assert len(all_shortest_unlocks("000", "111", [])) == @@B@@
""", D=sorted(map(tuple, LOCK_D)), A=LOCK_A, B=LOCK_B),
        T("jammed codes prune routes without losing optimal ones", """
routes = all_shortest_unlocks("000", "012", ["010", "001"])
assert len(routes) == @@C@@, len(routes)
for route in routes:
    state = "000"
    for (i, delta) in route:
        digit = (int(state[i]) + delta) % 10
        state = state[:i] + str(digit) + state[i + 1:]
        assert state not in ("010", "001"), ("route runs through a deadend", route)
    assert state == "012", (route, state)
""", C=LOCK_C),
        T("results replay correctly and share one optimal length", """
from collections import deque
import random
random.seed(29)


def bfs_len(start, target, dead):
    dead = set(dead)
    if start in dead or target in dead:
        return None
    if start == target:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        state, d = q.popleft()
        for i in range(len(state)):
            for delta in (1, -1):
                digit = (int(state[i]) + delta) % 10
                nxt = state[:i] + str(digit) + state[i + 1:]
                if nxt in dead or nxt in seen:
                    continue
                if nxt == target:
                    return d + 1
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None


for trial in range(40):
    start = "".join(random.choice("012") for _ in range(2))
    target = "".join(random.choice("012") for _ in range(2))
    dead = [s for s in ("11", "21", "12") if random.random() < 0.4]
    routes = all_shortest_unlocks(start, target, dead)
    want = bfs_len(start, target, dead)
    if want is None:
        assert routes == [], (start, target, dead, routes)
        continue
    assert routes, (start, target, dead)
    assert len({len(r) for r in routes}) == 1
    assert len(routes[0]) == want, (start, target, dead, len(routes[0]), want)
    seqs = set()
    for route in routes:
        state = start
        for (i, delta) in route:
            digit = (int(state[i]) + delta) % 10
            state = state[:i] + str(digit) + state[i + 1:]
            assert state not in dead
        assert state == target, (start, target, route)
        seqs.add(tuple(route))
    assert len(seqs) == len(routes), "duplicate sequences returned"
"""),
    ],
)


problem(
    id="hanoi-anywhere",
    track="Iterative Deepening",
    title="Hanoi Between Two Arbitrary Piles",
    difficulty="hard",
    points=25,
    blurb="Not the textbook tower: any starting arrangement, any target, shortest route.",
    statement="""
<p>Three pegs, <code>n</code> disks of distinct sizes. A configuration is a
tuple where entry <code>i</code> gives the peg holding disk <code>i + 1</code>,
so disk 1 is the smallest and <code>(0, 0, 0)</code> means all three disks are
stacked on peg 0. On each peg the disks are necessarily ordered largest at the
bottom, so the configuration alone describes the state completely.</p>

<p>One move takes the <strong>top</strong> disk off a peg &mdash; the smallest
disk currently on it &mdash; and drops it on another peg, but only if that peg
is empty or its top disk is larger.</p>

<p>Write <code>hanoi_solve(start, goal)</code>, returning a shortest list of
<code>(from_peg, to_peg)</code> moves. Any minimal answer is accepted, and an
already-solved configuration returns <code>[]</code>. Every configuration is
reachable from every other, so you never need to report failure.</p>

<p>The classic <code>2**n - 1</code> formula only covers one full pile moving
to another. Arbitrary endpoints need a real search. A useful admissible
heuristic is the count of disks not already on their target peg &mdash; each
such disk has to move at least once.</p>
""",
    examples="""
>>> hanoi_solve((0, 0), (0, 0))
[]
>>> hanoi_solve((0,), (2,))
[(0, 2)]
>>> len(hanoi_solve((0, 0, 0), (2, 2, 2)))
7
>>> len(hanoi_solve((0, 1, 2), (1, 1, 1)))
7
""",
    starter="""
def hanoi_solve(start, goal):
    pass
""",
    hints=[
        "To find each peg's top disk, scan the configuration once and keep "
        "the FIRST disk index seen for each peg -- smaller index means "
        "smaller disk, which is the one on top.",
        "A move from peg p to peg d is legal when d holds no disk at all, or "
        "when d's top disk index is greater than the disk you are lifting.",
        "The number of disks sitting on the wrong peg is admissible, since "
        "each of them needs at least one move. It is weak but sound, and it "
        "still beats searching blind.",
    ],
    solution="""
import heapq


def _tops(state):
    tops = {}
    for disk, peg in enumerate(state):
        if peg not in tops:
            tops[peg] = disk
    return tops


def _moves(state):
    tops = _tops(state)
    for peg, disk in tops.items():
        for dest in range(3):
            if dest == peg:
                continue
            if dest in tops and tops[dest] < disk:
                continue
            lst = list(state)
            lst[disk] = dest
            yield (peg, dest), tuple(lst)


def hanoi_solve(start, goal):
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return []

    def h(state):
        return sum(1 for a, b in zip(state, goal) if a != b)

    best = {start: 0}
    parents = {start: None}
    counter = 0
    queue = [(h(start), counter, start)]
    seen = set()

    while queue:
        _, _, state = heapq.heappop(queue)
        if state in seen:
            continue
        seen.add(state)
        if state == goal:
            moves = []
            cur = state
            while parents[cur] is not None:
                prev, move = parents[cur]
                moves.append(move)
                cur = prev
            moves.reverse()
            return moves
        for move, child in _moves(state):
            if child in seen:
                continue
            candidate = best[state] + 1
            if candidate < best.get(child, float("inf")):
                best[child] = candidate
                parents[child] = (state, move)
                counter += 1
                heapq.heappush(queue, (candidate + h(child), counter, child))
    return None
""",
    tests=[
        T("trivial cases and single disks", """
assert hanoi_solve((0, 0), (0, 0)) == []
assert hanoi_solve((0,), (0,)) == []
assert hanoi_solve((0,), (2,)) == [(0, 2)]
assert hanoi_solve((1,), (0,)) == [(1, 0)]
"""),
        T("the classic tower matches 2**n - 1", """
def replay(start, moves):
    state = list(start)
    for (src, dst) in moves:
        tops = {}
        for disk, peg in enumerate(state):
            if peg not in tops:
                tops[peg] = disk
        assert src in tops, ("no disk on the source peg", src, state)
        disk = tops[src]
        assert src != dst, "move to the same peg"
        assert dst not in tops or tops[dst] > disk, ("onto a smaller disk", state)
        state[disk] = dst
    return tuple(state)


for n in (1, 2, 3, 4):
    start = tuple([0] * n)
    goal = tuple([2] * n)
    moves = hanoi_solve(start, goal)
    assert replay(start, moves) == goal, (n, moves)
    assert len(moves) == 2 ** n - 1, (n, len(moves))
assert len(hanoi_solve((0, 0, 0, 0), (2, 2, 2, 2))) == @@CLASSIC@@
assert len(hanoi_solve((0, 0, 0, 0, 0), (1, 1, 1, 1, 1))) == @@FIVE@@
""", CLASSIC=HANOI_CLASSIC, FIVE=HANOI_FIVE),
        T("arbitrary endpoints hit the oracle length", """
def replay(start, moves):
    state = list(start)
    for (src, dst) in moves:
        tops = {}
        for disk, peg in enumerate(state):
            if peg not in tops:
                tops[peg] = disk
        assert src in tops and src != dst
        disk = tops[src]
        assert dst not in tops or tops[dst] > disk
        state[disk] = dst
    return tuple(state)


for start, goal, want in (((0, 1, 2, 0), (1, 1, 1, 1), @@SPLIT@@),
                          ((2, 0, 1, 1), (0, 2, 2, 0), @@MIXED@@)):
    moves = hanoi_solve(start, goal)
    assert replay(start, moves) == goal, (start, goal, moves)
    assert len(moves) == want, (start, goal, len(moves), want)
""", SPLIT=HANOI_SPLIT, MIXED=HANOI_MIXED),
        T("every three-disk pair, against breadth-first search", """
from collections import deque
from itertools import product


def tops_of(state):
    tops = {}
    for disk, peg in enumerate(state):
        if peg not in tops:
            tops[peg] = disk
    return tops


def succ(state):
    tops = tops_of(state)
    for peg, disk in tops.items():
        for dest in range(3):
            if dest == peg or (dest in tops and tops[dest] < disk):
                continue
            lst = list(state)
            lst[disk] = dest
            yield (peg, dest), tuple(lst)


def bfs_len(start, goal):
    if start == goal:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        state, d = q.popleft()
        for _, nxt in succ(state):
            if nxt == goal:
                return d + 1
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, d + 1))
    return None


states = list(product(range(3), repeat=3))
for start in states:
    for goal in states:
        moves = hanoi_solve(start, goal)
        state = list(start)
        for (src, dst) in moves:
            tops = tops_of(tuple(state))
            assert src in tops and src != dst, (start, goal, moves)
            disk = tops[src]
            assert dst not in tops or tops[dst] > disk, (start, goal, moves)
            state[disk] = dst
        assert tuple(state) == goal, (start, goal, moves)
        assert len(moves) == bfs_len(start, goal), (start, goal, len(moves))
"""),
        T("the wrong-peg count is admissible", """
from collections import deque
from itertools import product


def tops_of(state):
    tops = {}
    for disk, peg in enumerate(state):
        if peg not in tops:
            tops[peg] = disk
    return tops


def succ(state):
    tops = tops_of(state)
    for peg, disk in tops.items():
        for dest in range(3):
            if dest == peg or (dest in tops and tops[dest] < disk):
                continue
            lst = list(state)
            lst[disk] = dest
            yield tuple(lst)


goal = (1, 1, 1, 1)
dist = {goal: 0}
q = deque([goal])
while q:
    cur = q.popleft()
    for nxt in succ(cur):
        if nxt not in dist:
            dist[nxt] = dist[cur] + 1
            q.append(nxt)

assert len(dist) == 81
for state, true_cost in dist.items():
    h = sum(1 for a, b in zip(state, goal) if a != b)
    assert h <= true_cost, (state, h, true_cost)
"""),
    ],
)


def _tile_all_optimal(board):
    """Every optimal solution to a sliding puzzle, as lists of direction names."""
    offsets = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
    order = ["up", "down", "left", "right"]
    rows, cols = len(board), len(board[0])
    start = tuple(v for row in board for v in row)
    goal = tuple(range(1, rows * cols)) + (0,)
    if start == goal:
        return [[]]

    def successors(state):
        i = state.index(0)
        r, c = divmod(i, cols)
        for name in order:
            dr, dc = offsets[name]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                j = nr * cols + nc
                lst = list(state)
                lst[i], lst[j] = lst[j], lst[i]
                yield name, tuple(lst)

    layer = {start: [[]]}
    seen = {start}
    while layer:
        nxt = {}
        for state, routes in layer.items():
            for name, other in successors(state):
                if other in seen:
                    continue
                nxt.setdefault(other, [])
                for route in routes:
                    nxt[other].append(route + [name])
        if goal in nxt:
            return nxt[goal]
        seen.update(nxt)
        layer = nxt
    return []


TILE_A = _tile_all_optimal([[4, 1, 2], [0, 5, 3], [7, 8, 6]])
TILE_B = _tile_all_optimal([[1, 2, 3], [4, 0, 8], [7, 6, 5]])
TILE_C = _tile_all_optimal([[4, 1, 2], [5, 0, 3]])

TILE_CLASS = '''
class TilePuzzle(object):

    def __init__(self, board):
        self.board = board

    def get_board(self):
        return self.board

    def perform_move(self, direction):
        offsets = {"up": (-1, 0), "down": (1, 0),
                   "left": (0, -1), "right": (0, 1)}
        if direction not in offsets:
            return False
        rows, cols = len(self.board), len(self.board[0])
        dr, dc = offsets[direction]
        for row in range(rows):
            for col in range(cols):
                if self.board[row][col] == 0:
                    r, c = row + dr, col + dc
                    if 0 <= r < rows and 0 <= c < cols:
                        self.board[row][col], self.board[r][c] = (
                            self.board[r][c], self.board[row][col])
                        return True
                    return False
        return False

    def is_solved(self):
        flat = [x for row in self.board for x in row]
        return flat == list(range(1, len(flat))) + [0]

    def copy(self):
        return TilePuzzle([row.copy() for row in self.board])

    def successors(self):
        for move in ["up", "down", "left", "right"]:
            board_copy = self.copy()
            if board_copy.perform_move(move):
                yield (move, board_copy)
'''


problem(
    id="tile-all-optimal",
    track="Iterative Deepening",
    title="Every Optimal Way to Solve the Tiles",
    difficulty="hard",
    points=25,
    blurb="The homework's IDDFS solver, restated: yield all optimal solutions, not just one.",
    statement="""
<p>This one is deliberately the Homework 3 problem rather than a variation of
it &mdash; worth a second pass from a blank editor, because two of its traps
cost real time the first time round.</p>

<p>The puzzle is a rectangular board of tiles <code>1</code> to
<code>r*c - 1</code> with <code>0</code> as the empty space. The solved board
has the tiles in row-major order with the space in the lower-right corner. A
move slides the empty space one square, named from the space's point of view:
<code>"up"</code>, <code>"down"</code>, <code>"left"</code>,
<code>"right"</code>.</p>

<p>You write the whole class from an empty skeleton &mdash;
<code>__init__</code>, <code>get_board</code>, <code>perform_move</code>,
<code>is_solved</code>, <code>copy</code> and <code>successors</code>, then
the solver on top of them. The tests exercise every one of those directly, so
a shortcut in the infrastructure surfaces as a failure rather than passing
quietly.</p>

<p><code>find_solutions_iddfs(self)</code> must <strong>yield</strong> every
optimal solution as a list of direction strings. Order among the solutions
does not matter. A solved board yields one solution, the empty list.</p>

<p><code>perform_move</code> returns a Boolean saying whether the move
happened, and <code>successors</code> yields <code>(direction,
new-puzzle)</code> pairs &mdash; only for moves that actually succeed.
<code>copy</code> must be deep enough that changing one board leaves the other
alone.</p>

<p>Use iterative deepening: depth-limited searches at 0 moves, then 1, then 2,
stopping at the first depth that finds anything and yielding everything found
there. You may assume the board is solvable.</p>

<p>Two things to watch, both of which decide whether this finishes at all:</p>

<ul>
  <li>The helper must recurse on the <strong>successor</strong> board. Recurse
      on the same board and the puzzle never changes, so no depth ever
      succeeds and the limit climbs forever.</li>
  <li>Do <strong>not</strong> carry a visited set across depths. A state
      reachable in four moves down one route may sit on a different optimal
      route, and pruning it loses solutions.</li>
</ul>
""",
    examples="""
>>> p = TilePuzzle([[1,2,3], [4,5,6], [7,8,0]])
>>> p.perform_move("up")
True
>>> p.get_board()
[[1, 2, 3], [4, 5, 0], [7, 8, 6]]
>>> p = TilePuzzle([[1,2,3], [4,5,6], [7,8,0]])
>>> p.perform_move("down")
False
>>> for move, new_p in TilePuzzle([[1,2,3], [4,5,6], [7,8,0]]).successors():
...     print(move, new_p.get_board())
up [[1, 2, 3], [4, 5, 0], [7, 8, 6]]
left [[1, 2, 3], [4, 5, 6], [7, 0, 8]]
>>> b = [[4,1,2], [0,5,3], [7,8,6]]
>>> p = TilePuzzle(b)
>>> solutions = p.find_solutions_iddfs()
>>> next(solutions)
['up', 'right', 'right', 'down', 'down']
>>> b = [[1,2,3], [4,0,8], [7,6,5]]
>>> p = TilePuzzle(b)
>>> len(list(p.find_solutions_iddfs()))
2
>>> p = TilePuzzle([[1,2,3], [4,5,6], [7,8,0]])
>>> list(p.find_solutions_iddfs())
[[]]
""",
    starter="""
class TilePuzzle(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def perform_move(self, direction):
        pass

    def is_solved(self):
        pass

    def copy(self):
        pass

    def successors(self):
        pass

    # Required
    def find_solutions_iddfs(self):
        pass
""",
    hints=[
        "Build the infrastructure first and check it against the examples "
        "before touching the solver. successors() must skip moves that fail "
        "-- yielding an unchanged board for an illegal move triples the "
        "search tree and lets no-op moves into your solutions.",
        "Write a recursive helper taking (puzzle, limit, moves). When "
        "len(moves) == limit, check is_solved() and record a copy of moves if "
        "so; otherwise recurse on each successor. Name its first parameter "
        "something other than `self` -- shadowing it is how the recurse-on-"
        "the-same-board bug hides.",
        "The outer loop resets the results list at each new limit, runs the "
        "helper, and stops the moment the list is non-empty. Stopping there "
        "is what makes the answers optimal.",
        "Skipping the move that undoes the previous one is safe -- no optimal "
        "solution ever contains an immediate reversal, since deleting that "
        "pair gives a shorter solution. It cuts the branching factor from "
        "about 2.7 to about 1.7, which is the difference between seconds and "
        "minutes at depth 20.",
    ],
    solution=TILE_CLASS + """
    # Required
    def find_solutions_iddfs(self):

        opposite = {"up": "down", "down": "up",
                    "left": "right", "right": "left"}

        def helper(puzzle, limit, moves):
            if len(moves) == limit:
                if puzzle.is_solved():
                    solutions.append(list(moves))
                return
            for move, mod_board in puzzle.successors():
                if moves and move == opposite[moves[-1]]:
                    continue
                helper(mod_board, limit, moves + [move])

        limit = 0
        while True:
            solutions = []
            helper(self, limit, [])
            if solutions:
                for solution in solutions:
                    yield solution
                return
            limit += 1
""",
    tests=[
        T("the homework's own examples", """
p = TilePuzzle([[4, 1, 2], [0, 5, 3], [7, 8, 6]])
assert next(p.find_solutions_iddfs()) == ['up', 'right', 'right', 'down', 'down']

p = TilePuzzle([[4, 1, 2], [0, 5, 3], [7, 8, 6]])
assert sorted(map(tuple, p.find_solutions_iddfs())) == @@A@@

p = TilePuzzle([[1, 2, 3], [4, 0, 8], [7, 6, 5]])
assert sorted(map(tuple, p.find_solutions_iddfs())) == @@B@@
""", A=sorted(map(tuple, TILE_A)), B=sorted(map(tuple, TILE_B))),
        T("solved and one-move boards", """
p = TilePuzzle([[1, 2, 3], [4, 5, 6], [7, 8, 0]])
assert list(p.find_solutions_iddfs()) == [[]]

p = TilePuzzle([[1, 2], [3, 0]])
assert list(p.find_solutions_iddfs()) == [[]]

p = TilePuzzle([[1, 2, 3], [4, 5, 6], [7, 0, 8]])
assert list(p.find_solutions_iddfs()) == [['right']]

p = TilePuzzle([[1, 2, 0], [4, 5, 3]])
assert list(p.find_solutions_iddfs()) == [['down']]
"""),
        T("it is a generator, not a list", """
p = TilePuzzle([[1, 2, 3], [4, 0, 8], [7, 6, 5]])
gen = p.find_solutions_iddfs()
assert hasattr(gen, "__next__"), "find_solutions_iddfs should yield, not return a list"
first = next(gen)
assert isinstance(first, list) and all(isinstance(m, str) for m in first)
"""),
        T("non-square boards", """
p = TilePuzzle([[4, 1, 2], [5, 0, 3]])
got = sorted(map(tuple, p.find_solutions_iddfs()))
assert got == @@C@@, got
""", C=sorted(map(tuple, TILE_C))),
        T("every solution replays, and they all share one optimal length", """
from collections import deque


def optimal_len(board):
    rows, cols = len(board), len(board[0])
    start = tuple(v for row in board for v in row)
    goal = tuple(range(1, rows * cols)) + (0,)
    if start == goal:
        return 0
    seen = {start}
    q = deque([(start, 0)])
    while q:
        state, d = q.popleft()
        i = state.index(0)
        r, c = divmod(i, cols)
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                j = nr * cols + nc
                lst = list(state)
                lst[i], lst[j] = lst[j], lst[i]
                nxt = tuple(lst)
                if nxt == goal:
                    return d + 1
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, d + 1))
    return None


boards = [[[4, 1, 2], [0, 5, 3], [7, 8, 6]],
          [[1, 2, 3], [4, 0, 8], [7, 6, 5]],
          [[1, 2, 3], [4, 5, 0], [7, 8, 6]],
          [[0, 1, 2], [4, 5, 3]],
          [[4, 1, 2], [5, 0, 3]]]

for board in boards:
    want = optimal_len(board)
    sols = list(TilePuzzle([row[:] for row in board]).find_solutions_iddfs())
    assert sols, board
    assert len({len(s) for s in sols}) == 1, ("mixed lengths", board)
    assert len(sols[0]) == want, (board, len(sols[0]), want)
    seen = set()
    for sol in sols:
        replay = TilePuzzle([row[:] for row in board])
        for move in sol:
            assert replay.perform_move(move), ("illegal move", board, sol)
        assert replay.is_solved(), (board, sol)
        seen.add(tuple(sol))
    assert len(seen) == len(sols), ("duplicate solutions", board)
"""),
        T("ALL optimal solutions are present, checked against a layered BFS", """
from collections import deque

ORDER = ["up", "down", "left", "right"]
OFF = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}


def oracle(board):
    rows, cols = len(board), len(board[0])
    start = tuple(v for row in board for v in row)
    goal = tuple(range(1, rows * cols)) + (0,)
    if start == goal:
        return [[]]

    def succ(state):
        i = state.index(0)
        r, c = divmod(i, cols)
        for name in ORDER:
            dr, dc = OFF[name]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                j = nr * cols + nc
                lst = list(state)
                lst[i], lst[j] = lst[j], lst[i]
                yield name, tuple(lst)

    layer = {start: [[]]}
    seen = {start}
    while layer:
        nxt = {}
        for state, routes in layer.items():
            for name, other in succ(state):
                if other in seen:
                    continue
                nxt.setdefault(other, [])
                for route in routes:
                    nxt[other].append(route + [name])
        if goal in nxt:
            return nxt[goal]
        seen.update(nxt)
        layer = nxt
    return []


boards = [[[4, 1, 2], [0, 5, 3], [7, 8, 6]],
          [[1, 2, 3], [4, 0, 8], [7, 6, 5]],
          [[1, 0, 2], [4, 5, 3]],
          [[4, 1, 2], [5, 0, 3]],
          [[1, 2, 3], [0, 4, 5]]]

for board in boards:
    want = sorted(map(tuple, oracle(board)))
    got = sorted(map(tuple,
                     TilePuzzle([row[:] for row in board]).find_solutions_iddfs()))
    assert got == want, (board, len(got), len(want))
"""),
    ],
)

TRACKS = [
    ("Heuristics",
     "Estimating what is left to do, and proving the estimate is safe."),
    ("A* Machinery",
     "The queue, the cost bookkeeping, and the h = 0 baseline."),
    ("A* Solvers",
     "Best-first search let loose on real state spaces."),
    ("Iterative Deepening",
     "Depth limits, when you want every optimal answer or very little memory."),
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


def check_examples(prob):
    """Run a problem's >>> examples against its reference solution."""
    namespace = {}
    exec(compile(prob["solution"], "<solution>", "exec"), namespace)
    parser = doctest.DocTestParser()
    case = parser.get_doctest(prob["examples"].strip("\n") + "\n",
                              namespace, prob["id"], None, 0)
    runner = doctest.DocTestRunner(verbose=False,
                                   optionflags=doctest.NORMALIZE_WHITESPACE)
    buf = io.StringIO()
    runner.run(case, out=buf.write)
    result = runner.summarize(verbose=False)
    return result.failed, buf.getvalue()


def main():
    import time
    total_tests = 0
    bad = 0
    ids = [p["id"] for p in PROBLEMS]
    assert len(ids) == len(set(ids)), "duplicate problem id"
    for prob in PROBLEMS:
        assert prob["track"] in dict(TRACKS), \
            "%s has unknown track %r" % (prob["id"], prob["track"])
        compile(prob["starter"], "<starter>", "exec")
        started = time.time()
        failures = run_tests(prob["solution"], prob["tests"])
        elapsed = time.time() - started
        total_tests += len(prob["tests"])
        status = "ok  " if not failures else "FAIL"
        print("%s %-22s %2d tests  %5.2fs" %
              (status, prob["id"], len(prob["tests"]), elapsed))
        for name, message in failures:
            bad += 1
            print("       - %s -> %s" % (name, message))
        failed_examples, report = check_examples(prob)
        if failed_examples:
            bad += failed_examples
            print("       - %d bad example(s) in the statement" % failed_examples)
            for line in report.rstrip().splitlines():
                print("         %s" % line)

    print("\n%d problems, %d tests, %d points, %d failures" %
          (len(PROBLEMS), total_tests, sum(p["points"] for p in PROBLEMS), bad))
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
