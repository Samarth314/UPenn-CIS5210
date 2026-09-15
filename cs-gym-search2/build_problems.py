"""Build the CS Gym (Expectimax & Alpha-Beta II) problem bank.

Every problem runs its reference solution against its own tests before
problems.json is written, so a broken problem can never ship. Oracles work
on plain nested-list/tuple tree specs, never on a learner's own Node class.
"""

import doctest
import io
import json
import os
import random

PROBLEMS = []


def problem(**kwargs):
    PROBLEMS.append(kwargs)


def T(name, src, **consts):
    for key, value in consts.items():
        marker = "@@%s@@" % key
        assert marker in src, "unused constant %s in test %r" % (key, name)
        src = src.replace(marker, repr(value))
    assert "@@" not in src, "unresolved constant in test %r" % name
    return {"name": name, "src": src.strip("\n")}


NODE_SRC = '''
class Node(object):

    def __init__(self, value=None, children=None):
        self.value = value
        self.children = children if children is not None else []

    def is_leaf(self):
        return len(self.children) == 0


def build(spec):
    """7 -> a leaf, [a, b] -> a node, (h, [a, b]) -> a node carrying a
    heuristic value h."""
    if isinstance(spec, tuple):
        return Node(spec[0], [build(child) for child in spec[1]])
    if isinstance(spec, list):
        return Node(None, [build(child) for child in spec])
    return Node(spec)
'''.strip("\n")

WNODE_SRC = '''
class WNode(object):
    """A chance node's children each carry an explicit probability."""

    def __init__(self, value=None, children=None, kind="max"):
        self.value = value
        self.children = children if children is not None else []
        self.kind = kind

    def is_leaf(self):
        return len(self.children) == 0


def wbuild(spec):
    """A leaf: a plain number.
    A MAX node: ("max", [child, child, ...]).
    A CHANCE node: ("chance", [(prob, child), (prob, child), ...])."""
    if isinstance(spec, tuple):
        kind, kids = spec
        if kind == "chance":
            children = [(p, wbuild(c)) for p, c in kids]
        else:
            children = [wbuild(c) for c in kids]
        return WNode(None, children, kind)
    return WNode(spec)
'''.strip("\n")

TRACKED_SRC = '''
class Tracked(Node):

    def __init__(self, value, children, path, log):
        self.path = path
        self.log = log
        Node.__init__(self, value, children)

    @property
    def value(self):
        if not self.children:
            self.log.append(self.path)
        return self._value

    @value.setter
    def value(self, value):
        self._value = value


def build_tracked(spec, log, path=()):
    if isinstance(spec, tuple):
        value, kids = spec
    elif isinstance(spec, list):
        value, kids = None, spec
    else:
        value, kids = spec, []
    children = [build_tracked(kid, log, path + (i,))
                for i, kid in enumerate(kids)]
    return Tracked(value, children, path, log)
'''.strip("\n")


def with_nodes(code):
    return NODE_SRC + "\n\n\n" + code.strip("\n") + "\n"


def with_wnodes(code):
    return WNODE_SRC + "\n\n\n" + code.strip("\n") + "\n"


def TN(name, src, tracked=False, **consts):
    head = NODE_SRC + ("\n\n\n" + TRACKED_SRC if tracked else "")
    return T(name, head + "\n\n\n" + src.strip("\n"), **consts)


def TW(name, src, **consts):
    return T(name, WNODE_SRC + "\n\n\n" + src.strip("\n"), **consts)


INF = float("inf")


def kids(spec):
    if isinstance(spec, tuple):
        return spec[1]
    if isinstance(spec, list):
        return spec
    return []


def val(spec):
    if isinstance(spec, tuple):
        return spec[0]
    if isinstance(spec, list):
        return None
    return spec


def at(spec, path):
    for i in path:
        spec = kids(spec)[i]
    return spec


def leaves_of(spec):
    if not kids(spec):
        return [val(spec)]
    return [v for child in kids(spec) for v in leaves_of(child)]


def random_tree(rng, depth, heuristic=False):
    if depth == 0 or (depth < 3 and rng.random() < 0.3):
        return rng.randint(-9, 20)
    children = [random_tree(rng, depth - 1, heuristic)
                for _ in range(rng.randint(1, 3))]
    return (rng.randint(-9, 20), children) if heuristic else children


def draw(spec, kinds=None):
    """kinds: a function(depth) -> label string for interior nodes."""
    def label(node, depth):
        if not kids(node):
            return str(val(node))
        return kinds(depth) if kinds else "*"

    lines = [label(spec, 0)]

    def walk(node, prefix, depth):
        children = kids(node)
        for i, child in enumerate(children):
            last = i == len(children) - 1
            lines.append("%s%s[%d] %s" % (prefix, "└── " if last else "├── ",
                                          i, label(child, depth)))
            walk(child, prefix + ("    " if last else "│   "), depth + 1)

    walk(spec, "", 1)
    return "\n".join(lines)


def picture(spec, kinds=None):
    return '<pre class="block">%s</pre>' % draw(spec, kinds)


# --------------------------------------------------------------------------
# Generic adversarial/expectimax search oracle over any game (board, take-
# away pile, tree -- anything with `children(state, maxing)` and
# `evaluate(state, maxing)`). Shared by every homework-style problem here.
# --------------------------------------------------------------------------

def game_search(root, children, evaluate, limit, bug=None):
    def go(state, alpha, beta, maxing, depth):
        succ = children(state, maxing)
        if depth == 0 or not succ:
            return evaluate(state, maxing), None, 1
        value = -INF if maxing else INF
        move, leaves = None, 0
        for m, child in succ:
            v2, _, l2 = go(child, alpha, beta, not maxing, depth - 1)
            leaves += l2
            if (v2 > value) if maxing else (v2 < value):
                value, move = v2, m
            elif bug == "ties_last" and v2 == value:
                move = m
            if bug != "no_window":
                if maxing:
                    alpha = max(alpha, value)
                else:
                    beta = min(beta, value)
            if bug == "strict_cut":
                cut = (value > beta) if maxing else (value < alpha)
            else:
                cut = (value >= beta) if maxing else (value <= alpha)
            if cut:
                return value, move, leaves
        return value, move, leaves

    value, move, leaves = go(root, -INF, INF, True, limit)
    return move, value, leaves


def expectimax_search(root, children, evaluate, limit, bug=None):
    """MAX alternates with CHANCE (uniform average over `children`).
    `children(state, maxing)` returns [(move_or_None, child), ...]; for a
    chance node the move is irrelevant and ignored."""
    def go(state, maxing, depth):
        succ = children(state, maxing)
        if depth == 0 or not succ:
            return evaluate(state, maxing), None, 1
        if maxing or bug == "always_max":
            value, move, leaves = -INF, None, 0
            for m, child in succ:
                v2, _, l2 = go(child, not maxing, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, m
            return value, move, leaves
        if bug == "used_min":
            value, leaves = INF, 0
            for _, child in succ:
                v2, _, l2 = go(child, not maxing, depth - 1)
                leaves += l2
                value = min(value, v2)
            return value, None, leaves
        total, leaves = 0.0, 0
        for _, child in succ:
            v2, _, l2 = go(child, not maxing, depth - 1)
            leaves += l2
            total += v2
        return total / len(succ), None, leaves

    value, move, leaves = go(root, True, limit)
    return move, value, leaves


# --------------------------------------------------------------------------
# Track 1 -- Expectimax Basics
# --------------------------------------------------------------------------

CHANCE_TREE = [10, 4, 20, 6]
EXP_FIG = [[8, 4], [2, 14]]


def o_average(spec):
    return sum(leaves_of(spec)) / len(leaves_of(spec))


def o_expectimax(spec, maximizing=True):
    if not kids(spec):
        return val(spec)
    values = [o_expectimax(c, not maximizing) for c in kids(spec)]
    if maximizing:
        return max(values)
    return sum(values) / len(values)


problem(
    id="chance-node-average",
    track="Expectimax Basics",
    title="A Chance Node Is Just an Average",
    difficulty="warmup",
    points=5,
    blurb="No adversary, no worst case -- a chance node's value is the plain mean of its children.",
    statement="""
<p>Minimax has two kinds of node: MAX picks the largest child, MIN picks
the smallest. Expectimax replaces the adversarial MIN with a
<strong>CHANCE</strong> node -- one that models an opponent (or an
environment) that doesn't pick against you, it just acts unpredictably.
A CHANCE node's value is the <strong>average</strong> of its children's
values, since with no other information, every outcome is treated as
equally likely.</p>

<p>Write <code>chance_value(node)</code>: the average value of
<code>node</code>'s children. You may assume <code>node</code> always has
at least one child.</p>
""",
    examples="""
>>> chance_value(build([10, 4, 20, 6]))
10.0
>>> chance_value(build([3, 3, 3]))
3.0
>>> chance_value(build([1, 2]))
1.5
""",
    starter=with_nodes("""
def chance_value(node):
    pass
"""),
    hints=[
        "Collect every child's value -- node.children[i].value for a leaf "
        "child -- into a list, or just sum them as you go.",
        "The average of n numbers is their sum divided by n. Use "
        "len(node.children) for n.",
        "return sum(c.value for c in node.children) / len(node.children).",
    ],
    solution=with_nodes("""
def chance_value(node):
    return sum(c.value for c in node.children) / len(node.children)
"""),
    tests=[
        T("evenly split values", "assert chance_value(build([1, 2])) == 1.5"),
        T("all children equal", "assert chance_value(build([3, 3, 3])) == 3.0"),
        T("the example tree", """
got = chance_value(build(@@TREE@@))
assert got == 10.0, got
""", TREE=CHANCE_TREE),
        T("random flat trees, checked against a direct average", """
import random
random.seed(31)
for _ in range(200):
    values = [random.randint(-20, 20) for _ in range(random.randint(1, 8))]
    got = chance_value(build(values))
    want = sum(values) / len(values)
    assert abs(got - want) < 1e-9, (values, got, want)
"""),
    ],
)


problem(
    id="expectimax-value",
    track="Expectimax Basics",
    title="MAX Against an Unpredictable Opponent",
    difficulty="easy",
    points=10,
    blurb="minimax_value with one word changed: CHANCE nodes average instead of minimizing.",
    statement="""
<p>Write <code>expectimax(node, maximizing)</code>: the same alternating
structure as <code>minimax</code> from the first gym, but the non-MAX
levels are CHANCE nodes, not MIN nodes. When <code>maximizing</code> is
<code>True</code>, <code>node</code> is a MAX node and its children are
CHANCE nodes; when <code>False</code>, <code>node</code> is a CHANCE node
(its own value ignored here, same as MIN's structure) and its children
are MAX nodes.</p>
""" + picture(EXP_FIG, lambda d: "MAX" if d % 2 == 0 else "CHANCE") + """
<p>The two CHANCE nodes here average to <code>6.0</code> and
<code>8.0</code>. MAX then picks the larger: <code>8.0</code>. Compare
that to what plain minimax would compute on the identical tree --
minimax's MIN would pick <code>4</code> at the left and <code>2</code> at
the right, giving MAX only <code>4</code> to choose from. Averaging
instead of taking the worst case is what makes expectimax less
pessimistic than minimax against an opponent who isn't actually your
adversary.</p>
""",
    examples="""
>>> expectimax(build([[8, 4], [2, 14]]), True)
8.0
>>> expectimax(build(5), True)
5
>>> expectimax(build(5), False)
5
""",
    starter=with_nodes("""
def expectimax(node, maximizing):
    pass
"""),
    hints=[
        "Base case: a leaf returns node.value, exactly as in minimax.",
        "Recurse on every child with expectimax(child, not maximizing), "
        "same flip as minimax.",
        "If maximizing, return max(...) of those results, same as "
        "minimax. If not, return their average instead of min(...) -- "
        "sum(values) / len(values).",
    ],
    solution=with_nodes("""
def expectimax(node, maximizing):
    if node.is_leaf():
        return node.value
    values = [expectimax(child, not maximizing) for child in node.children]
    if maximizing:
        return max(values)
    return sum(values) / len(values)
"""),
    tests=[
        T("a leaf is its own value either way", """
assert expectimax(build(5), True) == 5
assert expectimax(build(5), False) == 5
"""),
        T("the worked example, both directions", """
tree = build(@@FIG@@)
assert expectimax(tree, True) == 8.0, expectimax(tree, True)
assert expectimax(tree, False) == 11.0, expectimax(tree, False)
""", FIG=EXP_FIG),
        T("differs from plain minimax on the same tree", """
tree = build([[8, 4], [2, 14]])
got = expectimax(tree, True)
if got == 4:
    raise AssertionError(
        "4 is what plain minimax gives here (MIN takes the worst case) -- "
        "a CHANCE node should average, not minimize")
assert got == 8.0, got
"""),
        T("random trees, checked against a direct oracle", """
TREES = @@TREES@@
for spec in TREES:
    tree = build(spec)
    got_max = expectimax(tree, True)
    want_max = @@WANT_MAX@@[TREES.index(spec)]
    assert abs(got_max - want_max) < 1e-9, (spec, got_max, want_max)
""", TREES=[random_tree(random.Random(32), 4) for _ in range(20)],
           WANT_MAX=[o_expectimax(t, True)
                    for t in [random_tree(random.Random(32), 4)
                              for _ in range(20)]]),
    ],
)


problem(
    id="weighted-expectimax",
    track="Expectimax Basics",
    title="When the Outcomes Aren't Equally Likely",
    difficulty="medium",
    points=15,
    blurb="A chance node's value is a weighted average -- probability times value, summed.",
    statement="""
<p>Real chance nodes rarely have uniform odds -- a loaded die, a weather
forecast, an opponent who favors one move. This problem uses a different
node type, <code>WNode</code>, where a CHANCE node's children each carry
an explicit probability:</p>

<pre class="block">wbuild(7)                                    a leaf holding 7
wbuild(("max", [3, 8]))                      a MAX node over two leaves
wbuild(("chance", [(0.25, 2), (0.75, 10)]))  a CHANCE node: 2 with
                                              probability 0.25, 10 with
                                              probability 0.75</pre>

<p>Write <code>weighted_expectimax(node)</code>. <code>node.kind</code>
is either <code>"max"</code> or <code>"chance"</code>; a MAX node's
<code>children</code> is a plain list of child nodes, while a CHANCE
node's <code>children</code> is a list of <code>(probability, child)</code>
pairs whose probabilities sum to <code>1</code>.</p>

<p>A CHANCE node's value is <strong>&sum; probability &times;
value</strong> over its children -- not a plain average, since each
outcome now counts in proportion to how likely it is.</p>
""",
    examples="""
>>> weighted_expectimax(wbuild(7))
7
>>> weighted_expectimax(wbuild(("chance", [(0.25, 2), (0.75, 10)])))
8.0
>>> weighted_expectimax(wbuild(("max", [3, 8])))
8
>>> weighted_expectimax(wbuild(("max", [
...     ("chance", [(0.5, 0), (0.5, 20)]),
...     ("chance", [(0.9, 5), (0.1, 6)])])))
10.0
""",
    starter=with_wnodes("""
def weighted_expectimax(node):
    pass
"""),
    hints=[
        "Base case: node.is_leaf() -- return node.value.",
        "If node.kind == 'max': recurse on each plain child in "
        "node.children and return the max of the results.",
        "If node.kind == 'chance': node.children is a list of (prob, "
        "child) pairs. For each pair, recurse into weighted_expectimax(child) "
        "to get that outcome's value, multiply by prob, and sum all of "
        "those products.",
    ],
    solution=with_wnodes("""
def weighted_expectimax(node):
    if node.is_leaf():
        return node.value
    if node.kind == "max":
        return max(weighted_expectimax(child) for child in node.children)
    return sum(prob * weighted_expectimax(child)
               for prob, child in node.children)
"""),
    tests=[
        T("a leaf is its own value", "assert weighted_expectimax(wbuild(7)) == 7"),
        T("an uneven chance node", """
got = weighted_expectimax(wbuild(("chance", [(0.25, 2), (0.75, 10)])))
assert got == 8.0, got
"""),
        T("a max node over plain leaves", """
assert weighted_expectimax(wbuild(("max", [3, 8]))) == 8
"""),
        T("the worked example: max over two uneven chance nodes", """
tree = wbuild(("max", [
    ("chance", [(0.5, 0), (0.5, 20)]),
    ("chance", [(0.9, 5), (0.1, 6)])]))
got = weighted_expectimax(tree)
assert got == 10.0, got
"""),
        T("using a plain average instead of weighting gives the wrong answer here", """
tree = wbuild(("chance", [(0.1, 0), (0.9, 100)]))
got = weighted_expectimax(tree)
if got == 50.0:
    raise AssertionError(
        "50.0 is the unweighted average -- multiply each outcome by its "
        "own probability before summing")
assert got == 90.0, got
"""),
        T("nested chance-under-chance, checked against a hand-built oracle", """
import random
random.seed(33)

def make(depth):
    if depth == 0 or random.random() < 0.3:
        return random.randint(-10, 10)
    if random.random() < 0.5:
        return ("max", [make(depth - 1) for _ in range(random.randint(1, 3))])
    n = random.randint(2, 3)
    raw = [random.random() + 0.01 for _ in range(n)]
    total = sum(raw)
    probs = [r / total for r in raw]
    return ("chance", [(p, make(depth - 1)) for p in probs])

def oracle(spec):
    if isinstance(spec, tuple):
        kind, kids_ = spec
        if kind == "max":
            return max(oracle(c) for c in kids_)
        return sum(p * oracle(c) for p, c in kids_)
    return spec

for _ in range(150):
    spec = make(3)
    got = weighted_expectimax(wbuild(spec))
    want = oracle(spec)
    assert abs(got - want) < 1e-6, (spec, got, want)
"""),
    ],
)


EXP_HORIZON_TREE = (13, [
    (8, [(12, [(9, []), (15, [])]), (18, [(6, []), (16, [])])]),
    (9, [(3, [(19, []), (8, [])]), (9, [(3, []), (2, [])])]),
])


problem(
    id="expectimax-horizon",
    track="Expectimax Basics",
    title="Expectimax With a Depth Limit",
    difficulty="medium",
    points=20,
    blurb="minimax_decision's exact shape, with CHANCE swapped in for MIN -- and no move to report at a chance node.",
    statement="""
<p>Write <code>expectimax_decision(node, limit)</code> for MAX at the
root, returning <code>(move, value, leaves)</code> -- the same triple
<code>minimax_decision</code> returned in the first gym, and the same
shape <code>get_best_move</code> will need on real games.</p>

<p>Every node at depth <code>limit</code>, and every real leaf reached
sooner, is evaluated directly and counts as one leaf -- which means
every node in the tree needs a value, not just the true leaves at the
bottom. That's why the example tree below carries a heuristic estimate
at <em>every</em> level, written <code>(h, [children])</code>, the same
convention <code>minimax_decision</code> used: without one, a depth cut-
off would have nothing meaningful to return.</p>

<p>Levels alternate MAX and CHANCE the same way they alternated MAX and
MIN before. The one real difference: a CHANCE node has no "best" child
to report -- it doesn't choose, it averages over everything -- so its
own move is always <code>None</code>. Only <code>move</code>s chosen at
MAX nodes ever matter, and only the very top one is returned. Notice how
the chosen move itself, not just the value, changes between limit 1 and
limit 2 below -- seeing one more level of the chance node's real spread
is enough to flip which branch looks best.</p>
""",
    examples="""
>>> tree = build((13, [
...     (8, [(12, [(9, []), (15, [])]), (18, [(6, []), (16, [])])]),
...     (9, [(3, [(19, []), (8, [])]), (9, [(3, []), (2, [])])])]))
>>> expectimax_decision(tree, 1)
(1, 9, 2)
>>> expectimax_decision(tree, 2)
(0, 15.0, 4)
""",
    starter=with_nodes("""
def expectimax_decision(node, limit):
    pass
"""),
    hints=[
        "Two helpers, max_value(subtree, depth) and chance_value(subtree, "
        "depth), each returning (value, move, leaves). Stop when depth == "
        "0 or subtree.is_leaf(): return (subtree.value, None, 1).",
        "max_value loops over enumerate(subtree.children), recurses into "
        "chance_value(child, depth - 1), sums leaves, and keeps the "
        "child's index as move only on a strictly better value -- same as "
        "minimax_decision.",
        "chance_value has no move to track: sum up every "
        "max_value(child, depth - 1)'s value, divide by the number of "
        "children, and return (average, None, total_leaves).",
    ],
    solution=with_nodes("""
def expectimax_decision(node, limit):

    def max_value(subtree, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        value, move, leaves = float('-inf'), None, 0
        for i, child in enumerate(subtree.children):
            v2, _, l2 = chance_value(child, depth - 1)
            leaves += l2
            if v2 > value:
                value, move = v2, i
        return value, move, leaves

    def chance_value(subtree, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        total, leaves = 0.0, 0
        for child in subtree.children:
            v2, _, l2 = max_value(child, depth - 1)
            leaves += l2
            total += v2
        return total / len(subtree.children), None, leaves

    value, move, leaves = max_value(node, limit)
    return move, value, leaves
"""),
    tests=[
        T("returns a (move, value, leaves) tuple", """
got = expectimax_decision(build([[1, 2], [3, 4]]), 2)
assert isinstance(got, tuple) and len(got) == 3, got
"""),
        T("the worked example at both limits", """
tree = build(@@FIG@@)
assert expectimax_decision(tree, 1) == (1, 9, 2), expectimax_decision(tree, 1)
assert expectimax_decision(tree, 2) == (0, 15.0, 4), expectimax_decision(tree, 2)
assert expectimax_decision(tree, 3) == (0, 15.5, 8), expectimax_decision(tree, 3)
""", FIG=EXP_HORIZON_TREE),
        T("a chance node never reports a move of its own", """
# a lopsided tree where the wrong move would look plausible if the chance
# level were mistakenly treated as a decision point
tree = build([[0, 0, 100], [1, 1, 1]])
move, value, leaves = expectimax_decision(tree, 2)
assert move in (0, 1), (move, value, leaves)
"""),
        T("random trees, cross-checked against the un-limited oracle", """
import random

def random_tree_local(rng, depth):
    if depth == 0 or (depth < 3 and rng.random() < 0.3):
        return rng.randint(-9, 20)
    return [random_tree_local(rng, depth - 1) for _ in range(rng.randint(1, 3))]

def oracle(spec, maximizing=True):
    if not isinstance(spec, list):
        return spec
    values = [oracle(c, not maximizing) for c in spec]
    return max(values) if maximizing else sum(values) / len(values)

random.seed(34)
CASES = [random_tree_local(random.Random(random.randint(0, 10**6)), 4)
        for _ in range(40)]

for spec in CASES:
    got_move, got_value, got_leaves = expectimax_decision(build(spec), 50)
    want_value = oracle(spec)
    assert abs(got_value - want_value) < 1e-6, (spec, got_value, want_value)
"""),
    ],
)


# --------------------------------------------------------------------------
# Track 2 -- Alpha-Beta Basics II (new angles, not a repeat of gym I)
# --------------------------------------------------------------------------

AB2_FIG = [[3, 12, 8], [2, 4, 6], [14, 5, 2]]
AB2_EQUAL = [[3, 5], [3, 9]]

_rng2 = random.Random(4001)
RANDOM_AB2 = [random_tree(_rng2, 5) for _ in range(30)]
RANDOM_AB2_H = [random_tree(_rng2, 5, heuristic=True) for _ in range(15)]


def o_alphabeta(spec, alpha=-INF, beta=INF, maximizing=True):
    if not kids(spec):
        return val(spec)
    if maximizing:
        value = -INF
        for c in kids(spec):
            value = max(value, o_alphabeta(c, alpha, beta, False))
            alpha = max(alpha, value)
            if value >= beta:
                return value
        return value
    value = INF
    for c in kids(spec):
        value = min(value, o_alphabeta(c, alpha, beta, True))
        beta = min(beta, value)
        if value <= alpha:
            return value
    return value


def o_visits(spec, alpha=-INF, beta=INF, maximizing=True):
    """Every node touched: 1 for this call, plus every child visited
    before any cutoff fires."""
    if not kids(spec):
        return val(spec), 1
    total = 1
    if maximizing:
        value = -INF
        for c in kids(spec):
            v, n = o_visits(c, alpha, beta, False)
            total += n
            value = max(value, v)
            alpha = max(alpha, value)
            if value >= beta:
                return value, total
        return value, total
    value = INF
    for c in kids(spec):
        v, n = o_visits(c, alpha, beta, True)
        total += n
        value = min(value, v)
        beta = min(beta, value)
        if value <= alpha:
            return value, total
    return value, total


def o_cutoffs(spec, alpha=-INF, beta=INF, maximizing=True):
    if not kids(spec):
        return val(spec), 0
    count = 0
    if maximizing:
        value = -INF
        for c in kids(spec):
            v, n = o_cutoffs(c, alpha, beta, False)
            count += n
            value = max(value, v)
            alpha = max(alpha, value)
            if value >= beta:
                return value, count + 1
        return value, count
    value = INF
    for c in kids(spec):
        v, n = o_cutoffs(c, alpha, beta, True)
        count += n
        value = min(value, v)
        beta = min(beta, value)
        if value <= alpha:
            return value, count + 1
    return value, count


problem(
    id="total-node-visits",
    track="Alpha-Beta Basics II",
    title="Counting Every Node, Not Just the Leaves",
    difficulty="easy",
    points=15,
    blurb="The homework's leaf count only tells half the story -- interior nodes cost real work too.",
    statement="""
<p>The first gym's leaf count measures how many terminal positions
alpha-beta evaluates. It says nothing about the <strong>interior</strong>
nodes visited along the way -- and on a real search tree, every one of
those costs a function call too.</p>

<p>Write <code>alphabeta_visits(node)</code>: run alpha-beta for MAX at
the root exactly as in figure 5.7, and return
<code>(value, total_visits)</code>, where <code>total_visits</code>
counts <strong>every</strong> node the search touches -- the root
itself, every interior node it recurses into, and every leaf it
evaluates. A single leaf counts <code>1</code>. Figure 5.2's root counts
<code>1</code> for itself, its 3 MIN children count <code>1</code> each,
and the 7 leaves alpha-beta actually reads (of the 9 total) bring the
count to <code>11</code>.</p>
""",
    examples="""
>>> alphabeta_visits(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]))
(3, 11)
>>> alphabeta_visits(build(4))
(4, 1)
""",
    starter=with_nodes("""
def alphabeta_visits(node):
    pass
"""),
    hints=[
        "Write max_value(subtree, alpha, beta) and min_value(subtree, "
        "alpha, beta), each returning (value, visits). A leaf returns "
        "(subtree.value, 1) -- it visits only itself.",
        "An interior node visits itself (1) plus every child it recurses "
        "into before any cutoff -- start visits = 1, and add each child's "
        "visits as you go, even the child that ultimately triggers the "
        "cutoff (that child was still visited before the cutoff fired).",
        "The cutoff logic itself (updating alpha/beta, checking value >= "
        "beta or value <= alpha) is unchanged from ordinary alpha-beta -- "
        "only the bookkeeping you're returning is different.",
    ],
    solution=with_nodes("""
def alphabeta_visits(node):

    def max_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 1
        value, visits = float('-inf'), 1
        for child in subtree.children:
            v, n = min_value(child, alpha, beta)
            visits += n
            value = max(value, v)
            alpha = max(alpha, value)
            if value >= beta:
                return value, visits
        return value, visits

    def min_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 1
        value, visits = float('inf'), 1
        for child in subtree.children:
            v, n = max_value(child, alpha, beta)
            visits += n
            value = min(value, v)
            beta = min(beta, value)
            if value <= alpha:
                return value, visits
        return value, visits

    return max_value(node, float('-inf'), float('inf'))
"""),
    tests=[
        T("a lone leaf visits only itself", """
assert alphabeta_visits(build(4)) == (4, 1)
"""),
        T("figure 5.2: root, 3 MIN children, 7 of 9 leaves", """
got = alphabeta_visits(build(@@FIG@@))
assert got == (3, 11), got
""", FIG=AB2_FIG),
        T("leaves alone undercounts -- interior nodes must be included too", """
got = alphabeta_visits(build(@@FIG@@))
if got == (3, 7):
    raise AssertionError(
        "(3, 7) is the leaf-only count -- add 1 for every interior node "
        "visited too, including the root")
""", FIG=AB2_FIG),
        T("random trees, checked against a direct oracle", """
CASES = @@CASES@@
for spec, want in CASES:
    got = alphabeta_visits(build(spec))
    assert got == want, (spec, got, want)
""", CASES=[(t, o_visits(t)) for t in RANDOM_AB2]),
    ],
)


problem(
    id="cutoff-count",
    track="Alpha-Beta Basics II",
    title="How Many Times Did Pruning Actually Fire?",
    difficulty="medium",
    points=15,
    blurb="Not every early return is a cutoff -- the last child in a loop always 'returns early' too, without anything being pruned.",
    statement="""
<p>Write <code>alphabeta_cutoffs(node)</code>: run alpha-beta for MAX at
the root, and return <code>(value, cutoffs)</code>, where
<code>cutoffs</code> counts how many times the pruning condition
(<code>value &gt;= beta</code> at a MAX node, <code>value &lt;= alpha</code>
at a MIN node) <strong>actually fired and skipped remaining
children</strong>.</p>

<p>Be careful what counts. A node that finishes its loop normally, having
looked at every child, is not a cutoff -- even though its function call
is about to return, nothing was skipped. Only count a node once, the
moment its cutoff condition trips and it stops early, abandoning
children it would otherwise have explored.</p>
""",
    examples="""
>>> alphabeta_cutoffs(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]))
(3, 2)
>>> alphabeta_cutoffs(build([[1, 2], [3, 4]]))
(3, 0)
""",
    starter=with_nodes("""
def alphabeta_cutoffs(node):
    pass
"""),
    hints=[
        "Same max_value/min_value shape as ordinary alpha-beta, each "
        "returning (value, cutoffs) instead of just (value, leaves).",
        "Accumulate the cutoff counts your children report, the same way "
        "you'd accumulate a leaf count -- cutoffs += child_cutoffs inside "
        "the loop.",
        "The moment your own cutoff condition trips, add exactly 1 more "
        "(for this node's own cutoff) before returning -- "
        "return value, cutoffs + 1. If the loop finishes without ever "
        "tripping, return cutoffs unchanged, with no +1.",
    ],
    solution=with_nodes("""
def alphabeta_cutoffs(node):

    def max_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 0
        value, cutoffs = float('-inf'), 0
        for child in subtree.children:
            v, n = min_value(child, alpha, beta)
            cutoffs += n
            value = max(value, v)
            alpha = max(alpha, value)
            if value >= beta:
                return value, cutoffs + 1
        return value, cutoffs

    def min_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 0
        value, cutoffs = float('inf'), 0
        for child in subtree.children:
            v, n = max_value(child, alpha, beta)
            cutoffs += n
            value = min(value, v)
            beta = min(beta, value)
            if value <= alpha:
                return value, cutoffs + 1
        return value, cutoffs

    return max_value(node, float('-inf'), float('inf'))
"""),
    tests=[
        T("a lone leaf has no cutoffs at all", """
assert alphabeta_cutoffs(build(4)) == (4, 0)
"""),
        T("a tree with no pruning: every value improves the bound but never trips it", """
got = alphabeta_cutoffs(build([[1, 2], [3, 4]]))
assert got == (3, 0), got
"""),
        T("figure 5.2: exactly two cutoffs, at the second and third MIN nodes", """
got = alphabeta_cutoffs(build(@@FIG@@))
assert got == (3, 2), got
""", FIG=AB2_FIG),
        T("finishing a loop normally is not a cutoff", """
# every value at this node makes the loop run to completion -- no child
# is ever skipped, so this node itself contributes 0 cutoffs
tree = build([5, 5, 5])
got = alphabeta_cutoffs(tree)
if got[1] != 0:
    raise AssertionError(
        "a node that examines every child without skipping any should "
        "not count as a cutoff, even though its call is about to return")
"""),
        T("random trees, checked against a direct oracle", """
CASES = @@CASES@@
for spec, want in CASES:
    got = alphabeta_cutoffs(build(spec))
    assert got == want, (spec, got, want)
""", CASES=[(t, o_cutoffs(t)) for t in RANDOM_AB2]),
    ],
)


problem(
    id="negamax",
    track="Alpha-Beta Basics II",
    title="One Function Instead of Two: Negamax",
    difficulty="medium",
    points=20,
    blurb="max_value and min_value are mirror images of each other -- negate the value and swap the roles of alpha and beta, and one function does both jobs.",
    statement="""
<p>Every alpha-beta implementation so far has needed two nearly-identical
functions, <code>max_value</code> and <code>min_value</code>, that differ
only by which comparison operator and which of <code>alpha</code>/
<code>beta</code> gets updated. <strong>Negamax</strong> is the standard
trick real game engines use to collapse them into one: score every leaf
from the mover's own point of view, and negate the value on the way back
up.</p>

<p>Write <code>negamax(node, alpha, beta, color)</code>, where
<code>color</code> is <code>1</code> or <code>-1</code>: multiply a
leaf's stored value by <code>color</code> before returning it, so a node
always evaluates its own position as "good for me." Recurse with
<code>-beta, -alpha</code> (the window flips and swaps) and
<code>-color</code> (the next level scores from the other side), negate
what comes back, and keep only the <strong>best</strong> (largest) result
-- there is no separate "take the min" branch anymore, because negation
already turned every level's job into "pick the biggest."</p>

<p>The single cutoff condition is <code>value &gt;= beta</code>, checked
after every child, exactly like MAX's condition in ordinary alpha-beta --
because negamax reframes <em>every</em> level as a maximizing one.</p>
""",
    examples="""
>>> tree = build([[3, 12, 8], [2, 4, 6], [14, 5, 2]])
>>> negamax(tree, float('-inf'), float('inf'), 1)
3
>>> negamax(tree, float('-inf'), float('inf'), -1)
-6
""",
    starter=with_nodes("""
def negamax(node, alpha, beta, color):
    pass
"""),
    hints=[
        "Base case: a leaf returns color * node.value -- flip the sign "
        "only at the leaves, where a real value first appears.",
        "Recursive case: value = float('-inf'); for each child: "
        "v = -negamax(child, -beta, -alpha, -color); take value = "
        "max(value, v); alpha = max(alpha, value); then cut off if "
        "value >= beta.",
        "Compare this shape to your ordinary max_value: negamax's loop "
        "is exactly max_value's loop, with min_value nowhere to be seen "
        "-- the negation is what makes a single function correct for "
        "every level.",
    ],
    solution=with_nodes("""
def negamax(node, alpha, beta, color):
    if node.is_leaf():
        return color * node.value
    value = float('-inf')
    for child in node.children:
        v = -negamax(child, -beta, -alpha, -color)
        value = max(value, v)
        alpha = max(alpha, value)
        if value >= beta:
            return value
    return value
"""),
    tests=[
        T("a lone leaf, both colors", """
assert negamax(build(7), float('-inf'), float('inf'), 1) == 7
assert negamax(build(7), float('-inf'), float('inf'), -1) == -7
"""),
        T("figure 5.2 from MAX's side matches ordinary alpha-beta", """
tree = build(@@FIG@@)
got = negamax(tree, float('-inf'), float('inf'), 1)
assert got == 3, got
""", FIG=AB2_FIG),
        T("figure 5.2 from MIN's side is the negation of MAX's", """
tree = build(@@FIG@@)
got = negamax(tree, float('-inf'), float('inf'), -1)
assert got == -6, got
""", FIG=AB2_FIG),
        T("random trees, cross-checked against ordinary alpha-beta", """
CASES = @@CASES@@
for spec, want_max, want_min in CASES:
    tree = build(spec)
    got = negamax(tree, float('-inf'), float('inf'), 1)
    assert got == want_max, (spec, got, want_max)
    got_min_side = negamax(tree, float('-inf'), float('inf'), -1)
    assert got_min_side == -want_min, (spec, got_min_side, want_min)
""", CASES=[(t, o_alphabeta(t, maximizing=True), o_alphabeta(t, maximizing=False))
           for t in RANDOM_AB2]),
    ],
)


AB2_ITER_TREE = (0, [(4, [(2, [7, 1]), (9, [3, 8])]),
                     (6, [(5, [2, 6]), (1, [9, 9])]),
                     (3, [(8, [4, 5])])])


def o_iterative(spec, max_limit):
    out = []
    for limit in range(1, max_limit + 1):
        move, value, leaves = None, None, 0

        def max_value(subtree, alpha, beta, depth):
            if depth == 0 or not kids(subtree):
                return val(subtree), None, 1
            v, m, n = -INF, None, 0
            for i, c in enumerate(kids(subtree)):
                v2, _, l2 = min_value(c, alpha, beta, depth - 1)
                n += l2
                if v2 > v:
                    v, m = v2, i
                alpha = max(alpha, v)
                if v >= beta:
                    return v, m, n
            return v, m, n

        def min_value(subtree, alpha, beta, depth):
            if depth == 0 or not kids(subtree):
                return val(subtree), None, 1
            v, m, n = INF, None, 0
            for i, c in enumerate(kids(subtree)):
                v2, _, l2 = max_value(c, alpha, beta, depth - 1)
                n += l2
                if v2 < v:
                    v, m = v2, i
                beta = min(beta, v)
                if v <= alpha:
                    return v, m, n
            return v, m, n

        value, move, leaves = max_value(spec, -INF, INF, limit)
        out.append((limit, move, value, leaves))
    return out


problem(
    id="iterative-deepening-ab",
    track="Alpha-Beta Basics II",
    title="Searching Depth 1, Then 2, Then 3",
    difficulty="medium",
    points=20,
    blurb="A real engine doesn't pick a depth and hope -- it searches shallow first, deeper if there's time, keeping the best answer found so far at every step.",
    statement="""
<p>Real game engines rarely search to one fixed depth. Time is limited
and unpredictable, so instead they search depth 1, then depth 2, then
depth 3, and so on -- keeping the best move found at each completed depth
-- and stop whenever they run out of time. This is
<strong>iterative deepening</strong>, and it means the engine always has
a legal answer ready, even if it gets cut off mid-search.</p>

<p>Write <code>iterative_deepening(node, max_limit)</code>: for every
depth limit from <code>1</code> up to and including
<code>max_limit</code>, run alpha-beta for MAX at the root at that depth,
and collect the results. Return a list of
<code>(limit, move, value, leaves)</code> tuples, one per depth, in
increasing order of <code>limit</code>. As with any depth-limited search,
every node needs a value ready in case the limit stops there, so the
tree below carries a heuristic estimate at every level.</p>

<p>Each depth is searched <strong>independently and from scratch</strong>
-- nothing carries over between them. That repeats a lot of work
(everything depth 2 does, depth 3 does again and then some), which seems
wasteful, but the shallow searches are cheap compared to the deepest one,
and the guarantee of always having an answer ready is usually worth
far more than the redundant computation costs.</p>
""",
    examples="""
>>> tree = build((0, [(4, [(2, [7, 1]), (9, [3, 8])]),
...                   (6, [(5, [2, 6]), (1, [9, 9])]),
...                   (3, [(8, [4, 5])])]))
>>> iterative_deepening(tree, 1)
[(1, 1, 6, 3)]
>>> iterative_deepening(tree, 2)
[(1, 1, 6, 3), (2, 2, 8, 5)]
""",
    starter=with_nodes("""
def iterative_deepening(node, max_limit):
    pass
"""),
    hints=[
        "This calls for the exact alpha-beta-with-a-depth-limit function "
        "you've already built elsewhere -- max_value/min_value taking "
        "(subtree, alpha, beta, depth) and returning (value, move, "
        "leaves) -- run once per limit.",
        "Loop limit from 1 to max_limit inclusive (range(1, max_limit + "
        "1)). For each limit, call your depth-limited search fresh, with "
        "a brand new alpha=-inf, beta=inf window -- don't reuse state "
        "between limits.",
        "Append (limit, move, value, leaves) to a results list each "
        "time, and return the whole list at the end.",
    ],
    solution=with_nodes("""
def iterative_deepening(node, max_limit):

    def max_value(subtree, alpha, beta, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        value, move, leaves = float('-inf'), None, 0
        for i, child in enumerate(subtree.children):
            v2, _, l2 = min_value(child, alpha, beta, depth - 1)
            leaves += l2
            if v2 > value:
                value, move = v2, i
            alpha = max(alpha, value)
            if value >= beta:
                return value, move, leaves
        return value, move, leaves

    def min_value(subtree, alpha, beta, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        value, move, leaves = float('inf'), None, 0
        for i, child in enumerate(subtree.children):
            v2, _, l2 = max_value(child, alpha, beta, depth - 1)
            leaves += l2
            if v2 < value:
                value, move = v2, i
            beta = min(beta, value)
            if value <= alpha:
                return value, move, leaves
        return value, move, leaves

    results = []
    for limit in range(1, max_limit + 1):
        value, move, leaves = max_value(node, float('-inf'), float('inf'),
                                        limit)
        results.append((limit, move, value, leaves))
    return results
"""),
    tests=[
        T("a single depth returns a one-element list", """
tree = build(@@FIG@@)
got = iterative_deepening(tree, 1)
assert got == [(1, 1, 6, 3)], got
""", FIG=AB2_ITER_TREE),
        T("depths accumulate -- earlier results are not thrown away", """
tree = build(@@FIG@@)
got = iterative_deepening(tree, 3)
assert len(got) == 3, got
assert [limit for limit, m, v, l in got] == [1, 2, 3], got
""", FIG=AB2_ITER_TREE),
        T("the worked example: the chosen move itself changes with depth", """
tree = build(@@FIG@@)
got = iterative_deepening(tree, 3)
assert got == [(1, 1, 6, 3), (2, 2, 8, 5), (3, 0, 7, 8)], got
""", FIG=AB2_ITER_TREE),
        T("each depth matches a fresh, independent call at that same limit", """
CASES = @@CASES@@
for spec, max_limit, want in CASES:
    got = iterative_deepening(build(spec), max_limit)
    assert got == want, (spec, got, want)
""", CASES=[(t, 4, o_iterative(t, 4)) for t in RANDOM_AB2_H]),
    ],
)


# --------------------------------------------------------------------------
# Track 3 -- Expectimax, Homework-Style
# --------------------------------------------------------------------------

def dom_legal_moves(board, vertical):
    rows, cols = len(board), len(board[0])
    moves = []
    for r in range(rows):
        for c in range(cols):
            if vertical:
                if r + 1 < rows and not board[r][c] and not board[r + 1][c]:
                    moves.append((r, c))
            else:
                if c + 1 < cols and not board[r][c] and not board[r][c + 1]:
                    moves.append((r, c))
    return moves


def dom_after(board, move, vertical):
    r, c = move
    new = [row[:] for row in board]
    new[r][c] = True
    if vertical:
        new[r + 1][c] = True
    else:
        new[r][c + 1] = True
    return new


def dom_best(board, vertical, limit, bug=None):
    def children(state, maxing):
        to_move = vertical if maxing else not vertical
        return [(m, dom_after(state, m, to_move))
                for m in dom_legal_moves(state, to_move)]

    def evaluate(state, maxing):
        me = vertical if bug == "mover" else vertical
        return (len(dom_legal_moves(state, vertical))
                - len(dom_legal_moves(state, not vertical)))

    return expectimax_search(board, children, evaluate, limit, bug)


F3, X3 = False, True
DOM_MISTAKES = ("always_max", "used_min")
DOM_BOARDS = [
    [[F3] * 2 for _ in range(2)],
    [[F3] * 3 for _ in range(2)],
    [[F3] * 3 for _ in range(3)],
    [[X3, F3, F3], [F3, F3, F3], [F3, F3, X3]],
    [[F3, X3, X3, F3], [F3, F3, F3, F3]],
    [[F3, F3, X3, F3], [F3, F3, F3, X3], [F3, F3, F3, F3]],
]


def dom_case(board, vertical, limit):
    want = dom_best(board, vertical, limit)
    mistakes = [(bug, dom_best(board, vertical, limit, bug))
                for bug in DOM_MISTAKES]
    return (board, vertical, limit, want,
            [(n, o) for n, o in mistakes if o != want])


DOM_CASES = [dom_case(b, v, k) for b in DOM_BOARDS
             for v in (True, False) for k in (1, 2, 3)]
DOM_MISTAKE_CASE = next((c for c in DOM_CASES
                        if dict(c[4]).get("used_min") is not None), None)
if DOM_MISTAKE_CASE is None:
    DOM_MISTAKE_CASE = dom_case(
        [[False, True, True, False], [False, False, False, False]], True, 2)
    assert dict(DOM_MISTAKE_CASE[4]).get("used_min") is not None

DOM_SOLUTION = '''
def create_dominoes_vs_random_game(rows, cols):
    return DominoesVsRandomGame([[False] * cols for _ in range(rows)])


class DominoesVsRandomGame(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0])

    def get_board(self):
        return self.board

    def is_legal_move(self, row, col, vertical):
        if vertical:
            if not (0 <= row < self.rows - 1 and 0 <= col < self.cols):
                return False
            return not self.board[row][col] and not self.board[row + 1][col]
        if not (0 <= row < self.rows and 0 <= col < self.cols - 1):
            return False
        return not self.board[row][col] and not self.board[row][col + 1]

    def legal_moves(self, vertical):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_legal_move(row, col, vertical):
                    yield (row, col)

    def perform_move(self, row, col, vertical):
        self.board[row][col] = True
        if vertical:
            self.board[row + 1][col] = True
        else:
            self.board[row][col + 1] = True

    def game_over(self, vertical):
        return next(self.legal_moves(vertical), None) is None

    def copy(self):
        return DominoesVsRandomGame([row[:] for row in self.board])

    def successors(self, vertical):
        for row, col in self.legal_moves(vertical):
            child = self.copy()
            child.perform_move(row, col, vertical)
            yield (row, col), child

    def get_expectimax_move(self, vertical, limit):

        def evaluate(game):
            return (len(list(game.legal_moves(vertical)))
                    - len(list(game.legal_moves(not vertical))))

        def max_value(game, vert_flag, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            value, move, leaves = float('-inf'), None, 0
            for mod_move, mod_game in game.successors(vert_flag):
                v2, _, l2 = chance_value(mod_game, not vert_flag, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, mod_move
            return value, move, leaves

        def chance_value(game, vert_flag, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            children = list(game.successors(vert_flag))
            total, leaves = 0.0, 0
            for mod_move, mod_game in children:
                v2, _, l2 = max_value(mod_game, not vert_flag, depth - 1)
                leaves += l2
                total += v2
            return total / len(children), None, leaves

        value, move, leaves = max_value(self, vertical, limit)
        return move, value, leaves
'''

problem(
    id="dominoes-vs-random",
    track="Expectimax, Homework-Style",
    title="Dominoes Against an Opponent Who Never Plans Ahead",
    difficulty="hard",
    points=30,
    blurb="Same DominoesGame class, but the opponent always plays get_random_move -- so MIN's worst case is the wrong model, and CHANCE's average is the right one.",
    statement="""
<p>Same board, same <code>1&times;2</code> pieces, same vertical/
horizontal roles as the homework. The one thing that changes: your
opponent isn't out to beat you. Every turn, they call something exactly
like the homework's own <code>get_random_move</code> -- they pick
uniformly at random among their own legal moves, with no strategy at
all.</p>

<p>Playing minimax against a player like that is needlessly cautious: it
prepares for their <em>worst possible</em> move, when in reality every
legal move is equally likely, including plenty of bad ones for them.
<strong>Expectimax</strong> is the right tool whenever you know your
opponent's policy isn't adversarial -- average over what they'll
actually do, rather than assuming they'll do whatever hurts you most.</p>

<p>Write the class, method for method as in the homework, but with
<code>get_expectimax_move(vertical, limit)</code> in place of
<code>get_best_move</code>: your own turns are MAX nodes exactly as
before, but the opponent's turns are CHANCE nodes, averaging uniformly
over every legal move they could make. The evaluation itself is
unchanged from the homework -- your legal moves minus theirs, always
from the <code>vertical</code> passed to the call.</p>
""",
    examples="""
>>> g = create_dominoes_vs_random_game(2, 2)
>>> g.get_expectimax_move(True, 1)
((0, 0), 1, 2)
>>> g = create_dominoes_vs_random_game(2, 3)
>>> move, value, leaves = g.get_expectimax_move(True, 2)
>>> move
(0, 1)
""",
    starter="""
def create_dominoes_vs_random_game(rows, cols):
    pass


class DominoesVsRandomGame(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def is_legal_move(self, row, col, vertical):
        pass

    def legal_moves(self, vertical):
        pass

    def perform_move(self, row, col, vertical):
        pass

    def game_over(self, vertical):
        pass

    def copy(self):
        pass

    def successors(self, vertical):
        pass

    def get_expectimax_move(self, vertical, limit):
        pass
""",
    hints=[
        "Everything through successors() is identical to the homework's "
        "DominoesGame -- copy that structure over unchanged.",
        "get_expectimax_move needs two helpers instead of max_value/"
        "min_value: max_value(game, vert_flag, depth) for your turns, "
        "chance_value(game, vert_flag, depth) for the opponent's. Both "
        "stop on depth == 0 or game_over(vert_flag), returning "
        "(evaluate(game), None, 1).",
        "chance_value has no move to choose -- collect every successor "
        "into a list, recurse into max_value on each, sum the values, "
        "and divide by how many successors there were. If there's only "
        "one, that's fine -- dividing by 1 changes nothing.",
        "There is no alpha, no beta, no cutoff anywhere in this search. "
        "Expectimax can't safely prune the way alpha-beta does, since a "
        "chance node's value depends on every child, not just the best "
        "or worst one -- skipping any of them changes the average.",
    ],
    solution=DOM_SOLUTION,
    tests=[
        T("stores the board and creates empty boards of any shape", """
board = [[False, True], [False, False]]
assert DominoesVsRandomGame(board).get_board() is board
assert create_dominoes_vs_random_game(2, 3).get_board() == [[False]*3]*2
"""),
        T("is_legal_move and legal_moves match the homework's own rules", """
board = [[False, True], [False, False]]
game = DominoesVsRandomGame([row[:] for row in board])
assert game.is_legal_move(0, 0, False) is False
assert game.is_legal_move(1, 0, False) is True
assert list(game.legal_moves(False)) == [(1, 0)]
"""),
        T("perform_move fills in place and returns None; game_over is player-specific", """
board = [[False] * 2 for _ in range(2)]
game = DominoesVsRandomGame(board)
assert game.perform_move(0, 0, True) is None
assert board == [[True, False], [True, False]]
assert game.game_over(True) is False, (
    "a vertical move still fits at (0, 1)")
assert game.game_over(False) is True, (
    "column 0 is fully blocked, and column 1 alone can't fit a "
    "horizontal piece")
assert DominoesVsRandomGame([[True, True], [True, True]]).game_over(True) is True
"""),
        T("copy is deep and successors leave the original untouched", """
original = DominoesVsRandomGame([[False] * 3 for _ in range(2)])
twin = original.copy()
assert isinstance(twin, DominoesVsRandomGame)
assert twin.get_board() == original.get_board()
assert all(a is not b for a, b in zip(twin.get_board(), original.get_board()))
pairs = list(original.successors(True))
assert original.get_board() == [[False] * 3 for _ in range(2)]
assert [m for m, _ in pairs] == @@WANT_MOVES@@
""", WANT_MOVES=dom_legal_moves([[False]*3 for _ in range(2)], True)),
        T("no alpha-beta pruning is happening: every leaf under the limit is touched", """
# on an empty board every move has an identical evaluation, so an
# expectimax search (which cannot prune) must still visit every one of
# them -- unlike alpha-beta, which could stop early on a tie
board = [[False] * 3 for _ in range(3)]
move, value, leaves = DominoesVsRandomGame(board).get_expectimax_move(True, 1)
assert leaves == @@WANT_LEAVES@@, (
    "expectimax cannot prune -- every child must be visited to average "
    "over them, so leaves should equal the full branching factor")
""", WANT_LEAVES=len(dom_legal_moves([[False]*3 for _ in range(3)], True))),
        T("get_expectimax_move: minimax's worst-case model gives the wrong value here", """
board, vertical, limit, want, mistakes = @@CASE@@
got = DominoesVsRandomGame([row[:] for row in board]).get_expectimax_move(vertical, limit)
if got != want and got == dict(mistakes).get("used_min"):
    raise AssertionError(
        "%r: this looks like ordinary minimax (taking the opponent's "
        "worst move for you) instead of averaging over all of their "
        "legal moves -- the opponent here is random, not adversarial"
        % (got,))
assert got == want, (got, want)
""", CASE=DOM_MISTAKE_CASE),
        T("get_expectimax_move across boards, players and limits", """
CASES = @@CASES@@
MESSAGES = {
    "always_max": "the opponent's turn was scored as if they play "
                 "optimally against you (still maximizing), not randomly",
    "used_min": "used the opponent's worst move (minimax) instead of "
               "averaging over all of their legal moves",
}
for board, vertical, limit, want, mistakes in CASES:
    game = DominoesVsRandomGame([row[:] for row in board])
    got = game.get_expectimax_move(vertical, limit)
    assert game.get_board() == board, "get_expectimax_move changed the board"
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("vertical=%s limit=%d on %r: got %r, %s"
                                     % (vertical, limit, board, got,
                                        MESSAGES[name]))
    gm, gv, gl = got
    wm, wv, wl = want
    assert gm == wm, (board, vertical, limit, got, want)
    assert abs(gv - wv) < 1e-9, (board, vertical, limit, got, want)
    assert gl == wl, (board, vertical, limit, got, want)
""", CASES=DOM_CASES),
    ],
)


def tri_legal_e(board, r, c, vertical):
    rows, cols = len(board), len(board[0])
    cells = [(r + i, c) if vertical else (r, c + i) for i in range(3)]
    return all(0 <= rr < rows and 0 <= cc < cols and not board[rr][cc]
               for rr, cc in cells)


def tri_moves_e(board, vertical):
    return [(r, c) for r in range(len(board)) for c in range(len(board[0]))
            if tri_legal_e(board, r, c, vertical)]


def tri_after_e(board, move, vertical):
    r, c = move
    new = [row[:] for row in board]
    for rr, cc in ([(r + i, c) for i in range(3)] if vertical
                   else [(r, c + i) for i in range(3)]):
        new[rr][cc] = True
    return new


def tri_best_e(board, vertical, limit, bug=None):
    def children(state, maxing):
        to_move = vertical if maxing else not vertical
        return [(m, tri_after_e(state, m, to_move))
                for m in tri_moves_e(state, to_move)]

    def evaluate(state, maxing):
        return (len(tri_moves_e(state, vertical))
                - len(tri_moves_e(state, not vertical)))

    return expectimax_search(board, children, evaluate, limit, bug)


TRI_BOARDS_E = [
    [[F3] * 3 for _ in range(3)],
    [[F3] * 4 for _ in range(2)],
    [[F3] * 4 for _ in range(3)],
]


def tri_case_e(board, vertical, limit):
    want = tri_best_e(board, vertical, limit)
    mistakes = [(bug, tri_best_e(board, vertical, limit, bug))
                for bug in DOM_MISTAKES]
    return (board, vertical, limit, want,
            [(n, o) for n, o in mistakes if o != want])


TRI_CASES_E = [tri_case_e(b, v, k) for b in TRI_BOARDS_E
               for v in (True, False) for k in (1, 2)]

TRI_SOLUTION_E = DOM_SOLUTION.replace(
    "create_dominoes_vs_random_game", "create_triominoes_vs_random_game"
).replace("DominoesVsRandomGame", "TriominoesVsRandomGame").replace(
    '''    def is_legal_move(self, row, col, vertical):
        if vertical:
            if not (0 <= row < self.rows - 1 and 0 <= col < self.cols):
                return False
            return not self.board[row][col] and not self.board[row + 1][col]
        if not (0 <= row < self.rows and 0 <= col < self.cols - 1):
            return False
        return not self.board[row][col] and not self.board[row][col + 1]''',
    '''    def cells(self, row, col, vertical):
        if vertical:
            return [(row + i, col) for i in range(3)]
        return [(row, col + i) for i in range(3)]

    def is_legal_move(self, row, col, vertical):
        for r, c in self.cells(row, col, vertical):
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return False
            if self.board[r][c]:
                return False
        return True''').replace(
    '''    def perform_move(self, row, col, vertical):
        self.board[row][col] = True
        if vertical:
            self.board[row + 1][col] = True
        else:
            self.board[row][col + 1] = True''',
    '''    def perform_move(self, row, col, vertical):
        for r, c in self.cells(row, col, vertical):
            self.board[r][c] = True''')

problem(
    id="triominoes-vs-random",
    track="Expectimax, Homework-Style",
    title="Triominoes Against the Same Careless Opponent",
    difficulty="hard",
    points=25,
    blurb="1x3 pieces this time, on top of the same MAX/CHANCE structure -- practice recognizing which parts of a variant carry over and which don't.",
    statement="""
<p>Combine the two variations you've already seen separately: pieces are
<code>1&times;3</code>, like the homework-length gym's own triominoes
problem, and the opponent plays uniformly at random, like
<code>DominoesVsRandomGame</code> above. Nothing else changes.</p>

<p>Write the class the same way: <code>is_legal_move</code> needs the
triominoes-style three-cell bounds check (reaching two squares past the
anchor, not one), while <code>get_expectimax_move(vertical, limit)</code>
needs the MAX/CHANCE structure from <code>DominoesVsRandomGame</code>,
completely unchanged. Recognizing which parts of a variant transfer
directly and which don't is the actual point of this problem.</p>
""",
    examples="""
>>> g = create_triominoes_vs_random_game(3, 3)
>>> g.is_legal_move(0, 0, True), g.is_legal_move(1, 0, True)
(True, False)
>>> move, value, leaves = g.get_expectimax_move(True, 1)
>>> move
(0, 0)
""",
    starter="""
def create_triominoes_vs_random_game(rows, cols):
    pass


class TriominoesVsRandomGame(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def cells(self, row, col, vertical):
        pass

    def is_legal_move(self, row, col, vertical):
        pass

    def legal_moves(self, vertical):
        pass

    def perform_move(self, row, col, vertical):
        pass

    def game_over(self, vertical):
        pass

    def copy(self):
        pass

    def successors(self, vertical):
        pass

    def get_expectimax_move(self, vertical, limit):
        pass
""",
    hints=[
        "is_legal_move: build the three cells the piece would cover, "
        "then check each is in bounds and empty -- same shape as the "
        "gym I triominoes problem.",
        "get_expectimax_move: identical structure to "
        "DominoesVsRandomGame's -- max_value for your turns, "
        "chance_value averaging over the opponent's, no alpha, no beta, "
        "no cutoff anywhere.",
        "If you're tempted to add pruning here, stop -- expectimax can't "
        "safely skip any child of a chance node, since the average needs "
        "every one of them.",
    ],
    solution=TRI_SOLUTION_E,
    tests=[
        T("stores the board and creates empty boards of any shape", """
board = [[False] * 4 for _ in range(2)]
assert TriominoesVsRandomGame(board).get_board() is board
assert create_triominoes_vs_random_game(2, 5).get_board() == [[False]*5]*2
"""),
        T("is_legal_move matches the three-cell rule, in and out of bounds", """
CASES = @@CASES@@
for board, expected in CASES:
    game = TriominoesVsRandomGame([row[:] for row in board])
    for row, col, vertical, want in expected:
        got = game.is_legal_move(row, col, vertical)
        assert got == want, (board, row, col, vertical, got, want)
""", CASES=[(b, [(r, c, v, tri_legal_e(b, r, c, v))
                 for r in range(-1, len(b) + 2)
                 for c in range(-1, len(b[0]) + 2) for v in (True, False)])
            for b in TRI_BOARDS_E[:2]]),
        T("perform_move fills three cells in place; game_over is player-specific", """
board = [[False] * 4 for _ in range(3)]
game = TriominoesVsRandomGame(board)
assert game.perform_move(0, 0, True) is None
assert board == [[True, False, False, False],
                 [True, False, False, False],
                 [True, False, False, False]]
wide = TriominoesVsRandomGame([[False] * 5 for _ in range(2)])
assert wide.game_over(True) is True
assert wide.game_over(False) is False
"""),
        T("copy is independent and successors never touch the original", """
original = TriominoesVsRandomGame([[False] * 4 for _ in range(3)])
twin = original.copy()
assert all(a is not b for a, b in zip(twin.get_board(), original.get_board()))
list(original.successors(True))
assert original.get_board() == [[False] * 4 for _ in range(3)]
"""),
        T("get_expectimax_move across boards, players and limits", """
CASES = @@CASES@@
for board, vertical, limit, want, mistakes in CASES:
    game = TriominoesVsRandomGame([row[:] for row in board])
    got = game.get_expectimax_move(vertical, limit)
    assert game.get_board() == board
    gm, gv, gl = got
    wm, wv, wl = want
    assert gm == wm and abs(gv - wv) < 1e-9 and gl == wl, (
        board, vertical, limit, got, want)
""", CASES=TRI_CASES_E),
    ],
)


def take_best_e(stones, max_take, limit, bug=None):
    def children(state, maxing):
        return [(t, state - t) for t in range(1, min(max_take, state) + 1)]

    def evaluate(state, maxing):
        if state != 0:
            return 0
        return -1 if maxing else 1

    return expectimax_search(stones, children, evaluate, limit, bug)


TAKE_MISTAKES_E = ("always_max", "used_min")
TAKE_CASES_E = []
for _stones in range(1, 8):
    for _k in (2, 3):
        for _limit in (1, 2, 3, 4):
            _want = take_best_e(_stones, _k, _limit)
            _mistakes = [(bug, take_best_e(_stones, _k, _limit, bug))
                        for bug in TAKE_MISTAKES_E]
            TAKE_CASES_E.append((_stones, _k, _limit, _want,
                                 [(n, o) for n, o in _mistakes if o != _want]))
TAKE_MISTAKE_CASE_E = next(c for c in TAKE_CASES_E
                          if dict(c[4]).get("used_min") is not None)

TAKE_GIVEN_E = '''
class TakeAwayVsRandomGame(object):

    def __init__(self, stones, max_take=3):
        self.stones = stones
        self.max_take = max_take

    def game_over(self):
        return self.stones == 0

    def legal_moves(self):
        for take in range(1, min(self.max_take, self.stones) + 1):
            yield take

    def successors(self):
        for take in self.legal_moves():
            yield take, TakeAwayVsRandomGame(self.stones - take, self.max_take)
'''.strip("\n")

problem(
    id="take-away-vs-random",
    track="Expectimax, Homework-Style",
    title="Last Stone Wins, Against a Coin Flip",
    difficulty="hard",
    points=25,
    blurb="The homework's take-away game against an opponent who picks their take uniformly at random -- the win/loss value becomes a genuine expectation, not just +-1.",
    statement="""
<p>Same take-away game as the alpha-beta gym: a pile of stones, each
player takes between <code>1</code> and <code>max_take</code> on their
turn, and whoever takes the <strong>last</strong> stone wins. This time
your opponent picks their take uniformly at random among their legal
options, instead of playing to beat you.</p>

<p>Write <code>get_expectimax_move(self, limit)</code> on
<code>TakeAwayVsRandomGame</code> (given, along with
<code>game_over</code>, <code>legal_moves</code>, and
<code>successors</code>), returning <code>(move, value, leaves)</code>
for the player about to move -- structurally identical to the earlier
<code>TakeAwayGame</code>'s search, with <code>chance_value</code> in
place of <code>min_value</code>.</p>

<p>The terminal scoring is unchanged: <code>+1</code> if the pile is
empty and it's the opponent's turn (you took the last stone),
<code>-1</code> if it's empty and it's your own turn, <code>0</code> at
the depth horizon. What changes is what those numbers <em>mean</em> once
CHANCE is averaging over them: the value <code>get_expectimax_move</code>
returns is no longer just <code>+1</code> or <code>-1</code> -- it
becomes a genuine expectation, a number between them representing how
good this position is against a random opponent on average, not in the
worst case.</p>
""",
    examples="""
>>> TakeAwayVsRandomGame(1).get_expectimax_move(1)
(1, 1, 1)
>>> TakeAwayVsRandomGame(4, max_take=3).get_expectimax_move(2)
(1, -0.3333333333333333, 6)
""",
    starter=TAKE_GIVEN_E + """

    def get_expectimax_move(self, limit):
        pass
""",
    hints=[
        "Same shape as TakeAwayGame's search: max_value(game, depth) for "
        "your turn, chance_value(game, depth) for the opponent's. Both "
        "stop on game.game_over() (returning the terminal +-1) or "
        "depth == 0 (returning 0), same as before.",
        "chance_value has no move to track -- gather every successor "
        "into a list, recurse into max_value on each, average the "
        "results (sum divided by count), and return (average, None, "
        "total_leaves).",
        "There's no alpha, no beta, no cutoff condition anywhere here -- "
        "expectimax needs every child's value to compute an average, so "
        "nothing can be safely skipped.",
    ],
    solution=TAKE_GIVEN_E + """

    def get_expectimax_move(self, limit):

        def max_value(game, depth):
            if game.game_over():
                return -1, None, 1
            if depth == 0:
                return 0, None, 1
            value, move, leaves = float('-inf'), None, 0
            for take, after in game.successors():
                v2, _, l2 = chance_value(after, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, take
            return value, move, leaves

        def chance_value(game, depth):
            if game.game_over():
                return 1, None, 1
            if depth == 0:
                return 0, None, 1
            children = list(game.successors())
            total, leaves = 0.0, 0
            for take, after in children:
                v2, _, l2 = max_value(after, depth - 1)
                leaves += l2
                total += v2
            return total / len(children), None, leaves

        value, move, leaves = max_value(self, limit)
        return move, value, leaves
""",
    tests=[
        T("returns a (move, value, leaves) tuple", """
got = TakeAwayVsRandomGame(3).get_expectimax_move(1)
assert isinstance(got, tuple) and len(got) == 3, got
"""),
        T("taking the last stone is a certain win", """
got = TakeAwayVsRandomGame(1).get_expectimax_move(1)
assert got == (1, 1, 1), got
"""),
        T("no pruning happens: leaves grows with the full branching factor", """
game = TakeAwayVsRandomGame(6, max_take=3)
move, value, leaves = game.get_expectimax_move(2)
assert leaves == 9, (
    "expectimax cannot prune -- every branch at every depth must be "
    "visited to average over it")
"""),
        T("get_expectimax_move: minimax's worst case is not this opponent's actual behavior", """
stones, max_take, limit, want, mistakes = @@CASE@@
got = TakeAwayVsRandomGame(stones, max_take).get_expectimax_move(limit)
if got != want and got == dict(mistakes).get("used_min"):
    raise AssertionError(
        "%r: this looks like ordinary minimax (assuming the opponent "
        "always takes their worst option for you) instead of averaging "
        "over every legal take they could make" % (got,))
gm, gv, gl = got
wm, wv, wl = want
assert gm == wm and abs(gv - wv) < 1e-9 and gl == wl, (got, want)
""", CASE=TAKE_MISTAKE_CASE_E),
        T("every pile, take limit and depth up to 7, 3 and 4", """
CASES = @@CASES@@
for stones, max_take, limit, want, mistakes in CASES:
    got = TakeAwayVsRandomGame(stones, max_take).get_expectimax_move(limit)
    gm, gv, gl = got
    wm, wv, wl = want
    assert gm == wm and abs(gv - wv) < 1e-9 and gl == wl, (
        stones, max_take, limit, got, want)
""", CASES=TAKE_CASES_E),
    ],
)


def pig_oracle(turn_score, limit):
    def helper(turn_score, limit):
        if limit == 0:
            return "bank", turn_score, 1
        bank_value, leaves = turn_score, 1
        roll_total = 0.0
        for face in range(1, 7):
            if face == 1:
                roll_total += 0
                leaves += 1
            else:
                _, v, l = helper(turn_score + face, limit - 1)
                roll_total += v
                leaves += l
        roll_value = roll_total / 6.0
        if roll_value > bank_value:
            return "roll", roll_value, leaves
        return "bank", bank_value, leaves
    return helper(turn_score, limit)


PIG_CASES = [(ts, k, pig_oracle(ts, k))
             for ts in (0, 3, 8, 15, 20) for k in (0, 1, 2, 3)]

problem(
    id="pig-bank-or-roll",
    track="Expectimax, Homework-Style",
    title="Pig: Bank Your Points, or Push Your Luck",
    difficulty="hard",
    points=25,
    blurb="A real six-sided die, not a metaphor for an opponent -- chance nodes here are actual random outcomes, with real 1-in-6 probabilities.",
    statement="""
<p>Pig is a classic dice game: on your turn you repeatedly roll a die,
adding each result to your turn total -- until you either choose to
<strong>bank</strong> those points (locking them in and ending your
turn), or roll a <code>1</code>, which <strong>busts</strong> your whole
turn total back to zero and ends it immediately regardless.</p>

<p>Write <code>pig_decision(turn_score, limit)</code>: given your current
(not-yet-banked) turn total, decide whether to <code>"bank"</code> or
<code>"roll"</code>, returning
<code>(action, expected_value, leaves)</code>, the same
action-first convention every search in this gym returns.
<code>expected_value</code>
is how many points you can expect to walk away with from this point on,
playing optimally, looking no more than <code>limit</code> further
rolls ahead. Every one of the 6 die faces is a genuine
<strong>CHANCE</strong> outcome with probability <code>1/6</code> --
this is the first problem in the gym where a chance node isn't a stand-in
for an opponent, it's real randomness.</p>

<p>Two choices are available at every decision point:</p>

<ul>
  <li><code>"bank"</code> is worth exactly <code>turn_score</code> --
      guaranteed, no chance involved.</li>
  <li><code>"roll"</code> is a chance node over the 6 faces: rolling a
      <code>1</code> (probability <code>1/6</code>) busts, worth
      <code>0</code>; rolling <code>2</code> through <code>6</code>
      (each probability <code>1/6</code>) adds that face to
      <code>turn_score</code> and hands you a brand new decision one ply
      deeper, worth whatever the best of banking-or-rolling <em>then</em>
      turns out to be.</li>
</ul>

<p>Take the larger of the two. At the depth limit, assume you'd bank
right now -- the same value banking would give regardless, so it doubles
as a sensible cutoff heuristic with no extra work.</p>
""",
    examples="""
>>> pig_decision(0, 0)
('bank', 0, 1)
>>> pig_decision(0, 1)
('roll', 3.3333333333333335, 7)
>>> pig_decision(20, 1)
('bank', 20, 7)
""",
    starter="""
def pig_decision(turn_score, limit):
    pass
""",
    hints=[
        "Base case: limit == 0. Assume you bank right now -- return "
        "(turn_score, 'bank', 1).",
        "bank_value is just turn_score. For roll_value, loop face in "
        "range(1, 7): face == 1 contributes 0 to the running total (and "
        "counts as 1 leaf on its own, since a bust needs no further "
        "recursion); face 2 through 6 recurses into "
        "pig_decision(turn_score + face, limit - 1), and you need its "
        "value (not its action) added into the total.",
        "roll_value is that total divided by 6 -- all six faces are "
        "equally likely. Compare roll_value to bank_value and return "
        "whichever is larger, with 'roll' or 'bank' to match, and the "
        "leaves from every recursive call summed together (a bust face "
        "contributes exactly 1 leaf of its own).",
    ],
    solution="""
def pig_decision(turn_score, limit):
    if limit == 0:
        return 'bank', turn_score, 1

    bank_value, leaves = turn_score, 1
    roll_total = 0.0
    for face in range(1, 7):
        if face == 1:
            roll_total += 0
            leaves += 1
        else:
            _, value, l = pig_decision(turn_score + face, limit - 1)
            roll_total += value
            leaves += l
    roll_value = roll_total / 6.0

    if roll_value > bank_value:
        return 'roll', roll_value, leaves
    return 'bank', bank_value, leaves
""",
    tests=[
        T("at the horizon, banking is the only option", """
assert pig_decision(0, 0) == ('bank', 0, 1)
assert pig_decision(15, 0) == ('bank', 15, 1)
"""),
        T("one roll ahead from zero: rolling beats banking nothing", """
got = pig_decision(0, 1)
assert got == ('roll', 10 / 3, 7), got
"""),
        T("with a big turn total already banked up, one more roll isn't worth the bust risk", """
# both options are still fully evaluated -- expectimax cannot know
# rolling is worse without exploring every one of its six outcomes
got = pig_decision(20, 1)
assert got == ('bank', 20, 7), got
"""),
        T("rolling always explores exactly 6 outcomes per level -- no pruning", """
value, action, leaves = pig_decision(0, 2)
assert leaves > 7, (
    "two levels of a 6-outcome chance node should visit well more than "
    "7 leaves -- expectimax cannot skip any outcome")
"""),
        T("random turn scores and horizons, checked against a direct oracle", """
CASES = @@CASES@@
for turn_score, limit, want in CASES:
    got = pig_decision(turn_score, limit)
    ga, gv, gl = got
    wa, wv, wl = want
    assert ga == wa, (turn_score, limit, got, want)
    assert abs(gv - wv) < 1e-9, (turn_score, limit, got, want)
    assert gl == wl, (turn_score, limit, got, want)
""", CASES=PIG_CASES),
    ],
)


# --------------------------------------------------------------------------
# Track 4 -- Alpha-Beta, Homework-Style II
# --------------------------------------------------------------------------

L_OFFSETS = [
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
]


def l_cells(row, col, orientation):
    return [(row + dr, col + dc) for dr, dc in L_OFFSETS[orientation]]


def l_legal(board, row, col, orientation):
    rows, cols = len(board), len(board[0])
    return all(0 <= r < rows and 0 <= c < cols and not board[r][c]
               for r, c in l_cells(row, col, orientation))


def l_orientations(vertical):
    return (0, 1) if vertical else (2, 3)


def l_moves(board, vertical):
    rows, cols = len(board), len(board[0])
    return [(r, c, o) for r in range(rows) for c in range(cols)
            for o in l_orientations(vertical) if l_legal(board, r, c, o)]


def l_after(board, move):
    r, c, o = move
    new = [row[:] for row in board]
    for rr, cc in l_cells(r, c, o):
        new[rr][cc] = True
    return new


def l_best(board, vertical, limit, bug=None):
    def children(state, maxing):
        to_move = vertical if maxing else not vertical
        return [(m, l_after(state, m)) for m in l_moves(state, to_move)]

    def evaluate(state, maxing):
        return (len(l_moves(state, vertical)) - len(l_moves(state, not vertical)))

    return game_search(board, children, evaluate, limit, bug)


FL, XL = False, True
L_BOARDS = [
    [[FL] * 3 for _ in range(3)],
    [[FL] * 4 for _ in range(3)],
    [[XL, FL, FL], [FL, FL, FL], [FL, FL, XL]],
]
L_MISTAKES = ("no_window", "strict_cut", "ties_last")


def l_case(board, vertical, limit):
    want = l_best(board, vertical, limit)
    mistakes = [(bug, l_best(board, vertical, limit, bug)) for bug in L_MISTAKES]
    mistakes += [("deeper", l_best(board, vertical, limit + 1))]
    return (board, vertical, limit, want,
            [(n, o) for n, o in mistakes if o != want])


L_CASES = [l_case(b, v, k) for b in L_BOARDS for v in (True, False)
           for k in (1, 2)]

L_SOLUTION = '''
OFFSETS = [
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
]


def create_ltromino_game(rows, cols):
    return LTrominoGame([[False] * cols for _ in range(rows)])


class LTrominoGame(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0])

    def get_board(self):
        return self.board

    def cells(self, row, col, orientation):
        return [(row + dr, col + dc) for dr, dc in OFFSETS[orientation]]

    def is_legal_move(self, row, col, orientation):
        for r, c in self.cells(row, col, orientation):
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return False
            if self.board[r][c]:
                return False
        return True

    def orientations(self, vertical):
        return (0, 1) if vertical else (2, 3)

    def legal_moves(self, vertical):
        for row in range(self.rows):
            for col in range(self.cols):
                for o in self.orientations(vertical):
                    if self.is_legal_move(row, col, o):
                        yield (row, col, o)

    def perform_move(self, row, col, orientation):
        for r, c in self.cells(row, col, orientation):
            self.board[r][c] = True

    def game_over(self, vertical):
        return next(self.legal_moves(vertical), None) is None

    def copy(self):
        return LTrominoGame([row[:] for row in self.board])

    def successors(self, vertical):
        for move in self.legal_moves(vertical):
            child = self.copy()
            child.perform_move(*move)
            yield move, child

    def get_best_move(self, vertical, limit):

        def evaluate(game):
            return (len(list(game.legal_moves(vertical)))
                    - len(list(game.legal_moves(not vertical))))

        def max_value(game, vert_flag, alpha, beta, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            value, move, leaves = float('-inf'), None, 0
            for mod_move, mod_game in game.successors(vert_flag):
                v2, _, l2 = min_value(mod_game, not vert_flag, alpha, beta,
                                      depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, mod_move
                alpha = max(alpha, value)
                if value >= beta:
                    return value, move, leaves
            return value, move, leaves

        def min_value(game, vert_flag, alpha, beta, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            value, move, leaves = float('inf'), None, 0
            for mod_move, mod_game in game.successors(vert_flag):
                v2, _, l2 = max_value(mod_game, not vert_flag, alpha, beta,
                                      depth - 1)
                leaves += l2
                if v2 < value:
                    value, move = v2, mod_move
                beta = min(beta, value)
                if value <= alpha:
                    return value, move, leaves
            return value, move, leaves

        value, move, leaves = max_value(self, vertical, float('-inf'),
                                        float('inf'), limit)
        return move, value, leaves
'''

problem(
    id="ltromino-game",
    track="Alpha-Beta, Homework-Style II",
    title="L-Trominoes: Four Orientations, Not Two",
    difficulty="hard",
    points=30,
    blurb="A piece with 4 rotations instead of 2 -- bounds-checking becomes 'does this 2x2 block fit', not 'does this row or column range fit'.",
    statement="""
<p>Same rules as the homework -- two players alternate placing pieces on
a Boolean grid, last player able to move wins -- with an L-shaped piece
instead of a straight one. An L-tromino covers 3 of the 4 cells in some
2&times;2 block, in one of 4 orientations (which corner is left out):</p>

<pre class="block">0: X X     1: X X     2: X .     3: . X
    X .         . X         X X         X X</pre>

<p>The "vertical" player may only use orientations <code>0</code> and
<code>1</code>; the "horizontal" player only <code>2</code> and
<code>3</code> -- an arbitrary but fixed split, playing the same role
the homework's vertical/horizontal distinction played, just applied to
rotations instead of a straight line's direction.</p>

<p>Write the class: <code>is_legal_move(row, col, orientation)</code>
checks that <code>row, col</code> anchors a 2&times;2 block fully on the
board with all 3 of that orientation's cells empty.
<code>legal_moves(vertical)</code> yields <code>(row, col, orientation)</code>
in row-major order over <code>(row, col)</code>, trying the smaller
orientation number first at each cell.
<code>get_best_move(vertical, limit)</code> is alpha-beta exactly as in
the homework, scoring a board as the caller's legal moves minus the
opponent's.</p>
""",
    examples="""
>>> g = create_ltromino_game(3, 3)
>>> g.is_legal_move(0, 0, 0), g.is_legal_move(2, 2, 0)
(True, False)
>>> list(g.legal_moves(True))[:3]
[(0, 0, 0), (0, 0, 1), (0, 1, 0)]
>>> create_ltromino_game(3, 3).get_best_move(True, 1)
((1, 0, 1), 1, 8)
""",
    starter="""
OFFSETS = [
    [(0, 0), (0, 1), (1, 0)],
    [(0, 0), (0, 1), (1, 1)],
    [(0, 0), (1, 0), (1, 1)],
    [(0, 1), (1, 0), (1, 1)],
]


def create_ltromino_game(rows, cols):
    pass


class LTrominoGame(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def cells(self, row, col, orientation):
        pass

    def is_legal_move(self, row, col, orientation):
        pass

    def orientations(self, vertical):
        pass

    def legal_moves(self, vertical):
        pass

    def perform_move(self, row, col, orientation):
        pass

    def game_over(self, vertical):
        pass

    def copy(self):
        pass

    def successors(self, vertical):
        pass

    def get_best_move(self, vertical, limit):
        pass
""",
    hints=[
        "cells(row, col, orientation) just looks up OFFSETS[orientation] "
        "and adds (row, col) to each pair. is_legal_move checks every "
        "cell that comes back is in bounds and empty -- the same "
        "structure as every earlier is_legal_move, just with 3 arbitrary "
        "offsets instead of a straight line.",
        "orientations(vertical) returns (0, 1) if vertical else (2, 3). "
        "legal_moves loops row, then col, then each orientation in that "
        "tuple, checking is_legal_move each time.",
        "Everything from perform_move through get_best_move is a direct "
        "copy of the homework's structure -- perform_move fills whatever "
        "cells() returns, and get_best_move's alpha-beta doesn't care at "
        "all how many orientations there are, only that successors() "
        "hands it (move, child) pairs.",
    ],
    solution=L_SOLUTION,
    tests=[
        T("stores the board and creates empty boards of any shape", """
board = [[False, True], [False, False]]
assert LTrominoGame(board).get_board() is board
assert create_ltromino_game(2, 4).get_board() == [[False] * 4] * 2
"""),
        T("is_legal_move checks all 4 orientations, in and out of bounds", """
CASES = @@CASES@@
for board, expected in CASES:
    game = LTrominoGame([row[:] for row in board])
    for row, col, o, want in expected:
        got = game.is_legal_move(row, col, o)
        assert got == want, (board, row, col, o, got, want)
""", CASES=[(b, [(r, c, o, l_legal(b, r, c, o))
                 for r in range(-1, len(b) + 1)
                 for c in range(-1, len(b[0]) + 1) for o in range(4)])
            for b in L_BOARDS[:2]]),
        T("legal_moves restricts to the caller's two orientations, row-major", """
board = [[False] * 3 for _ in range(3)]
game = LTrominoGame(board)
got_v = list(game.legal_moves(True))
got_h = list(game.legal_moves(False))
assert all(o in (0, 1) for _, _, o in got_v), got_v
assert all(o in (2, 3) for _, _, o in got_h), got_h
assert got_v == @@WANT_V@@, got_v
""", WANT_V=l_moves([[False]*3 for _ in range(3)], True)),
        T("perform_move fills all 3 cells in place and returns None", """
board = [[False] * 3 for _ in range(3)]
game = LTrominoGame(board)
assert game.perform_move(0, 0, 0) is None
assert board == [[True, True, False], [True, False, False], [False]*3]
"""),
        T("game_over and copy behave per the homework's conventions", """
assert LTrominoGame([[False]*3]*3).game_over(True) is False
jammed = LTrominoGame([[True, False], [False, True]])
assert jammed.game_over(True) is True and jammed.game_over(False) is True
twin = LTrominoGame([[False]*3 for _ in range(3)]).copy()
assert isinstance(twin, LTrominoGame)
twin.perform_move(0, 0, 0)
assert twin.get_board() != [[False]*3 for _ in range(3)]
"""),
        T("get_best_move across boards, players and limits", """
CASES = @@CASES@@
MESSAGES = {
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later move -- replace the move only on >",
    "deeper": "searched one move deeper than the limit",
}
for board, vertical, limit, want, mistakes in CASES:
    game = LTrominoGame([row[:] for row in board])
    got = game.get_best_move(vertical, limit)
    assert game.get_board() == board
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("vertical=%s limit=%d on %r: got %r, %s"
                                     % (vertical, limit, board, got,
                                        MESSAGES[name]))
    assert got == want, (board, vertical, limit, got, want)
""", CASES=L_CASES),
    ],
)


# --- Blocked-Cell Dominoes: a 3-state board (0=empty, 1=filled, 2=blocked) ---

EMPTY, FILLED, BLOCKED = 0, 1, 2


def bd_legal(board, row, col, vertical):
    rows, cols = len(board), len(board[0])
    if vertical:
        cells = [(row, col), (row + 1, col)]
        if not (0 <= row < rows - 1 and 0 <= col < cols):
            return False
    else:
        cells = [(row, col), (row, col + 1)]
        if not (0 <= row < rows and 0 <= col < cols - 1):
            return False
    return all(board[r][c] == EMPTY for r, c in cells)


def bd_moves(board, vertical):
    rows, cols = len(board), len(board[0])
    return [(r, c) for r in range(rows) for c in range(cols)
            if bd_legal(board, r, c, vertical)]


def bd_after(board, move, vertical):
    r, c = move
    new = [row[:] for row in board]
    new[r][c] = FILLED
    if vertical:
        new[r + 1][c] = FILLED
    else:
        new[r][c + 1] = FILLED
    return new


def bd_best(board, vertical, limit, bug=None):
    def children(state, maxing):
        to_move = vertical if maxing else not vertical
        return [(m, bd_after(state, m, to_move))
                for m in bd_moves(state, to_move)]

    def evaluate(state, maxing):
        return (len(bd_moves(state, vertical)) - len(bd_moves(state, not vertical)))

    return game_search(board, children, evaluate, limit, bug)


E, F, B = EMPTY, FILLED, BLOCKED
BD_BOARDS = [
    [[E, E], [E, E]],
    [[E, B, E], [E, E, E]],
    [[E, E, E], [B, E, B], [E, E, E]],
    [[E, F, E, E], [E, E, B, E]],
]
BD_MISTAKES = ("no_window", "strict_cut", "ties_last")


def bd_case(board, vertical, limit):
    want = bd_best(board, vertical, limit)
    mistakes = [(bug, bd_best(board, vertical, limit, bug)) for bug in BD_MISTAKES]
    mistakes += [("deeper", bd_best(board, vertical, limit + 1))]
    return (board, vertical, limit, want,
            [(n, o) for n, o in mistakes if o != want])


BD_CASES = [bd_case(b, v, k) for b in BD_BOARDS for v in (True, False)
            for k in (1, 2)]

BD_SOLUTION = '''
EMPTY, FILLED, BLOCKED = 0, 1, 2


def create_blocked_dominoes_game(rows, cols):
    return BlockedDominoesGame([[EMPTY] * cols for _ in range(rows)])


class BlockedDominoesGame(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0])

    def get_board(self):
        return self.board

    def is_legal_move(self, row, col, vertical):
        if vertical:
            if not (0 <= row < self.rows - 1 and 0 <= col < self.cols):
                return False
            cells = [(row, col), (row + 1, col)]
        else:
            if not (0 <= row < self.rows and 0 <= col < self.cols - 1):
                return False
            cells = [(row, col), (row, col + 1)]
        return all(self.board[r][c] == EMPTY for r, c in cells)

    def legal_moves(self, vertical):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_legal_move(row, col, vertical):
                    yield (row, col)

    def perform_move(self, row, col, vertical):
        self.board[row][col] = FILLED
        if vertical:
            self.board[row + 1][col] = FILLED
        else:
            self.board[row][col + 1] = FILLED

    def game_over(self, vertical):
        return next(self.legal_moves(vertical), None) is None

    def copy(self):
        return BlockedDominoesGame([row[:] for row in self.board])

    def successors(self, vertical):
        for row, col in self.legal_moves(vertical):
            child = self.copy()
            child.perform_move(row, col, vertical)
            yield (row, col), child

    def get_best_move(self, vertical, limit):

        def evaluate(game):
            return (len(list(game.legal_moves(vertical)))
                    - len(list(game.legal_moves(not vertical))))

        def max_value(game, vert_flag, alpha, beta, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            value, move, leaves = float('-inf'), None, 0
            for mod_move, mod_game in game.successors(vert_flag):
                v2, _, l2 = min_value(mod_game, not vert_flag, alpha, beta,
                                      depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, mod_move
                alpha = max(alpha, value)
                if value >= beta:
                    return value, move, leaves
            return value, move, leaves

        def min_value(game, vert_flag, alpha, beta, depth):
            if depth == 0 or game.game_over(vert_flag):
                return evaluate(game), None, 1
            value, move, leaves = float('inf'), None, 0
            for mod_move, mod_game in game.successors(vert_flag):
                v2, _, l2 = max_value(mod_game, not vert_flag, alpha, beta,
                                      depth - 1)
                leaves += l2
                if v2 < value:
                    value, move = v2, mod_move
                beta = min(beta, value)
                if value <= alpha:
                    return value, move, leaves
            return value, move, leaves

        value, move, leaves = max_value(self, vertical, float('-inf'),
                                        float('inf'), limit)
        return move, value, leaves
'''

problem(
    id="blocked-dominoes-game",
    track="Alpha-Beta, Homework-Style II",
    title="Dominoes on a Board With Holes in It",
    difficulty="hard",
    points=25,
    blurb="A third cell state, permanently blocked -- occupancy checks need a real comparison now, not just a truthy/falsy test.",
    statement="""
<p>Same rules as the homework, but the board isn't just
<code>True</code>/<code>False</code> anymore. Each cell holds one of
three states: <code>EMPTY = 0</code>, <code>FILLED = 1</code> (a domino
sits there), or <code>BLOCKED = 2</code> (permanently unusable -- a hole
in the board, never fillable by either player, present from the very
start and never changing).</p>

<p>Write the class the same way as the homework, with one change
threaded through everything that checks a cell: <code>is_legal_move</code>
must check <code>self.board[r][c] == EMPTY</code>, not
<code>not self.board[r][c]</code> -- a blocked cell is falsy-adjacent in
neither direction, and treating <code>BLOCKED</code> as available (or
treating it like <code>FILLED</code> some places and not others) breaks
the search. <code>perform_move</code> sets a cell to <code>FILLED</code>,
never to <code>True</code>. Everything else -- <code>legal_moves</code>,
<code>game_over</code>, <code>copy</code>, <code>successors</code>,
<code>get_best_move</code> -- is structurally identical to the
homework.</p>
""",
    examples="""
>>> g = BlockedDominoesGame([[0, 2], [0, 0]])
>>> g.is_legal_move(0, 0, True), g.is_legal_move(0, 0, False)
(True, False)
>>> g.perform_move(0, 0, True)
>>> g.get_board()
[[1, 2], [1, 0]]
>>> g.game_over(False)
True
""",
    starter="""
EMPTY, FILLED, BLOCKED = 0, 1, 2


def create_blocked_dominoes_game(rows, cols):
    pass


class BlockedDominoesGame(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def is_legal_move(self, row, col, vertical):
        pass

    def legal_moves(self, vertical):
        pass

    def perform_move(self, row, col, vertical):
        pass

    def game_over(self, vertical):
        pass

    def copy(self):
        pass

    def successors(self, vertical):
        pass

    def get_best_move(self, vertical, limit):
        pass
""",
    hints=[
        "is_legal_move: same bounds check as the homework, then compare "
        "every relevant cell against EMPTY with == rather than checking "
        "truthiness -- self.board[row][col] == EMPTY and "
        "self.board[row+1][col] == EMPTY (or the horizontal pair).",
        "perform_move sets cells to FILLED (the integer 1), not True. "
        "Since FILLED == 1 == True in Python, mixing them up won't "
        "crash -- but BLOCKED == 2 is truthy too, so any code that "
        "checks 'if self.board[r][c]:' instead of '== EMPTY' will wrongly "
        "treat a blocked cell the same as a filled one, which happens to "
        "give the right answer for occupancy but the wrong one anywhere "
        "you need to tell BLOCKED and FILLED apart.",
        "get_best_move, successors, copy, game_over -- none of them look "
        "at individual cell values at all, only at is_legal_move's "
        "output, so they're identical to the homework's, untouched.",
    ],
    solution=BD_SOLUTION,
    tests=[
        T("stores the board and creates all-EMPTY boards of any shape", """
board = [[0, 1], [2, 0]]
assert BlockedDominoesGame(board).get_board() is board
assert create_blocked_dominoes_game(2, 3).get_board() == [[0]*3]*2
"""),
        T("is_legal_move treats BLOCKED as permanently unusable", """
CASES = @@CASES@@
for board, expected in CASES:
    game = BlockedDominoesGame([row[:] for row in board])
    for row, col, vertical, want in expected:
        got = game.is_legal_move(row, col, vertical)
        assert got == want, (board, row, col, vertical, got, want)
""", CASES=[(b, [(r, c, v, bd_legal(b, r, c, v))
                 for r in range(-1, len(b) + 1)
                 for c in range(-1, len(b[0]) + 1) for v in (True, False)])
            for b in BD_BOARDS[:3]]),
        T("perform_move writes FILLED, not True, and BLOCKED cells never change", """
board = [[0, 2], [0, 0]]
game = BlockedDominoesGame(board)
assert game.perform_move(0, 0, True) is None
assert board == [[1, 2], [1, 0]], board
assert board[0][1] == 2, "a blocked cell changed value"
"""),
        T("game_over accounts for BLOCKED cells removing otherwise-open moves", """
# every empty cell is isolated from every other by a blocked neighbour
board = [[0, 2, 0], [2, 0, 2], [0, 2, 0]]
game = BlockedDominoesGame(board)
assert game.game_over(True) is True
assert game.game_over(False) is True
"""),
        T("copy is independent and successors never touch the original", """
original = BlockedDominoesGame([[0, 0, 2], [0, 0, 0]])
twin = original.copy()
assert all(a is not b for a, b in zip(twin.get_board(), original.get_board()))
list(original.successors(True))
assert original.get_board() == [[0, 0, 2], [0, 0, 0]]
"""),
        T("get_best_move across boards with holes, players and limits", """
CASES = @@CASES@@
MESSAGES = {
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later move -- replace the move only on >",
    "deeper": "searched one move deeper than the limit",
}
for board, vertical, limit, want, mistakes in CASES:
    game = BlockedDominoesGame([row[:] for row in board])
    got = game.get_best_move(vertical, limit)
    assert game.get_board() == board
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("vertical=%s limit=%d on %r: got %r, %s"
                                     % (vertical, limit, board, got,
                                        MESSAGES[name]))
    assert got == want, (board, vertical, limit, got, want)
""", CASES=BD_CASES),
    ],
)


# --- Dominoes, Most Pieces Wins: a scoring win condition, not last-to-move ---

def sc_legal(board, row, col, vertical):
    rows, cols = len(board), len(board[0])
    if vertical:
        if not (0 <= row < rows - 1 and 0 <= col < cols):
            return False
        return not board[row][col] and not board[row + 1][col]
    if not (0 <= row < rows and 0 <= col < cols - 1):
        return False
    return not board[row][col] and not board[row][col + 1]


def sc_moves(board, vertical):
    rows, cols = len(board), len(board[0])
    return [(r, c) for r in range(rows) for c in range(cols)
            if sc_legal(board, r, c, vertical)]


def sc_after(board, move, vertical):
    r, c = move
    new = [row[:] for row in board]
    new[r][c] = True
    if vertical:
        new[r + 1][c] = True
    else:
        new[r][c + 1] = True
    return new


def sc_jammed(board):
    return not sc_moves(board, True) and not sc_moves(board, False)


def sc_best(board, vertical, my_count, opp_count, limit, bug=None):
    """Bespoke recursive search (not game_search) because a player with
    no legal moves in their own orientation, but the board not globally
    jammed, must PASS rather than be treated as terminal."""

    def terminal(mc, oc):
        if mc > oc:
            return 1
        if mc < oc:
            return -1
        return 0

    def max_value(bd, mc, oc, alpha, beta, depth):
        if sc_jammed(bd):
            return terminal(mc, oc), None, 1
        if depth == 0:
            return 0, None, 1
        moves = sc_moves(bd, vertical)
        if not moves:
            v2, _, l2 = min_value(bd, mc, oc, alpha, beta, depth - 1)
            return v2, None, l2
        value, move, leaves = -INF, None, 0
        for m in moves:
            child = sc_after(bd, m, vertical)
            v2, _, l2 = min_value(child, mc + 1, oc, alpha, beta, depth - 1)
            leaves += l2
            if v2 > value:
                value, move = v2, m
            elif bug == "ties_last" and v2 == value:
                move = m
            if bug != "no_window":
                alpha = max(alpha, value)
            cut = (value > beta) if bug == "strict_cut" else (value >= beta)
            if cut:
                return value, move, leaves
        return value, move, leaves

    def min_value(bd, mc, oc, alpha, beta, depth):
        if sc_jammed(bd):
            return terminal(mc, oc), None, 1
        if depth == 0:
            return 0, None, 1
        moves = sc_moves(bd, not vertical)
        if not moves:
            v2, _, l2 = max_value(bd, mc, oc, alpha, beta, depth - 1)
            return v2, None, l2
        value, move, leaves = INF, None, 0
        for m in moves:
            child = sc_after(bd, m, not vertical)
            v2, _, l2 = max_value(child, mc, oc + 1, alpha, beta, depth - 1)
            leaves += l2
            if v2 < value:
                value, move = v2, m
            elif bug == "ties_last" and v2 == value:
                move = m
            if bug != "no_window":
                beta = min(beta, value)
            cut = (value < alpha) if bug == "strict_cut" else (value <= alpha)
            if cut:
                return value, move, leaves
        return value, move, leaves

    value, move, leaves = max_value(board, my_count, opp_count, -INF, INF, limit)
    return move, value, leaves


FS, XS = False, True
SC_BOARDS = [
    [[FS] * 2 for _ in range(2)],
    [[FS] * 3 for _ in range(2)],
    [[FS] * 3 for _ in range(3)],
    [[XS, FS, FS], [FS, FS, FS], [FS, FS, XS]],
]
SC_MISTAKES = ("no_window", "strict_cut", "ties_last")


def sc_case(board, vertical, limit):
    want = sc_best(board, vertical, 0, 0, limit)
    mistakes = [(bug, sc_best(board, vertical, 0, 0, limit, bug))
                for bug in SC_MISTAKES]
    mistakes += [("deeper", sc_best(board, vertical, 0, 0, limit + 1))]
    return (board, vertical, limit, want,
            [(n, o) for n, o in mistakes if o != want])


SC_CASES = [sc_case(b, v, k) for b in SC_BOARDS for v in (True, False)
            for k in (2, 3)]
SC_MISTAKE_CASE = next(c for c in SC_CASES
                       if dict(c[4]).get("strict_cut") is not None
                       or dict(c[4]).get("no_window") is not None)

SCORING_GIVEN = '''
def create_scoring_dominoes_game(rows, cols):
    return ScoringDominoesGame([[False] * cols for _ in range(rows)], 0, 0)


class ScoringDominoesGame(object):

    def __init__(self, board, my_pieces=0, opp_pieces=0):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0])
        self.my_pieces = my_pieces
        self.opp_pieces = opp_pieces

    def get_board(self):
        return self.board

    def is_legal_move(self, row, col, vertical):
        if vertical:
            if not (0 <= row < self.rows - 1 and 0 <= col < self.cols):
                return False
            return not self.board[row][col] and not self.board[row + 1][col]
        if not (0 <= row < self.rows and 0 <= col < self.cols - 1):
            return False
        return not self.board[row][col] and not self.board[row][col + 1]

    def legal_moves(self, vertical):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_legal_move(row, col, vertical):
                    yield (row, col)

    def perform_move(self, row, col, vertical):
        self.board[row][col] = True
        if vertical:
            self.board[row + 1][col] = True
        else:
            self.board[row][col + 1] = True

    def is_jammed(self):
        return (next(self.legal_moves(True), None) is None
                and next(self.legal_moves(False), None) is None)
'''.strip("\n")

problem(
    id="scoring-dominoes-game",
    track="Alpha-Beta, Homework-Style II",
    title="Dominoes: Whoever Places More Pieces Wins",
    difficulty="hard",
    points=30,
    blurb="A completely different win condition -- the game runs until nobody can move at all, and the piece count decides, not who moved last.",
    statement="""
<p>Same board, same <code>1&times;2</code> pieces, same vertical/
horizontal roles -- a different objective entirely. The game continues
until the board is <strong>jammed for both orientations at once</strong>
(neither a vertical nor a horizontal move exists anywhere), which can
easily happen with empty squares still on the board. Whoever has placed
<strong>more total pieces</strong> by that point wins; equal counts are a
draw.</p>

<p>This changes what <code>game_over</code> and the evaluation need to
track. There's no single player who "runs out of moves" the way the
homework's <code>game_over(vertical)</code> checked -- a vertical move
being unavailable doesn't end anything if a horizontal one still is.
<code>is_jammed()</code> (given, along with the rest of the game
mechanics below) checks both orientations at once.</p>

<p>Write <code>get_best_move(self, vertical, limit)</code>, given
everything through <code>perform_move</code> and <code>is_jammed</code>.
It needs to track <strong>piece counts</strong> alongside the board
through the whole search -- each node needs to know how many pieces the
caller has placed so far along this line of play, and how many the
opponent has, not just what the board looks like. At a jammed position,
score <code>+1</code> if the caller placed more pieces than the opponent,
<code>-1</code> if fewer, <code>0</code> if tied. At the depth horizon
with the game still going, score <code>0</code> -- there's no cheap
heuristic here the way "my moves minus theirs" was in the homework, since
what matters is a running count, not the current board shape.</p>

<p>One rule the homework never needed, because it couldn't arise there:
a player can be <strong>stuck in their own orientation while the game
keeps going</strong>. If it's your turn and no vertical move exists
anywhere, but a horizontal move still does somewhere, the board is not
jammed -- your opponent can still move. You simply <strong>pass</strong>:
no piece placed, no count incremented, and it becomes the other
player's turn, still consuming one level of the search. Only when
<em>neither</em> orientation has a move anywhere does the game actually
end. A plain empty board can reach this the very first time either side
runs low on room, so this isn\'t a rare edge case to special-case away --
it needs to be part of the ordinary recursive step.</p>
""",
    examples="""
>>> g = create_scoring_dominoes_game(2, 2)
>>> g.get_best_move(True, 3)
((0, 0), 1, 2)
""",
    starter=SCORING_GIVEN + """

    def get_best_move(self, vertical, limit):
        pass
""",
    hints=[
        "You need to carry (board, my_pieces, opp_pieces) as one bundle "
        "through the whole recursion -- not just a board. The simplest "
        "way is to pass my_pieces and opp_pieces as extra parameters "
        "alongside game/depth in both helpers, incrementing the right "
        "one by 1 every time perform_move is actually called.",
        "Base case: if game.is_jammed(): compare my_pieces to "
        "opp_pieces directly (1 if greater, -1 if less, 0 if equal) -- "
        "not evaluate() on the board, since the board alone can't tell "
        "you who placed more pieces to reach it. If depth == 0 and the "
        "game isn't jammed, return 0 -- there's nothing else safe to "
        "guess.",
        "Before looping: collect this player's legal_moves(vert_flag) "
        "into a list. If it's empty but is_jammed() was already False, "
        "this player must pass -- recurse straight into the other "
        "helper with the same board and the same piece counts, "
        "depth - 1, and return whatever that call returns (with move = "
        "None). Only build the ordinary max/min loop when there's at "
        "least one real move.",
        "Structure is otherwise ordinary alpha-beta: max_value(game, "
        "vert_flag, my_pieces, opp_pieces, alpha, beta, depth) recurses "
        "into min_value with my_pieces + 1 (you just placed a piece) and "
        "opp_pieces unchanged; min_value recurses into max_value with "
        "opp_pieces + 1 and my_pieces unchanged. Everything else -- the "
        "alpha/beta updates, the cutoff checks, the leaf count -- is "
        "identical to the homework's.",
    ],
    solution=SCORING_GIVEN + """

    def get_best_move(self, vertical, limit):

        def max_value(game, vert_flag, mine, theirs, alpha, beta, depth):
            if game.is_jammed():
                return (1 if mine > theirs else -1 if mine < theirs else 0,
                        None, 1)
            if depth == 0:
                return 0, None, 1
            moves = list(game.legal_moves(vert_flag))
            if not moves:
                v2, _, l2 = min_value(game, not vert_flag, mine, theirs,
                                      alpha, beta, depth - 1)
                return v2, None, l2
            value, move, leaves = float('-inf'), None, 0
            for row, col in moves:
                child = ScoringDominoesGame(
                    [r[:] for r in game.board], game.my_pieces,
                    game.opp_pieces)
                child.perform_move(row, col, vert_flag)
                v2, _, l2 = min_value(child, not vert_flag, mine + 1,
                                      theirs, alpha, beta, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, (row, col)
                alpha = max(alpha, value)
                if value >= beta:
                    return value, move, leaves
            return value, move, leaves

        def min_value(game, vert_flag, mine, theirs, alpha, beta, depth):
            if game.is_jammed():
                return (1 if mine > theirs else -1 if mine < theirs else 0,
                        None, 1)
            if depth == 0:
                return 0, None, 1
            moves = list(game.legal_moves(vert_flag))
            if not moves:
                v2, _, l2 = max_value(game, not vert_flag, mine, theirs,
                                      alpha, beta, depth - 1)
                return v2, None, l2
            value, move, leaves = float('inf'), None, 0
            for row, col in moves:
                child = ScoringDominoesGame(
                    [r[:] for r in game.board], game.my_pieces,
                    game.opp_pieces)
                child.perform_move(row, col, vert_flag)
                v2, _, l2 = max_value(child, not vert_flag, mine,
                                      theirs + 1, alpha, beta, depth - 1)
                leaves += l2
                if v2 < value:
                    value, move = v2, (row, col)
                beta = min(beta, value)
                if value <= alpha:
                    return value, move, leaves
            return value, move, leaves

        value, move, leaves = max_value(self, vertical, 0, 0,
                                        float('-inf'), float('inf'), limit)
        return move, value, leaves
""",
    tests=[
        T("is_jammed is False whenever either orientation still has a move", """
assert ScoringDominoesGame([[False]*3 for _ in range(3)], 0, 0).is_jammed() is False
checkerboard = ScoringDominoesGame(
    [[False, True], [True, False]], 0, 0)
assert checkerboard.is_jammed() is True
"""),
        T("returns a (move, value, leaves) tuple and never mutates the board", """
board = [[False] * 2 for _ in range(2)]
game = ScoringDominoesGame(board, 0, 0)
got = game.get_best_move(True, 2)
assert isinstance(got, tuple) and len(got) == 3, got
assert board == [[False] * 2 for _ in range(2)], "get_best_move changed the board"
"""),
        T("the worked example: a full game to a jammed board", """
got = create_scoring_dominoes_game(2, 2).get_best_move(True, 3)
assert got == ((0, 0), 1, 2), got
"""),
        T("get_best_move: scoring the board directly, ignoring piece counts, misses the point", """
board, vertical, limit, want, mistakes = @@CASE@@
game = ScoringDominoesGame([r[:] for r in board], 0, 0)
got = game.get_best_move(vertical, limit)
if got != want:
    for name, output in mistakes:
        if got == output:
            raise AssertionError(
                "%r: matches a known alpha-beta mistake (%s) -- double "
                "check the cutoff logic itself, separately from the "
                "piece-count bookkeeping" % (got, name))
assert got == want, (got, want)
""", CASE=SC_MISTAKE_CASE),
        T("get_best_move across boards, players and limits", """
CASES = @@CASES@@
MESSAGES = {
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later move -- replace the move only on >",
    "deeper": "searched one move deeper than the limit",
}
for board, vertical, limit, want, mistakes in CASES:
    game = ScoringDominoesGame([r[:] for r in board], 0, 0)
    got = game.get_best_move(vertical, limit)
    assert game.get_board() == board
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("vertical=%s limit=%d on %r: got %r, %s"
                                     % (vertical, limit, board, got,
                                        MESSAGES[name]))
    assert got == want, (board, vertical, limit, got, want)
""", CASES=SC_CASES),
    ],
)


# --- Free-Orientation Triominoes: combining two earlier variant ideas ---

def ft_legal(board, r, c, vertical):
    rows, cols = len(board), len(board[0])
    cells = [(r + i, c) if vertical else (r, c + i) for i in range(3)]
    return all(0 <= rr < rows and 0 <= cc < cols and not board[rr][cc]
               for rr, cc in cells)


def ft_moves(board):
    rows, cols = len(board), len(board[0])
    moves = []
    for r in range(rows):
        for c in range(cols):
            if ft_legal(board, r, c, True):
                moves.append((r, c, True))
            if ft_legal(board, r, c, False):
                moves.append((r, c, False))
    return moves


def ft_after(board, move):
    r, c, vertical = move
    new = [row[:] for row in board]
    for rr, cc in ([(r + i, c) for i in range(3)] if vertical
                   else [(r, c + i) for i in range(3)]):
        new[rr][cc] = True
    return new


def ft_best(board, limit, bug=None):
    def children(state, maxing):
        return [(m, ft_after(state, m)) for m in ft_moves(state)]

    def evaluate(state, maxing):
        if bug == "flat_formula":
            return 0
        if not ft_moves(state):
            if bug == "always_neg":
                return -1
            return -1 if maxing else 1
        return 0

    search_bug = None if bug in ("flat_formula", "always_neg") else bug
    return game_search(board, children, evaluate, limit, search_bug)


FT_MISTAKES = ("flat_formula", "always_neg", "no_window", "strict_cut",
              "ties_last")
FT_BOARDS = [
    [[FS] * 3 for _ in range(3)],
    [[FS] * 4 for _ in range(3)],
    [[XS, FS, FS, FS], [FS, FS, FS, FS], [FS, FS, FS, XS]],
]


def ft_case(board, limit):
    want = ft_best(board, limit)
    mistakes = [(bug, ft_best(board, limit, bug)) for bug in FT_MISTAKES]
    return (board, limit, want, [(n, o) for n, o in mistakes if o != want])


FT_CASES = [ft_case(b, k) for b in FT_BOARDS for k in (1, 2, 3)]
FT_MISTAKE_CASE = next(c for c in FT_CASES
                       if dict(c[3]).get("flat_formula") is not None)

FT_SOLUTION = '''
def create_free_triominoes_game(rows, cols):
    return FreeTriominoesGame([[False] * cols for _ in range(rows)])


class FreeTriominoesGame(object):

    def __init__(self, board):
        self.board = board
        self.rows = len(board)
        self.cols = len(board[0])

    def get_board(self):
        return self.board

    def cells(self, row, col, vertical):
        if vertical:
            return [(row + i, col) for i in range(3)]
        return [(row, col + i) for i in range(3)]

    def is_legal_move(self, row, col, vertical):
        for r, c in self.cells(row, col, vertical):
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return False
            if self.board[r][c]:
                return False
        return True

    def legal_moves(self):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_legal_move(row, col, True):
                    yield (row, col, True)
                if self.is_legal_move(row, col, False):
                    yield (row, col, False)

    def perform_move(self, row, col, vertical):
        for r, c in self.cells(row, col, vertical):
            self.board[r][c] = True

    def game_over(self):
        return next(self.legal_moves(), None) is None

    def copy(self):
        return FreeTriominoesGame([row[:] for row in self.board])

    def successors(self):
        for row, col, vertical in self.legal_moves():
            child = self.copy()
            child.perform_move(row, col, vertical)
            yield (row, col, vertical), child

    def get_best_move(self, limit):

        def max_value(game, alpha, beta, depth):
            if game.game_over():
                return -1, None, 1
            if depth == 0:
                return 0, None, 1
            value, move, leaves = float('-inf'), None, 0
            for mod_move, mod_game in game.successors():
                v2, _, l2 = min_value(mod_game, alpha, beta, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, mod_move
                alpha = max(alpha, value)
                if value >= beta:
                    return value, move, leaves
            return value, move, leaves

        def min_value(game, alpha, beta, depth):
            if game.game_over():
                return 1, None, 1
            if depth == 0:
                return 0, None, 1
            value, move, leaves = float('inf'), None, 0
            for mod_move, mod_game in game.successors():
                v2, _, l2 = max_value(mod_game, alpha, beta, depth - 1)
                leaves += l2
                if v2 < value:
                    value, move = v2, mod_move
                beta = min(beta, value)
                if value <= alpha:
                    return value, move, leaves
            return value, move, leaves

        value, move, leaves = max_value(self, float('-inf'), float('inf'),
                                        limit)
        return move, value, leaves
'''

problem(
    id="free-triominoes-game",
    track="Alpha-Beta, Homework-Style II",
    title="Triominoes, With Nobody Owning an Orientation Either",
    difficulty="hard",
    points=30,
    blurb="1x3 pieces plus no fixed roles at once -- the two variant dimensions from earlier problems, stacked on top of each other.",
    statement="""
<p>Combine both twists you've already worked through separately: pieces
are <code>1&times;3</code>, and nobody is locked into vertical or
horizontal -- anyone may place either way on their turn, every turn.</p>

<p>Nothing about either half of this is new. The bounds-and-empty check
needs the triominoes' three-cell reach; the evaluation needs the
free-orientation problem's insight that "my moves minus theirs" is
useless when both players share one <code>legal_moves()</code>, so
<code>get_best_move(limit)</code> needs the same win/loss-at-the-horizon
scoring as before -- <code>-1</code> for a MAX node with no moves,
<code>+1</code> for a MIN node with none, <code>0</code> at the depth
limit. The only real work here is recognizing that the two variations
don't interact at all: each piece of the class only cares about one of
them.</p>
""",
    examples="""
>>> g = create_free_triominoes_game(3, 3)
>>> sorted(g.legal_moves())[:2]
[(0, 0, False), (0, 0, True)]
>>> create_free_triominoes_game(3, 3).get_best_move(1)
((0, 0, True), 0, 6)
""",
    starter="""
def create_free_triominoes_game(rows, cols):
    pass


class FreeTriominoesGame(object):

    def __init__(self, board):
        pass

    def get_board(self):
        pass

    def cells(self, row, col, vertical):
        pass

    def is_legal_move(self, row, col, vertical):
        pass

    def legal_moves(self):
        pass

    def perform_move(self, row, col, vertical):
        pass

    def game_over(self):
        pass

    def copy(self):
        pass

    def successors(self):
        pass

    def get_best_move(self, limit):
        pass
""",
    hints=[
        "is_legal_move and cells(): copy directly from the triominoes-"
        "game problem -- this half of the class hasn't changed at all.",
        "legal_moves() and game_over(): copy directly from "
        "free-dominoes-game, just yielding a third element (the "
        "orientation) since there's no longer a single fixed orientation "
        "per call.",
        "get_best_move(limit): identical structure to "
        "free-dominoes-game's -- no vertical parameter anywhere, "
        "terminal values are still +-1 by which side has no move, depth "
        "== 0 with the game still going is still 0.",
    ],
    solution=FT_SOLUTION,
    tests=[
        T("stores the board and creates empty boards of any shape", """
board = [[False, True], [False, False]]
assert FreeTriominoesGame(board).get_board() is board
assert create_free_triominoes_game(2, 4).get_board() == [[False]*4]*2
"""),
        T("legal_moves yields both orientations, row-major, vertical before horizontal", """
CASES = @@CASES@@
for board, want in CASES:
    got = list(FreeTriominoesGame([r[:] for r in board]).legal_moves())
    assert got == want, (board, got, want)
""", CASES=[(b, ft_moves(b)) for b in FT_BOARDS[:2]]),
        T("perform_move fills three cells and game_over checks both orientations", """
board = [[False] * 4 for _ in range(3)]
game = FreeTriominoesGame(board)
assert game.perform_move(0, 0, False) is None
assert board == [[True]*3 + [False], [False]*4, [False]*4]
assert FreeTriominoesGame([[True]]).game_over() is True
"""),
        T("copy is independent and successors never touch the original", """
original = FreeTriominoesGame([[False] * 4 for _ in range(3)])
twin = original.copy()
assert all(a is not b for a, b in zip(twin.get_board(), original.get_board()))
list(original.successors())
assert original.get_board() == [[False] * 4 for _ in range(3)]
"""),
        T("get_best_move: the homework's per-orientation formula doesn't apply here either", """
board, limit, want, mistakes = @@CASE@@
got = FreeTriominoesGame([r[:] for r in board]).get_best_move(limit)
if got != want and got == dict(mistakes).get("flat_formula"):
    raise AssertionError(
        "%r: both players share legal_moves() here -- a move-count "
        "difference is always 0. Score wins and losses at the horizon "
        "instead." % (got,))
assert got == want, (got, want)
""", CASE=FT_MISTAKE_CASE),
        T("get_best_move across boards and limits", """
CASES = @@CASES@@
MESSAGES = {
    "flat_formula": "scored with a move-count-difference formula, "
                    "which is always 0 here",
    "always_neg": "an empty legal_moves() is scored -1 whoever is to move",
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later move -- replace the move only on >",
}
for board, limit, want, mistakes in CASES:
    game = FreeTriominoesGame([r[:] for r in board])
    got = game.get_best_move(limit)
    assert game.get_board() == board
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("limit %d on %r: got %r, %s"
                                     % (limit, board, got, MESSAGES[name]))
    assert got == want, (board, limit, got, want)
""", CASES=FT_CASES),
    ],
)


TRACKS = [
    ("Expectimax Basics",
     "Chance nodes average instead of minimizing -- the same recursive "
     "shape as minimax, one word changed."),
    ("Alpha-Beta Basics II",
     "New angles on figure 5.7: every node visited, cutoffs counted, "
     "one function instead of two, and searching depth by depth."),
    ("Expectimax, Homework-Style",
     "get_best_move's exact shape, against an opponent who isn't "
     "actually your adversary -- plus a game built on real dice."),
    ("Alpha-Beta, Homework-Style II",
     "Four more DominoesGame-shaped variants: new piece shapes, a new "
     "cell state, a new win condition, and two variations stacked."),
]


def run_tests(source, tests):
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
        print("%s %-24s %2d tests  %5.2fs" %
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
