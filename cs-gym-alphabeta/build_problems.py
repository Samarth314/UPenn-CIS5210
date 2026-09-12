"""Build the CS Gym (Game Trees & Alpha-Beta) problem bank.

Same contract as the other gyms: every problem carries a reference solution
and a test suite, and this script runs each reference solution against its
own tests before emitting problems.json, so a broken problem can never reach
the site.  Anything a test depends on that is itself a search result --
minimax values, leaf counts, the exact leaves alpha-beta evaluates -- is
computed by the oracles below and spliced into the test source through
``@@NAME@@`` markers rather than being worked out by hand.
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
    """A single test.  ``@@NAME@@`` markers are replaced by build-time constants."""
    for key, value in consts.items():
        marker = "@@%s@@" % key
        assert marker in src, "unused constant %s in test %r" % (key, name)
        src = src.replace(marker, repr(value))
    assert "@@" not in src, "unresolved constant in test %r" % name
    return {"name": name, "src": src.strip("\n")}


# Every tree problem hands out the same Node class.  It sits in the starter so
# you can experiment with it, and it is repeated at the top of each tree test
# so the test still runs if you have edited or deleted your own copy.
NODE_SRC = '''
class Node(object):

    def __init__(self, value=None, children=None):
        self.value = value
        self.children = children if children is not None else []

    def is_leaf(self):
        return len(self.children) == 0


def build(spec):
    """7 -> a leaf, [a, b] -> a node with children, (h, [a, b]) -> the
    same node carrying value h, a heuristic estimate of that position."""
    if isinstance(spec, tuple):
        return Node(spec[0], [build(child) for child in spec[1]])
    if isinstance(spec, list):
        return Node(None, [build(child) for child in spec])
    return Node(spec)
'''.strip("\n")

# A Node that writes down every leaf whose value gets read, so a test can see
# exactly which leaves a search evaluated instead of trusting a count.
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


def TN(name, src, tracked=False, **consts):
    """A tree test: the Node helpers are prepended so it stands alone."""
    head = NODE_SRC + ("\n\n\n" + TRACKED_SRC if tracked else "")
    return T(name, head + "\n\n\n" + src.strip("\n"), **consts)


# --------------------------------------------------------------------------
# Oracles.  They work on plain nested specs, never on Node objects, so nothing
# a learner writes can leak into an expected answer.
# --------------------------------------------------------------------------

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


def leaf_paths(spec, path=()):
    if not kids(spec):
        return [path]
    return [p for i, child in enumerate(kids(spec))
            for p in leaf_paths(child, path + (i,))]


def random_tree(rng, depth, heuristic=False):
    """Uneven random trees: branching 1-3, leaves sometimes stop early."""
    if depth == 0 or (depth < 3 and rng.random() < 0.3):
        return rng.randint(-9, 20)
    children = [random_tree(rng, depth - 1, heuristic)
                for _ in range(rng.randint(1, 3))]
    return (rng.randint(-9, 20), children) if heuristic else children


def alphabeta(spec, limit=None, maximizing=True, bug=None):
    """Figure 5.7, with an optional depth limit.

    Returns (move, value, leaves, visited): visited is the path of every node
    evaluated, in order.  `bug` reproduces a common mistake so the tests can
    recognise it by its output:
        "no_window"   alpha and beta never updated -- plain minimax
        "strict_cut"  cutting off on v > beta / v < alpha, not >= / <=
        "ties_last"   replacing the best move on an equal value too
    """
    visited = []

    def go(node, alpha, beta, maxing, depth, path):
        if not kids(node) or depth == 0:
            visited.append(path)
            return val(node), None, 1
        value = -INF if maxing else INF
        move, leaves = None, 0
        for i, child in enumerate(kids(node)):
            nxt = None if depth is None else depth - 1
            v2, _, l2 = go(child, alpha, beta, not maxing, nxt, path + (i,))
            leaves += l2
            if (v2 > value) if maxing else (v2 < value):
                value, move = v2, i
            elif bug == "ties_last" and v2 == value:
                move = i
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

    value, move, leaves = go(spec, -INF, INF, maximizing, limit, ())
    return move, value, leaves, visited


def minimax(spec, limit=None, maximizing=True):
    move, value, leaves, _ = alphabeta(spec, limit, maximizing, "no_window")
    return move, value, leaves


def draw(spec, levels=False):
    """A picture of a tree with each child's index; levels marks MAX/MIN."""
    def label(node, depth):
        if not kids(node):
            return str(val(node))
        kind = ("MAX" if depth % 2 == 0 else "MIN") if levels else "*"
        return kind if val(node) is None else "%s  h=%s" % (kind, val(node))

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


def picture(spec, levels=False):
    return '<pre class="block">%s</pre>' % draw(spec, levels)


def trace(spec, limit=None):
    """Figure 5.7 narrated one step at a time, for the tracing solutions."""
    lines = []

    def show(x):
        return {INF: "+inf", -INF: "-inf"}.get(x, str(x))

    def name(path):
        return "root" if not path else "".join("[%d]" % i for i in path)

    def go(node, alpha, beta, maxing, depth, path):
        pad = "  " * len(path)
        if not kids(node):
            lines.append("%s%s leaf %s" % (pad, name(path), val(node)))
            return val(node)
        if depth == 0:
            lines.append("%s%s depth limit, h = %s"
                         % (pad, name(path), val(node)))
            return val(node)
        lines.append("%s%s %s  alpha=%s beta=%s"
                     % (pad, name(path), "MAX" if maxing else "MIN",
                        show(alpha), show(beta)))
        value = -INF if maxing else INF
        children = kids(node)
        for i, child in enumerate(children):
            nxt = None if depth is None else depth - 1
            v2 = go(child, alpha, beta, not maxing, nxt, path + (i,))
            if maxing:
                value = max(value, v2)
                alpha = max(alpha, value)
                cut = value >= beta
                test = "v=%s >= beta=%s" % (show(value), show(beta))
                note = "v=%s alpha=%s" % (show(value), show(alpha))
            else:
                value = min(value, v2)
                beta = min(beta, value)
                cut = value <= alpha
                test = "v=%s <= alpha=%s" % (show(value), show(alpha))
                note = "v=%s beta=%s" % (show(value), show(beta))
            rest = range(i + 1, len(children))
            if cut and rest:
                skipped = ", ".join(name(path + (j,)) for j in rest)
                if limit is None:
                    skipped += " (leaves %s)" % ", ".join(
                        str(v) for j in rest for v in leaves_of(children[j]))
                lines.append("%s  %s -> prune %s" % (pad, test, skipped))
                break
            lines.append("%s  %s" % (pad, note))
        lines.append("%s%s returns %s" % (pad, name(path), show(value)))
        return value

    go(spec, -INF, INF, True, limit, ())
    return lines


# --------------------------------------------------------------------------
# Track 1 -- recursion on trees: the shapes every game-tree search is built on
# --------------------------------------------------------------------------

def with_nodes(code):
    """Starter or solution source with the shared Node helpers on top."""
    return NODE_SRC + "\n\n\n" + code.strip("\n") + "\n"


FIG52 = [[3, 12, 8], [2, 4, 6], [14, 5, 2]]
UNEVEN = [1, [2, 3], [[4], 5, [6, [7, 8]]]]
FRONTIER_TREE = [[1, 2], [3, [4, 5]], 6]


def o_count_nodes(spec):
    return 1 + sum(o_count_nodes(child) for child in kids(spec))


def o_height(spec):
    if not kids(spec):
        return 0
    return 1 + max(o_height(child) for child in kids(spec))


def o_frontier(spec, limit):
    if limit == 0 or not kids(spec):
        return 1
    return sum(o_frontier(child, limit - 1) for child in kids(spec))


def o_max_path(spec):
    paths = leaf_paths(spec)
    best = max(val(at(spec, p)) for p in paths)
    return list(next(p for p in paths if val(at(spec, p)) == best))


_rng = random.Random(5210)
RANDOM_PLAIN = [random_tree(_rng, 5) for _ in range(30)]
RANDOM_HEURISTIC = [random_tree(_rng, 5, heuristic=True) for _ in range(30)]


problem(
    id="nodes-and-leaves",
    track="Recursion on Trees",
    title="Counting Nodes, Counting Leaves",
    difficulty="warmup",
    points=5,
    blurb="Two functions that look identical until you ask where the base case goes.",
    statement="""
<p>Every problem in this gym walks a tree of <code>Node</code> objects. A node
has a <code>value</code> and a list of <code>children</code>, left to right. A
<em>leaf</em> is a node whose list is empty. The starter defines
<code>Node</code>, plus <code>build</code>, which turns nested lists into nodes
so trees are quick to write:</p>

<pre class="block">build(7)              a leaf holding 7
build([3, 12, 8])     a node with three leaf children
build([[3, 12], 8])   a node whose first child has children of its own</pre>

<p>Write <code>count_nodes(node)</code>, the number of nodes in the whole tree
including the root, and <code>count_leaves(node)</code>, the number of
leaves.</p>

<p>They look nearly identical, and the difference between them is the lesson.
<code>count_nodes</code> barely needs a base case: a leaf's loop over zero
children adds nothing, so <code>1 + sum(...)</code> already returns 1.
<code>count_leaves</code> can't work that way, because an interior node must
contribute nothing for itself &mdash; it needs an explicit leaf check.</p>
""",
    examples="""
>>> count_nodes(build([3, 12, 8]))
4
>>> count_leaves(build([3, 12, 8]))
3
>>> count_nodes(build([[3, 12], 8]))
5
>>> count_leaves(build(7))
1
""",
    starter=with_nodes("""
def count_nodes(node):
    pass


def count_leaves(node):
    pass
"""),
    hints=[
        "Trust the recursion: assume count_nodes already works on each "
        "child, then ask how this node's answer follows from theirs.",
        "count_nodes(node) is 1 for the node itself plus count_nodes(child) "
        "summed over node.children. A leaf has no children, so that same "
        "line returns 1 without any special case.",
        "count_leaves needs the explicit base case: if node.is_leaf(), "
        "return 1. Otherwise return the sum over the children with no + 1, "
        "because an interior node is not a leaf.",
    ],
    solution=with_nodes("""
def count_nodes(node):
    return 1 + sum(count_nodes(child) for child in node.children)


def count_leaves(node):
    if node.is_leaf():
        return 1
    return sum(count_leaves(child) for child in node.children)
"""),
    tests=[
        TN("a single leaf is one node and one leaf", """
assert count_nodes(build(7)) == 1
assert count_leaves(build(7)) == 1
"""),
        TN("the textbook's figure 5.2 tree", """
tree = build(@@FIG@@)
assert count_nodes(tree) == 13, count_nodes(tree)
assert count_leaves(tree) == 9, count_leaves(tree)
""", FIG=FIG52),
        TN("uneven depths", """
tree = build(@@TREE@@)
assert count_nodes(tree) == @@NODES@@, count_nodes(tree)
assert count_leaves(tree) == @@LEAVES@@, count_leaves(tree)
""", TREE=UNEVEN, NODES=o_count_nodes(UNEVEN),
           LEAVES=len(leaves_of(UNEVEN))),
        TN("an interior node is never counted as a leaf", """
# A chain: every node but the last has exactly one child.
chain = build([[[[5]]]])
assert count_nodes(chain) == 5, count_nodes(chain)
assert count_leaves(chain) == 1, count_leaves(chain)
"""),
        TN("random trees, checked against a direct count", """
TREES = @@TREES@@
NODES = @@NODES@@
LEAVES = @@LEAVES@@
for spec, nodes, leaves in zip(TREES, NODES, LEAVES):
    tree = build(spec)
    assert count_nodes(tree) == nodes, (spec, count_nodes(tree), nodes)
    assert count_leaves(tree) == leaves, (spec, count_leaves(tree), leaves)
""", TREES=RANDOM_PLAIN, NODES=[o_count_nodes(t) for t in RANDOM_PLAIN],
           LEAVES=[len(leaves_of(t)) for t in RANDOM_PLAIN]),
    ],
)


problem(
    id="height-and-max-leaf",
    track="Recursion on Trees",
    title="How Deep It Goes, and What It Holds",
    difficulty="easy",
    points=10,
    blurb="max() over the children is a MAX node in disguise -- and a leaf has no children.",
    statement="""
<p>Write <code>height(node)</code>: the number of <strong>edges</strong> on
the longest path from <code>node</code> down to a leaf. A leaf has height
0.</p>

<p>Then write <code>max_leaf(node)</code>: the largest value held by any
<strong>leaf</strong> in the tree.</p>

<p>Both come down to <code>max(...)</code> over the children, which is a MAX
node from minimax in disguise. Both also need a real base case, because
<code>max()</code> of an empty sequence raises <code>ValueError</code> &mdash;
and a leaf has no children to take the maximum over.</p>

<p>One trap in <code>max_leaf</code>: some trees give interior nodes a value
too, written <code>(h, [children])</code>. Later problems use that as a
heuristic estimate. Here it must be ignored entirely &mdash; only leaves
count. Leaves can also be negative, so a running maximum that starts at 0 is
wrong.</p>
""",
    examples="""
>>> height(build(7))
0
>>> height(build([[3, 12], 8]))
2
>>> max_leaf(build([[3, 12], 8]))
12
>>> max_leaf(build((99, [4, (50, [8, 1])])))
8
""",
    starter=with_nodes("""
def height(node):
    pass


def max_leaf(node):
    pass
"""),
    hints=[
        "height: a leaf is 0. Anything else sits one edge above its tallest "
        "child, so it is 1 plus the largest child height.",
        "Check node.is_leaf() before calling max(). max() over an empty "
        "generator raises ValueError, which is exactly what happens when a "
        "leaf falls through to the recursive case.",
        "max_leaf never reads node.value on an interior node: return "
        "node.value at a leaf, and the max over max_leaf(child) everywhere "
        "else. If you keep a running best instead, start it at "
        "float('-inf'), never 0.",
    ],
    solution=with_nodes("""
def height(node):
    if node.is_leaf():
        return 0
    return 1 + max(height(child) for child in node.children)


def max_leaf(node):
    if node.is_leaf():
        return node.value
    return max(max_leaf(child) for child in node.children)
"""),
    tests=[
        TN("a leaf has height 0 and is its own maximum", """
assert height(build(7)) == 0
assert max_leaf(build(7)) == 7
assert max_leaf(build(-4)) == -4
"""),
        TN("the textbook's figure 5.2 tree", """
tree = build(@@FIG@@)
assert height(tree) == 2, height(tree)
assert max_leaf(tree) == 14, max_leaf(tree)
""", FIG=FIG52),
        TN("the longest path decides, wherever it is", """
# The deepest leaf hangs off the last child, then off the first.
assert height(build([1, 2, [3, [4, [5]]]])) == 4
assert height(build([[[[5]]], 1, 2])) == 4
"""),
        TN("interior values are not leaves", """
tree = build((99, [4, (50, [8, 1])]))
assert max_leaf(tree) == 8, max_leaf(tree)
"""),
        TN("all the leaves are negative", """
tree = build([[-5, -2], [-9, [-1, -3]]])
assert max_leaf(tree) == -1, max_leaf(tree)
"""),
        TN("random trees with a value on every interior node", """
TREES = @@TREES@@
HEIGHTS = @@HEIGHTS@@
MAXES = @@MAXES@@
for spec, h, m in zip(TREES, HEIGHTS, MAXES):
    tree = build(spec)
    assert height(tree) == h, (spec, height(tree), h)
    assert max_leaf(tree) == m, (spec, max_leaf(tree), m)
""", TREES=RANDOM_HEURISTIC, HEIGHTS=[o_height(t) for t in RANDOM_HEURISTIC],
           MAXES=[max(leaves_of(t)) for t in RANDOM_HEURISTIC]),
    ],
)


problem(
    id="iter-leaves",
    track="Recursion on Trees",
    title="Leaves, One at a Time",
    difficulty="easy",
    points=10,
    blurb="A recursive generator -- the shape of legal_moves() and successors().",
    statement="""
<p>Write <code>iter_leaves(node)</code> as a <strong>generator</strong> that
yields the value of every leaf, left to right.</p>

<p>This is the shape of <code>legal_moves()</code> and
<code>successors()</code> in the homework. Callers consume it lazily, and a
search that stops early never pays for what it didn't ask for. So beyond the
order, the tests check that calling <code>iter_leaves</code> returns a
generator, and that asking for the first leaf does not walk the rest of the
tree.</p>

<p>The recursive step is where this goes wrong. Calling
<code>iter_leaves(child)</code> on a line by itself just creates a generator
object and throws it away &mdash; nothing is yielded. You need
<code>yield from</code>.</p>
""",
    examples="""
>>> list(iter_leaves(build([[3, 12], 8, [[1]]])))
[3, 12, 8, 1]
>>> gen = iter_leaves(build([5, [6, 7]]))
>>> next(gen)
5
>>> next(gen)
6
""",
    starter=with_nodes("""
def iter_leaves(node):
    pass
"""),
    hints=[
        "Use yield, and never build and return a list. A function with "
        "yield anywhere in its body is a generator, even on paths that "
        "never reach it.",
        "At a leaf, yield node.value. At an interior node, loop over the "
        "children and pass along everything each child's generator yields.",
        "yield from iter_leaves(child) forwards every value the child "
        "produces. Without it, iter_leaves(child) creates a generator that "
        "nothing ever iterates, and your function yields nothing below the "
        "root.",
    ],
    solution=with_nodes("""
def iter_leaves(node):
    if node.is_leaf():
        yield node.value
    else:
        for child in node.children:
            yield from iter_leaves(child)
"""),
    tests=[
        TN("calling it returns a generator", """
import inspect
result = iter_leaves(build([1, 2]))
assert inspect.isgenerator(result), (
    "iter_leaves returned %s -- use yield, not return"
    % type(result).__name__)
"""),
        TN("left to right on figure 5.2", """
assert list(iter_leaves(build(@@FIG@@))) == @@LEAVES@@
""", FIG=FIG52, LEAVES=leaves_of(FIG52)),
        TN("uneven depths, and a lone leaf", """
assert list(iter_leaves(build(@@TREE@@))) == @@LEAVES@@
assert list(iter_leaves(build(7))) == [7]
""", TREE=UNEVEN, LEAVES=leaves_of(UNEVEN)),
        TN("the first leaf arrives without walking the rest of the tree", """
class Poisoned(list):

    def __iter__(self):
        raise AssertionError("the rest of the tree was walked before the "
                             "first leaf was requested -- yield as you go")


late = Node(None, Poisoned([Node(2), Node(3)]))
tree = Node(None, [Node(None, [Node(1)]), late])
assert next(iter_leaves(tree)) == 1
"""),
        TN("random trees, checked against a direct walk", """
TREES = @@TREES@@
LEAVES = @@LEAVES@@
for spec, want in zip(TREES, LEAVES):
    got = list(iter_leaves(build(spec)))
    assert got == want, (spec, got, want)
""", TREES=RANDOM_HEURISTIC, LEAVES=[leaves_of(t) for t in RANDOM_HEURISTIC]),
    ],
)


problem(
    id="path-to-best-leaf",
    track="Recursion on Trees",
    title="The Route to the Best Leaf",
    difficulty="medium",
    points=15,
    blurb="Return where the answer is, not just what it is -- with ties going to the leftmost.",
    statement="""
<p>Write <code>path_to_max_leaf(node)</code>, returning the route from
<code>node</code> down to its largest leaf as a list of child indices. In the
tree below the largest leaf is 14, reached by taking child 2 and then child
0, so the answer is <code>[2, 0]</code>. A leaf is already where it needs to
be, so its path is <code>[]</code>.</p>
""" + picture(FIG52) + """
<p>When several leaves share the largest value, return the path to the
<strong>leftmost</strong> one.</p>

<p>This is the <em>move</em> half of <code>get_best_move</code>. The value
alone is easy; the work is carrying the choice back up alongside it, and
breaking ties the way the homework does &mdash; only a
<strong>strictly</strong> better value replaces the current best, so the
first one found wins.</p>
""",
    examples="""
>>> path_to_max_leaf(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]))
[2, 0]
>>> path_to_max_leaf(build([5, [9, 2], [1, 9]]))
[1, 0]
>>> path_to_max_leaf(build(7))
[]
""",
    starter=with_nodes("""
def path_to_max_leaf(node):
    pass
"""),
    hints=[
        "Write a helper that returns two things for any subtree: its best "
        "leaf value and the path to that leaf. The public function returns "
        "only the path.",
        "At an interior node, loop with enumerate so you know each child's "
        "index. When child i reports (value, path), the path from here is "
        "[i] + path.",
        "Replace your best only when value > best -- strictly. With >=, a "
        "later tie overwrites the earlier one and you return the rightmost "
        "path instead.",
    ],
    solution=with_nodes("""
def path_to_max_leaf(node):

    def best(subtree):
        if subtree.is_leaf():
            return subtree.value, []
        best_value, best_path = None, None
        for i, child in enumerate(subtree.children):
            value, path = best(child)
            if best_value is None or value > best_value:
                best_value, best_path = value, [i] + path
        return best_value, best_path

    return best(node)[1]
"""),
    tests=[
        TN("a leaf's path is empty", """
assert path_to_max_leaf(build(7)) == []
"""),
        TN("the textbook's figure 5.2 tree", """
got = path_to_max_leaf(build(@@FIG@@))
assert got == [2, 0], got
""", FIG=FIG52),
        TN("ties go to the leftmost leaf", """
got = path_to_max_leaf(build([5, [9, 2], [1, 9]]))
assert got == [1, 0], "got %r -- a later tie replaced the first" % (got,)
got = path_to_max_leaf(build([[1, [7, 7]], [7]]))
assert got == [0, 1, 0], "got %r -- a later tie replaced the first" % (got,)
"""),
        TN("negative leaves", """
got = path_to_max_leaf(build([[-3, -8], [-1]]))
assert got == [1, 0], got
"""),
        TN("random trees whose interior values must be ignored", """
TREES = @@TREES@@
PATHS = @@PATHS@@
for spec, want in zip(TREES, PATHS):
    got = path_to_max_leaf(build(spec))
    assert got == want, (spec, got, want)
""", TREES=RANDOM_HEURISTIC, PATHS=[o_max_path(t) for t in RANDOM_HEURISTIC]),
    ],
)


problem(
    id="frontier-count",
    track="Recursion on Trees",
    title="Where a Depth Limit Stops",
    difficulty="medium",
    points=15,
    blurb="Count the nodes a depth-limited search evaluates: get_best_move's leaf count, unpruned.",
    statement="""
<p>A depth-limited search never looks more than <code>limit</code> moves
ahead. It stops at a node for one of two reasons: the limit is used up, or
the node is a real leaf with nowhere further to go. Every node where it stops
is evaluated once.</p>

<p>Write <code>count_frontier(node, limit)</code>, the number of nodes where
that search stops. The root is at depth 0, so a limit of 0 stops at the root
and the answer is 1. Nodes below a stopping point are never reached and don't
count.</p>
""" + picture(FRONTIER_TREE) + """
<p>For this tree a limit of 1 stops at the root's three children. A limit of
2 stops at five nodes: the leaves <code>1</code>, <code>2</code> and
<code>3</code>; the interior node <code>[1][1]</code>, cut off by the limit;
and the leaf <code>6</code>, which the search reached early.</p>

<p>This number is the <em>leaves</em> count from the homework with pruning
switched off. On the empty 3&times;3 dominoes board,
<code>get_best_move(True, 1)</code> reports 6: six vertical moves, each child
evaluated once.</p>
""",
    examples="""
>>> tree = build([[1, 2], [3, [4, 5]], 6])
>>> count_frontier(tree, 0)
1
>>> count_frontier(tree, 1)
3
>>> count_frontier(tree, 2)
5
>>> count_frontier(tree, 10)
6
""",
    starter=with_nodes("""
def count_frontier(node, limit):
    pass
"""),
    hints=[
        "Think of limit as moves remaining. Every step down a level uses "
        "one, so the recursive call passes limit - 1.",
        "Check the two stopping conditions first: limit == 0, or "
        "node.is_leaf(). Either way this node gets evaluated, so return 1.",
        "Otherwise the node itself is not evaluated: return the sum of "
        "count_frontier(child, limit - 1) over its children. Adding 1 for "
        "the interior node as well is the most common wrong answer here.",
    ],
    solution=with_nodes("""
def count_frontier(node, limit):
    if limit == 0 or node.is_leaf():
        return 1
    return sum(count_frontier(child, limit - 1) for child in node.children)
"""),
    tests=[
        TN("a limit of 0 stops at the root", """
assert count_frontier(build(@@FIG@@), 0) == 1
assert count_frontier(build(7), 0) == 1
""", FIG=FIG52),
        TN("the example tree at every limit", """
tree = build(@@TREE@@)
got = [count_frontier(tree, limit) for limit in range(5)]
assert got == @@WANT@@, got
""", TREE=FRONTIER_TREE, WANT=[o_frontier(FRONTIER_TREE, k) for k in range(5)]),
        TN("interior nodes above the limit are not counted", """
tree = build(@@FIG@@)
assert count_frontier(tree, 1) == 3, count_frontier(tree, 1)
assert count_frontier(tree, 2) == 9, count_frontier(tree, 2)
""", FIG=FIG52),
        TN("a limit past the bottom counts exactly the leaves", """
TREES = @@TREES@@
LEAVES = @@LEAVES@@
for spec, want in zip(TREES, LEAVES):
    got = count_frontier(build(spec), 50)
    assert got == want, (spec, got, want)
""", TREES=RANDOM_PLAIN, LEAVES=[len(leaves_of(t)) for t in RANDOM_PLAIN]),
        TN("random trees at limits 1 to 4", """
CASES = @@CASES@@
for spec, limit, want in CASES:
    got = count_frontier(build(spec), limit)
    assert got == want, (spec, limit, got, want)
""", CASES=[(t, k, o_frontier(t, k))
            for t in RANDOM_HEURISTIC[:15] for k in range(1, 5)]),
    ],
)


# --------------------------------------------------------------------------
# Track 2 -- minimax: alternating levels, then a horizon
# --------------------------------------------------------------------------

H_TREE = (0, [(4, [(2, [7, 1]), (9, [3, 8])]),
              (6, [(5, [2, 6]), (1, [9, 9])]),
              (3, [(8, [4, 5])])])

problem(
    id="minimax-value",
    track="Minimax",
    title="Whose Turn Is It at This Level?",
    difficulty="easy",
    points=10,
    blurb="The value of a game tree when both sides play perfectly, and the one-word flip that makes it work.",
    statement="""
<p>In a game tree the levels alternate between two players. MAX picks the
child with the largest value, MIN the smallest, and every leaf holds a score
from MAX's point of view. The <em>minimax value</em> of a node is what it's
worth when both sides play perfectly from there.</p>

<p>Write <code>minimax(node, maximizing)</code>. When
<code>maximizing</code> is <code>True</code> the node belongs to MAX, and its
children belong to MIN.</p>
""" + picture(FIG52, levels=True) + """
<p>This is figure 5.2 from the textbook. MIN's three nodes are worth 3, 2 and
2, so MAX at the root is worth 3.</p>

<p>The whole algorithm hangs on one flip: each recursive call passes
<code>not maximizing</code>. Leave it out and every level belongs to the same
player, and this tree comes out as 14.</p>
""",
    examples="""
>>> tree = build([[3, 12, 8], [2, 4, 6], [14, 5, 2]])
>>> minimax(tree, True)
3
>>> minimax(tree, False)
6
>>> minimax(build(5), True)
5
""",
    starter=with_nodes("""
def minimax(node, maximizing):
    pass
"""),
    hints=[
        "At a leaf, return node.value. It is already a score, whoever is "
        "to move.",
        "At an interior node, compute minimax(child, not maximizing) for "
        "every child, then take max() of them if maximizing, else min().",
        "If figure 5.2 gives you 14 you forgot to flip, so every level is "
        "MAX. If it gives 2 with maximizing=True, the flip is happening but "
        "max and min are the wrong way round.",
    ],
    solution=with_nodes("""
def minimax(node, maximizing):
    if node.is_leaf():
        return node.value
    values = [minimax(child, not maximizing) for child in node.children]
    return max(values) if maximizing else min(values)
"""),
    tests=[
        TN("a leaf is worth its own value to either player", """
assert minimax(build(5), True) == 5
assert minimax(build(5), False) == 5
"""),
        TN("figure 5.2 from both sides", """
tree = build(@@FIG@@)
got = minimax(tree, True)
assert got != 14, "14 means every level is MAX -- pass not maximizing down"
assert got == 3, got
assert minimax(tree, False) == 6, minimax(tree, False)
""", FIG=FIG52),
        TN("a chain of single children still alternates", """
# MAX -> MIN -> MAX -> MIN -> leaf: nobody has a choice to make.
assert minimax(build([[[[4]]]]), True) == 4
assert minimax(build([[[[4]]]]), False) == 4
assert minimax(build([[1, 9], [[2, 8]]]), True) == 8
"""),
        TN("random uneven trees with MAX and with MIN at the root", """
CASES = @@CASES@@
for spec, maximizing, want in CASES:
    got = minimax(build(spec), maximizing)
    assert got == want, (spec, maximizing, got, want)
""", CASES=[(t, m, minimax(t, None, m)[1])
            for t in RANDOM_PLAIN for m in (True, False)]),
    ],
)


problem(
    id="minimax-horizon",
    track="Minimax",
    title="The Best Move Changes With the Horizon",
    difficulty="medium",
    points=20,
    blurb="Depth-limited minimax returning (move, value, leaves) -- get_best_move without the pruning.",
    statement="""
<p>Real game trees are far too big to search to the bottom, so the search
stops after <code>limit</code> moves and asks a heuristic how good that
position looks. Here each interior node carries that estimate as its
<code>value</code>, written <code>(h, [children])</code>.</p>

<p>Write <code>minimax_decision(node, limit)</code> for MAX at the root. It
returns <code>(move, value, leaves)</code> &mdash; the same shape as
<code>get_best_move</code>:</p>

<ul>
  <li><code>move</code> &mdash; the index of the root child to play.</li>
  <li><code>value</code> &mdash; the minimax value of the root, where any
      node at depth <code>limit</code> is worth its <code>value</code>, and
      so is any leaf reached sooner.</li>
  <li><code>leaves</code> &mdash; how many nodes were evaluated that way.</li>
</ul>

<p>Break ties toward the leftmost child. There is no pruning yet; that comes
in the Alpha-Beta tracks.</p>
""" + picture(H_TREE, levels=True) + """
<p>Search this tree one move deep and the estimates say play child 1. Two
moves deep, child 2. All the way down, child 0. A deeper search sees
replies the shallow one couldn't, which is exactly why the limit matters
&mdash; and why a search that's accidentally one ply too deep or too shallow
returns a plausible-looking wrong move.</p>
""",
    examples="""
>>> tree = build((0, [(4, [(2, [7, 1]), (9, [3, 8])]),
...                   (6, [(5, [2, 6]), (1, [9, 9])]),
...                   (3, [(8, [4, 5])])]))
>>> minimax_decision(tree, 1)
(1, 6, 3)
>>> minimax_decision(tree, 2)
(2, 8, 5)
>>> minimax_decision(tree, 3)
(0, 7, 10)
""",
    starter=with_nodes("""
def minimax_decision(node, limit):
    pass
"""),
    hints=[
        "Write a helper search(subtree, maximizing, depth) that returns "
        "(value, move, leaves). Stop when depth == 0 or the subtree is a "
        "leaf, and return (subtree.value, None, 1) -- that one line covers "
        "both real leaves and positions cut off by the limit.",
        "Recurse with depth - 1 and not maximizing. Add every child's leaf "
        "count to your total, whether or not that child's value wins.",
        "Keep a child's index only when its value is strictly better (> for "
        "MAX, < for MIN). The recursive calls' moves are thrown away; only "
        "the root's is returned, reordered to (move, value, leaves).",
    ],
    solution=with_nodes("""
def minimax_decision(node, limit):

    def search(subtree, maximizing, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        best = float('-inf') if maximizing else float('inf')
        move, leaves = None, 0
        for i, child in enumerate(subtree.children):
            value, _, count = search(child, not maximizing, depth - 1)
            leaves += count
            if (value > best) if maximizing else (value < best):
                best, move = value, i
        return best, move, leaves

    value, move, leaves = search(node, True, limit)
    return move, value, leaves
"""),
    tests=[
        TN("returns a (move, value, leaves) tuple", """
got = minimax_decision(build([[3, 12, 8], [2, 4, 6]]), 2)
assert isinstance(got, tuple) and len(got) == 3, (
    "expected (move, value, leaves), got %r" % (got,))
"""),
        TN("figure 5.2 searched to the bottom", """
tree = build(@@FIG@@)
assert minimax_decision(tree, 2) == (0, 3, 9), minimax_decision(tree, 2)
assert minimax_decision(tree, 10) == (0, 3, 9), minimax_decision(tree, 10)
""", FIG=FIG52),
        TN("the horizon changes the decision", """
tree = build(@@TREE@@)
WANT = @@WANT@@
for limit in (1, 2, 3):
    got = minimax_decision(tree, limit)
    assert got == WANT[limit], (limit, got, WANT[limit])
""", TREE=H_TREE, WANT={k: minimax(H_TREE, k) for k in (1, 2, 3)}),
        TN("ties go to the leftmost child", """
got = minimax_decision(build([[5, 6], [7, 5], [5, 9]]), 2)
assert got == (0, 5, 6), got
"""),
        TN("random trees at limits 1 to 4, off-by-one limits flagged", """
CASES = @@CASES@@
for spec, limit, want, deeper, shallower in CASES:
    got = minimax_decision(build(spec), limit)
    if got != want and got == deeper:
        raise AssertionError("limit %d searched one move too deep: %r"
                             % (limit, got))
    if got != want and got == shallower:
        raise AssertionError("limit %d searched one move too shallow: %r"
                             % (limit, got))
    assert got == want, (spec, limit, got, want)
""", CASES=[(t, k, minimax(t, k), minimax(t, k + 1), minimax(t, k - 1))
            for t in RANDOM_HEURISTIC for k in range(1, 5)]),
    ],
)


# --------------------------------------------------------------------------
# Track 4 -- alpha-beta in code: figure 5.7, checked leaf by leaf
# --------------------------------------------------------------------------

EQUAL_EDGE = [[3, 5], [3, 9]]
DUPLICATES = [[3, 5], [2, 3]]

_rng = random.Random(1957)
RANDOM_AB = [random_tree(_rng, 5) for _ in range(40)]
RANDOM_AB_H = [random_tree(_rng, 5, heuristic=True) for _ in range(40)]


def o_pruned(spec):
    seen = set(alphabeta(spec)[3])
    return [val(at(spec, p)) for p in leaf_paths(spec) if p not in seen]


problem(
    id="alphabeta-prunes",
    track="Alpha-Beta in Code",
    title="Pruning You Can Actually See",
    difficulty="medium",
    points=15,
    blurb="Figure 5.7 as one function. The tests watch which leaves you read, so a search that never prunes fails.",
    statement="""
<p>Write <code>alphabeta(node, alpha, beta, maximizing)</code>, returning the
minimax value of <code>node</code> using alpha-beta pruning exactly as in
figure 5.7. The top-level call passes <code>float('-inf')</code> and
<code>float('inf')</code> for the window.</p>

<p>Getting the right number is not enough. A minimax that never prunes
returns the same value, so the tests hand you instrumented nodes that record
every leaf whose <code>value</code> you read, and they compare that set with
the leaves figure 5.7 evaluates. Skip one it needs, or read one it would
prune, and the test fails and tells you which.</p>

<p>The details that decide which leaves get read:</p>

<ul>
  <li>After each child, a MAX node raises <code>alpha</code> to its best
      value so far, and a MIN node lowers <code>beta</code>.</li>
  <li>MAX stops looking at its children once <code>v &gt;= beta</code>; MIN
      stops once <code>v &lt;= alpha</code>. Those are
      <strong>non-strict</strong>: an equal value prunes too.</li>
  <li>Read a leaf's <code>value</code> only when you evaluate it.</li>
</ul>
""",
    examples="""
>>> tree = build([[3, 12, 8], [2, 4, 6], [14, 5, 2]])
>>> alphabeta(tree, float('-inf'), float('inf'), True)
3
>>> alphabeta(tree, float('-inf'), float('inf'), False)
6
""",
    starter=with_nodes("""
def alphabeta(node, alpha, beta, maximizing):
    pass
"""),
    hints=[
        "Start from your minimax: same base case, same flip of maximizing. "
        "Then thread alpha and beta through every recursive call.",
        "In the MAX branch: v = max(v, alphabeta(child, alpha, beta, False)), "
        "then alpha = max(alpha, v), then return v if v >= beta. The MIN "
        "branch mirrors it with min, beta, and v <= alpha.",
        "If the value is right but the test says every leaf was read, the "
        "window never narrows -- usually a missing alpha/beta update, or "
        "updating a copy that the next child never sees.",
    ],
    solution=with_nodes("""
def alphabeta(node, alpha, beta, maximizing):
    if node.is_leaf():
        return node.value
    if maximizing:
        value = float('-inf')
        for child in node.children:
            value = max(value, alphabeta(child, alpha, beta, False))
            alpha = max(alpha, value)
            if value >= beta:
                return value
        return value
    value = float('inf')
    for child in node.children:
        value = min(value, alphabeta(child, alpha, beta, True))
        beta = min(beta, value)
        if value <= alpha:
            return value
    return value
"""),
    tests=[
        TN("figure 5.2 prunes exactly leaves [1][1] and [1][2]", """
log = []
got = alphabeta(build_tracked(@@FIG@@, log), float('-inf'), float('inf'),
                True)
assert got == 3, got
seen = set(log)
if (1, 1) in seen or (1, 2) in seen:
    raise AssertionError("read a leaf alpha-beta prunes: MIN node [1] should "
                         "stop at 2, since 2 <= alpha = 3")
assert seen == set(@@VISITED@@), sorted(seen)
""", tracked=True, FIG=FIG52, VISITED=alphabeta(FIG52)[3]),
        TN("an equal value prunes too", """
log = []
got = alphabeta(build_tracked(@@TREE@@, log), float('-inf'), float('inf'),
                True)
assert got == 3, got
assert (1, 1) not in set(log), (
    "leaf 9 was read: MIN node [1] reaches v = 3 <= alpha = 3 and must stop "
    "-- the cut-off comparison is <=, not <")
""", tracked=True, TREE=EQUAL_EDGE),
        TN("random trees with MAX and with MIN at the root", """
CASES = @@CASES@@
for spec, maximizing, want, visited, every, strict in CASES:
    log = []
    got = alphabeta(build_tracked(spec, log), float('-inf'), float('inf'),
                    maximizing)
    assert got == want, (spec, maximizing, got, want)
    seen = set(log)
    if seen == set(visited):
        continue
    if seen == set(every):
        raise AssertionError("right value, but every leaf was read -- update "
                             "alpha/beta after each child: %r" % (spec,))
    if seen == set(strict):
        raise AssertionError("cut-offs use < or > instead of <= and >=: %r"
                             % (spec,))
    raise AssertionError("wrong leaves on %r: skipped %r, read %r too" % (
        spec, sorted(set(visited) - seen), sorted(seen - set(visited))))
""", tracked=True, CASES=[
            (t, m, alphabeta(t, None, m)[1], alphabeta(t, None, m)[3],
             leaf_paths(t), alphabeta(t, None, m, "strict_cut")[3])
            for t in RANDOM_AB for m in (True, False)]),
    ],
)


problem(
    id="alphabeta-leaf-count",
    track="Alpha-Beta in Code",
    title="Counting What the Search Evaluated",
    difficulty="medium",
    points=20,
    blurb="Return (value, leaves) through every early return -- the bookkeeping get_best_move needs.",
    statement="""
<p>Write <code>alphabeta_count(node)</code> for MAX at the root. It returns
<code>(value, leaves)</code>: the minimax value, and how many leaves
alpha-beta evaluated to find it.</p>

<p>This is the third number <code>get_best_move</code> reports, and it's the
one that exposes a broken search. Value and move can both come out right
while pruning silently does nothing; the leaf count cannot.</p>

<p>Every call returns a pair now, including the early return on a cut-off.
A leaf is worth <code>(node.value, 1)</code>. An interior node adds up the
counts its children reported &mdash; and the children it never reached,
because it returned early, contribute nothing. That is the saving.</p>

<p>Figure 5.2 evaluates 7 of its 9 leaves. A search that reports 9 isn't
pruning; one that reports 1 or 0 isn't adding the children's counts up.</p>
""",
    examples="""
>>> alphabeta_count(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]))
(3, 7)
>>> alphabeta_count(build([[3, 5], [3, 9]]))
(3, 3)
>>> alphabeta_count(build(4))
(4, 1)
""",
    starter=with_nodes("""
def alphabeta_count(node):
    pass
"""),
    hints=[
        "Write max_value(subtree, alpha, beta) and min_value(subtree, alpha, "
        "beta) inside alphabeta_count, each returning (value, leaves).",
        "At a leaf return (subtree.value, 1). In the loop, unpack the child's "
        "pair and do leaves += child_leaves before the cut-off check, so the "
        "early return carries the count of everything evaluated so far.",
        "Make the top call max_value(node, float('-inf'), float('inf')) and "
        "return its pair unchanged.",
    ],
    solution=with_nodes("""
def alphabeta_count(node):

    def max_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 1
        value, leaves = float('-inf'), 0
        for child in subtree.children:
            child_value, child_leaves = min_value(child, alpha, beta)
            leaves += child_leaves
            value = max(value, child_value)
            alpha = max(alpha, value)
            if value >= beta:
                return value, leaves
        return value, leaves

    def min_value(subtree, alpha, beta):
        if subtree.is_leaf():
            return subtree.value, 1
        value, leaves = float('inf'), 0
        for child in subtree.children:
            child_value, child_leaves = max_value(child, alpha, beta)
            leaves += child_leaves
            value = min(value, child_value)
            beta = min(beta, value)
            if value <= alpha:
                return value, leaves
        return value, leaves

    return max_value(node, float('-inf'), float('inf'))
"""),
    tests=[
        TN("returns a (value, leaves) pair", """
got = alphabeta_count(build([1, 2]))
assert isinstance(got, tuple) and len(got) == 2, (
    "expected (value, leaves), got %r" % (got,))
assert alphabeta_count(build(4)) == (4, 1)
"""),
        TN("figure 5.2 evaluates 7 of 9 leaves", """
got = alphabeta_count(build(@@FIG@@))
if got == (3, 9):
    raise AssertionError("(3, 9): right value, but nothing was pruned")
if got[0] == 3 and got[1] in (0, 1):
    raise AssertionError("%r: the children's leaf counts are not being "
                         "added up" % (got,))
assert got == (3, 7), got
""", FIG=FIG52),
        TN("an equal value prunes too", """
got = alphabeta_count(build(@@TREE@@))
if got == (3, 4):
    raise AssertionError("(3, 4): leaf 9 was evaluated, but 3 <= alpha = 3 "
                         "already cuts MIN node [1] off")
assert got == (3, 3), got
""", TREE=EQUAL_EDGE),
        TN("random trees, with the common mistakes recognised", """
CASES = @@CASES@@
for spec, want, unpruned, strict in CASES:
    got = alphabeta_count(build(spec))
    if got != want and got == unpruned:
        raise AssertionError("%r is plain minimax's count -- nothing was "
                             "pruned on %r" % (got, spec))
    if got != want and got == strict:
        raise AssertionError("%r matches cutting off on < and > instead of "
                             "<= and >= on %r" % (got, spec))
    assert got == want, (spec, got, want)
""", CASES=[(t, alphabeta(t)[1:3], alphabeta(t, bug="no_window")[1:3],
             alphabeta(t, bug="strict_cut")[1:3]) for t in RANDOM_AB]),
    ],
)


problem(
    id="alphabeta-best-move",
    track="Alpha-Beta in Code",
    title="get_best_move on a Bare Tree",
    difficulty="hard",
    points=25,
    blurb="Depth limit, heuristic, (move, value, leaves) -- the homework's search with the game stripped away.",
    statement="""
<p>Write <code>alphabeta_decision(node, limit)</code>: alpha-beta for MAX at
the root, looking no further than <code>limit</code> moves ahead, returning
<code>(move, value, leaves)</code>. It is <code>get_best_move</code> exactly,
with the dominoes board replaced by a tree so nothing but the search can go
wrong:</p>

<ul>
  <li><strong>Stopping.</strong> A node at depth <code>limit</code>, or a
      leaf reached sooner, is evaluated: its value is
      <code>node.value</code>, and it counts as one leaf.</li>
  <li><strong>The move</strong> is the index of the root child. Replace it
      only on a strictly better value, so ties go to the leftmost child.</li>
  <li><strong>Pruning</strong> is figure 5.7's: update alpha at MAX and beta
      at MIN after each child, cut off on <code>&gt;=</code> and
      <code>&lt;=</code>.</li>
</ul>
""" + picture(H_TREE, levels=True) + """
<p>Alpha-beta must return the same move and value that plain minimax does
at every limit &mdash; 1, then 2, then 0 on this tree &mdash; while
evaluating fewer nodes. At limit 3 minimax evaluates 10; alpha-beta needs 8.
The tests check all three numbers, and when yours differ they check whether
you match a known mistake: no pruning, strict cut-offs, ties breaking
rightward, or a limit off by one.</p>
""",
    examples="""
>>> tree = build((0, [(4, [(2, [7, 1]), (9, [3, 8])]),
...                   (6, [(5, [2, 6]), (1, [9, 9])]),
...                   (3, [(8, [4, 5])])]))
>>> alphabeta_decision(tree, 1)
(1, 6, 3)
>>> alphabeta_decision(tree, 3)
(0, 7, 8)
>>> alphabeta_decision(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]), 2)
(0, 3, 7)
""",
    starter=with_nodes("""
def alphabeta_decision(node, limit):
    pass
"""),
    hints=[
        "Two nested helpers, max_value and min_value, each taking (subtree, "
        "alpha, beta, depth) and returning (value, move, leaves). Stop when "
        "depth == 0 or subtree.is_leaf() and return (subtree.value, None, "
        "1).",
        "In max_value's loop over enumerate(subtree.children): recurse into "
        "min_value with depth - 1, add the child's leaves, keep i as the "
        "move if the child's value is > the best, then alpha = max(alpha, "
        "value), then return early if value >= beta.",
        "Call max_value(node, float('-inf'), float('inf'), limit) and reorder "
        "its (value, move, leaves) into (move, value, leaves). This is the "
        "exact structure your homework's get_best_move needs.",
    ],
    solution=with_nodes("""
def alphabeta_decision(node, limit):

    def max_value(subtree, alpha, beta, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        value, move, leaves = float('-inf'), None, 0
        for i, child in enumerate(subtree.children):
            child_value, _, child_leaves = min_value(child, alpha, beta,
                                                     depth - 1)
            leaves += child_leaves
            if child_value > value:
                value, move = child_value, i
            alpha = max(alpha, value)
            if value >= beta:
                return value, move, leaves
        return value, move, leaves

    def min_value(subtree, alpha, beta, depth):
        if depth == 0 or subtree.is_leaf():
            return subtree.value, None, 1
        value, move, leaves = float('inf'), None, 0
        for i, child in enumerate(subtree.children):
            child_value, _, child_leaves = max_value(child, alpha, beta,
                                                     depth - 1)
            leaves += child_leaves
            if child_value < value:
                value, move = child_value, i
            beta = min(beta, value)
            if value <= alpha:
                return value, move, leaves
        return value, move, leaves

    value, move, leaves = max_value(node, float('-inf'), float('inf'), limit)
    return move, value, leaves
"""),
    tests=[
        TN("returns a (move, value, leaves) tuple", """
got = alphabeta_decision(build([[1, 2], [3, 4]]), 2)
assert isinstance(got, tuple) and len(got) == 3, (
    "expected (move, value, leaves), got %r" % (got,))
"""),
        TN("same move and value as minimax at every limit, fewer leaves", """
tree = build(@@TREE@@)
WANT = @@WANT@@
for limit in (1, 2, 3):
    got = alphabeta_decision(tree, limit)
    assert got == WANT[limit], (limit, got, WANT[limit])
""", TREE=H_TREE, WANT={k: alphabeta(H_TREE, k)[:3] for k in (1, 2, 3)}),
        TN("ties go to the leftmost child", """
got = alphabeta_decision(build([[5, 6], [7, 5], [5, 9]]), 2)
if got[0] == 2:
    raise AssertionError("%r: a later equal value replaced the move -- "
                         "use > not >=" % (got,))
assert got == @@WANT@@, got
""", WANT=alphabeta([[5, 6], [7, 5], [5, 9]], 2)[:3]),
        TN("random trees at limits 1 to 4, known mistakes recognised", """
CASES = @@CASES@@
MESSAGES = {
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later child -- replace the move only on >",
    "deeper": "searched one move deeper than the limit",
    "shallower": "searched one move shallower than the limit",
}
for spec, limit, want, mistakes in CASES:
    got = alphabeta_decision(build(spec), limit)
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("limit %d, got %r: %s" % (
                    limit, got, MESSAGES[name]))
    assert got == want, (spec, limit, got, want)
""", CASES=[
            (t, k, alphabeta(t, k)[:3],
             [(bug, alphabeta(t, k, bug=bug)[:3])
              for bug in ("no_window", "strict_cut", "ties_last")
              if alphabeta(t, k, bug=bug)[:3] != alphabeta(t, k)[:3]]
             + [(name, alphabeta(t, k2)[:3])
                for name, k2 in (("deeper", k + 1), ("shallower", k - 1))
                if alphabeta(t, k2)[:3] != alphabeta(t, k)[:3]])
            for t in RANDOM_AB_H for k in range(1, 5)]),
    ],
)


problem(
    id="pruned-leaves",
    track="Alpha-Beta in Code",
    title="Name the Leaves It Never Read",
    difficulty="medium",
    points=20,
    blurb="Report what alpha-beta skipped -- which means telling two leaves with the same value apart.",
    statement="""
<p>Write <code>pruned_leaves(node)</code>: run alpha-beta from MAX at the
root with no depth limit, and return the values of the leaves it never
evaluated, in left-to-right order.</p>

<p>This is the question exams ask about figure 5.7, turned into code. For
figure 5.2 the answer is <code>[4, 6]</code>.</p>

<p>The catch is that leaf values repeat. In <code>[[3, 5], [2, 3]]</code>
MIN node <code>[1]</code> stops at 2, so its second leaf is pruned &mdash; but
that leaf holds 3, the same value as a leaf that <em>was</em> evaluated. Keep
a set of evaluated values and you'll wrongly report nothing. Record the leaf
objects themselves (or their <code>id()</code>) instead.</p>
""",
    examples="""
>>> pruned_leaves(build([[3, 12, 8], [2, 4, 6], [14, 5, 2]]))
[4, 6]
>>> pruned_leaves(build([[3, 5], [2, 3]]))
[3]
>>> pruned_leaves(build([[1, 2], [3, 4]]))
[]
""",
    starter=with_nodes("""
def pruned_leaves(node):
    pass
"""),
    hints=[
        "Two passes. First run alpha-beta, recording each leaf at the moment "
        "you evaluate it. Then walk every leaf left to right and keep the "
        "ones you didn't record.",
        "Create the record in pruned_leaves and have nested max_value / "
        "min_value helpers add to it -- the same closure pattern as "
        "get_best_move's evaluation function.",
        "Record id(leaf), not leaf.value. Two different leaves can hold 3; "
        "only one of them may have been evaluated.",
    ],
    solution=with_nodes("""
def pruned_leaves(node):
    evaluated = set()

    def max_value(subtree, alpha, beta):
        if subtree.is_leaf():
            evaluated.add(id(subtree))
            return subtree.value
        value = float('-inf')
        for child in subtree.children:
            value = max(value, min_value(child, alpha, beta))
            alpha = max(alpha, value)
            if value >= beta:
                return value
        return value

    def min_value(subtree, alpha, beta):
        if subtree.is_leaf():
            evaluated.add(id(subtree))
            return subtree.value
        value = float('inf')
        for child in subtree.children:
            value = min(value, max_value(child, alpha, beta))
            beta = min(beta, value)
            if value <= alpha:
                return value
        return value

    def every_leaf(subtree):
        if subtree.is_leaf():
            yield subtree
        for child in subtree.children:
            yield from every_leaf(child)

    max_value(node, float('-inf'), float('inf'))
    return [leaf.value for leaf in every_leaf(node)
            if id(leaf) not in evaluated]
"""),
    tests=[
        TN("figure 5.2 prunes 4 and 6", """
got = pruned_leaves(build(@@FIG@@))
assert got == [4, 6], got
""", FIG=FIG52),
        TN("nothing pruned when every child improves the bound", """
got = pruned_leaves(build([[1, 2], [3, 4]]))
assert got == [], got
"""),
        TN("a pruned leaf can share a value with an evaluated one", """
got = pruned_leaves(build(@@TREE@@))
if got == []:
    raise AssertionError("[]: the pruned leaf holds 3, like an evaluated "
                         "leaf -- track leaves by id(), not by value")
assert got == [3], got
""", TREE=DUPLICATES),
        TN("left-to-right order across subtrees", """
tree = @@TREE@@
got = pruned_leaves(build(tree))
assert got == @@WANT@@, got
""", TREE=[[5, 9], [4, 1, 7], [[6, 2], 3, 8]],
           WANT=o_pruned([[5, 9], [4, 1, 7], [[6, 2], 3, 8]])),
        TN("random trees", """
CASES = @@CASES@@
for spec, want in CASES:
    got = pruned_leaves(build(spec))
    assert got == want, (spec, got, want)
""", CASES=[(t, o_pruned(t)) for t in RANDOM_AB]),
    ],
)


# --------------------------------------------------------------------------
# Track 5 -- homework-style games: the same search, on real game classes
# --------------------------------------------------------------------------

def game_search(root, children, evaluate, limit, bug=None):
    """Alpha-beta over any game, with the same `bug` switches as alphabeta().

    children(state, maxing) -> [(move, next_state)] in the order moves are
    generated; evaluate(state, maxing) -> score from the root player's view.
    """
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


def tri_cells(row, col, vertical):
    return [(row + i, col) if vertical else (row, col + i) for i in range(3)]


def tri_legal(board, row, col, vertical):
    rows, cols = len(board), len(board[0])
    return all(0 <= r < rows and 0 <= c < cols and not board[r][c]
               for r, c in tri_cells(row, col, vertical))


def tri_moves(board, vertical):
    return [(r, c) for r in range(len(board)) for c in range(len(board[0]))
            if tri_legal(board, r, c, vertical)]


def tri_after(board, move, vertical):
    new = [row[:] for row in board]
    for r, c in tri_cells(move[0], move[1], vertical):
        new[r][c] = True
    return new


def tri_best(board, vertical, limit, bug=None):
    def children(state, maxing):
        to_move = vertical if maxing else not vertical
        return [(m, tri_after(state, m, to_move))
                for m in tri_moves(state, to_move)]

    def evaluate(state, maxing):
        me = vertical
        if bug == "mover":
            me = vertical if maxing else not vertical
        return len(tri_moves(state, me)) - len(tri_moves(state, not me))

    search_bug = None if bug == "mover" else bug
    return game_search(board, children, evaluate, limit, search_bug)


F, X = False, True
TRI_BOARDS = [
    [[F] * 3 for _ in range(3)],
    [[F] * 5 for _ in range(2)],
    [[F] * 2 for _ in range(5)],
    [[F, X, F, F], [F, F, F, X], [F, F, F, F], [X, F, F, F]],
    [[F, F, F, X, F], [F, X, F, F, F], [F, F, F, F, F]],
    [[F, F, F]],
]
TRI_SEARCH_BOARDS = [
    [[F] * 3 for _ in range(3)],
    [[F] * 4 for _ in range(3)],
    [[F] * 4 for _ in range(4)],
    [[F, X, F, F], [F, F, F, X], [F, F, F, F], [X, F, F, F]],
    [[F, F, F, X, F], [F, X, F, F, F], [F, F, F, F, F], [F, F, X, F, F]],
    [[F] * 5 for _ in range(3)],
]
TRI_MISTAKES = ("mover", "no_window", "strict_cut", "ties_last")


def tri_case(board, vertical, limit):
    want = tri_best(board, vertical, limit)
    mistakes = [(bug, tri_best(board, vertical, limit, bug))
                for bug in TRI_MISTAKES]
    mistakes += [("deeper", tri_best(board, vertical, limit + 1)),
                 ("shallower", tri_best(board, vertical, limit - 1))]
    return (board, vertical, limit, want,
            [(name, out) for name, out in mistakes if out != want])


TRI_CASES = [tri_case(b, v, k) for b in TRI_SEARCH_BOARDS
             for v in (True, False) for k in (1, 2, 3)]
TRI_MOVER = next(c for c in TRI_CASES
                 if any(name == "mover" for name, _ in c[4]))

TRI_SOLUTION = '''
def create_triominoes_game(rows, cols):
    return TriominoesGame([[False] * cols for _ in range(rows)])


class TriominoesGame(object):

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

    def legal_moves(self, vertical):
        for row in range(self.rows):
            for col in range(self.cols):
                if self.is_legal_move(row, col, vertical):
                    yield (row, col)

    def perform_move(self, row, col, vertical):
        for r, c in self.cells(row, col, vertical):
            self.board[r][c] = True

    def game_over(self, vertical):
        return next(self.legal_moves(vertical), None) is None

    def copy(self):
        return TriominoesGame([row[:] for row in self.board])

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
    id="triominoes-game",
    track="Homework-Style Games",
    title="Dominoes, One Square Longer",
    difficulty="hard",
    points=30,
    blurb="The whole DominoesGame class again with 1x3 pieces -- every bound moves by one, and the search must not care.",
    statement="""
<p>Same game as the homework, with longer pieces. Two players take turns
placing <strong>1&times;3</strong> pieces on a grid of Booleans
(<code>True</code> = filled). The vertical player always covers
<code>(row, col)</code>, <code>(row + 1, col)</code> and <code>(row + 2,
col)</code>; the horizontal player covers <code>(row, col)</code>,
<code>(row, col + 1)</code> and <code>(row, col + 2)</code>. The last player
able to move wins.</p>

<p>Write the whole class from the skeleton, method for method as in the
homework:</p>

<ul>
  <li><code>__init__</code>, <code>get_board</code>, and the top-level
      <code>create_triominoes_game(rows, cols)</code>.</li>
  <li><code>is_legal_move(row, col, vertical)</code> &mdash; all three
      squares in bounds and empty.</li>
  <li><code>legal_moves(vertical)</code> &mdash; a <strong>generator</strong>
      of <code>(row, col)</code> in row-major order.</li>
  <li><code>perform_move(row, col, vertical)</code> &mdash; fills the
      squares in place and returns <code>None</code>.</li>
  <li><code>game_over(vertical)</code> &mdash; whether that player has no
      legal move.</li>
  <li><code>copy()</code> and <code>successors(vertical)</code> &mdash; the
      latter yields <code>((row, col), new_game)</code> in row-major order and
      never touches the original.</li>
  <li><code>get_best_move(vertical, limit)</code> &mdash; alpha-beta
      returning <code>(move, value, leaves)</code>, scoring a board as the
      caller's legal moves minus the opponent's.</li>
</ul>

<p>Every trap from the homework is still here, and a couple got easier to
fall into. The piece reaches <em>two</em> squares past its anchor, so a
bounds check copied from dominoes is wrong; boards are often not square, so
checking a column against the row count only passes on square boards. And
the evaluation must stay with the <code>vertical</code> passed to
<code>get_best_move</code> at every depth &mdash; score from whoever is to
move instead and the numbers stay plausible while the answers go wrong.</p>
""",
    examples="""
>>> g = create_triominoes_game(3, 3)
>>> g.is_legal_move(0, 0, True), g.is_legal_move(1, 0, True)
(True, False)
>>> list(g.legal_moves(False))
[(0, 0), (1, 0), (2, 0)]
>>> g.perform_move(0, 1, True)
>>> g.get_board()
[[False, True, False], [False, True, False], [False, True, False]]
>>> g.game_over(False)
True
>>> create_triominoes_game(3, 3).get_best_move(True, 1)
((0, 0), 2, 3)
>>> list(create_triominoes_game(2, 4).legal_moves(True))
[]
>>> create_triominoes_game(2, 4).get_best_move(False, 1)
((0, 0), 2, 4)
""",
    starter="""
def create_triominoes_game(rows, cols):
    pass


class TriominoesGame(object):

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
        "Get is_legal_move right first and everything else leans on it. "
        "Build the list of the three squares the piece would cover, then "
        "check each one is inside the board and empty. Compare row indices "
        "against the number of rows and column indices against the number "
        "of columns.",
        "legal_moves is two loops over every square with a yield. successors "
        "copies, performs the move on the copy, and yields ((row, col), "
        "copy). A shallow copy of the board shares rows, so copy each row.",
        "get_best_move is your homework's, unchanged: nested max and min "
        "helpers, stop on depth == 0 or game_over(vert_flag), recurse on the "
        "successor with not vert_flag and depth - 1, add up leaves, keep the "
        "move only on a strictly better value. The evaluation closes over "
        "the original vertical.",
    ],
    solution=TRI_SOLUTION,
    tests=[
        T("stores the board and creates empty boards of any shape", """
board = [[False, True], [False, False]]
assert TriominoesGame(board).get_board() is board, (
    "get_board should return the board you were given, not a copy")
assert create_triominoes_game(2, 5).get_board() == [[False] * 5] * 2
assert create_triominoes_game(5, 2).get_board() == [[False] * 2] * 5
"""),
        T("is_legal_move matches the rules on every square, in and out of bounds", """
CASES = @@CASES@@
for board, expected in CASES:
    game = TriominoesGame([row[:] for row in board])
    for row, col, vertical, want in expected:
        got = game.is_legal_move(row, col, vertical)
        assert got == want, (
            "board %r: is_legal_move(%d, %d, %s) gave %r"
            % (board, row, col, vertical, got))
""", CASES=[(b, [(r, c, v, tri_legal(b, r, c, v))
                 for r in range(-1, len(b) + 2)
                 for c in range(-1, len(b[0]) + 2) for v in (True, False)])
            for b in TRI_BOARDS]),
        T("legal_moves is a row-major generator", """
import inspect
CASES = @@CASES@@
result = TriominoesGame([[False] * 3] * 3).legal_moves(True)
assert inspect.isgenerator(result), "legal_moves should use yield"
for board, vertical, want in CASES:
    got = list(TriominoesGame([row[:] for row in board]).legal_moves(vertical))
    assert got == want, (board, vertical, got, want)
""", CASES=[(b, v, tri_moves(b, v)) for b in TRI_BOARDS for v in (True, False)]),
        T("perform_move fills three squares in place and returns None", """
board = [[False] * 5 for _ in range(4)]
game = TriominoesGame(board)
assert game.perform_move(0, 1, True) is None, "perform_move should return None"
assert game.perform_move(3, 2, False) is None
assert game.get_board() is board, "perform_move should change the board in place"
assert board == @@WANT@@, board
""", WANT=tri_after(tri_after([[F] * 5 for _ in range(4)], (0, 1), True),
                   (3, 2), False)),
        T("game_over means no piece fits, not a full board", """
assert TriominoesGame([[False] * 3 for _ in range(3)]).game_over(True) is False
wide = TriominoesGame([[False] * 5 for _ in range(2)])
assert wide.game_over(True) is True, "a 2-row board has no vertical move"
assert wide.game_over(False) is False
jammed = TriominoesGame([[False, True, False],
                         [True, False, True],
                         [False, True, False]])
assert jammed.game_over(True) and jammed.game_over(False), (
    "five squares are empty but no piece fits anywhere")
"""),
        T("copy is deep enough that the two games are independent", """
original = TriominoesGame([[False] * 4 for _ in range(3)])
twin = original.copy()
assert isinstance(twin, TriominoesGame), "copy should return a TriominoesGame"
assert twin.get_board() == original.get_board()
assert twin.get_board() is not original.get_board()
assert all(a is not b for a, b in zip(twin.get_board(), original.get_board())), (
    "the copy shares row lists with the original -- copy each row")
twin.perform_move(0, 0, True)
assert original.get_board() == [[False] * 4 for _ in range(3)], (
    "a move on the copy changed the original")
"""),
        T("successors pair each move with a new game and leave the original alone", """
import inspect
CASES = @@CASES@@
for board, vertical, want in CASES:
    game = TriominoesGame([row[:] for row in board])
    result = game.successors(vertical)
    assert inspect.isgenerator(result), "successors should use yield"
    pairs = list(result)
    assert [move for move, _ in pairs] == [move for move, _ in want], (
        board, vertical, [move for move, _ in pairs])
    for (move, child), (_, child_board) in zip(pairs, want):
        assert child.get_board() == child_board, (board, move, child.get_board())
    assert game.get_board() == board, "successors changed the original board"
    rows = [id(row) for _, child in pairs for row in child.get_board()]
    assert len(rows) == len(set(rows)), "two successors share a row list"
""", CASES=[(b, v, [(m, tri_after(b, m, v)) for m in tri_moves(b, v)])
            for b in TRI_BOARDS[3:5] for v in (True, False)]),
        T("get_best_move scores from the caller's side at every depth", """
board, vertical, limit, want, mistakes = @@CASE@@
got = TriominoesGame([row[:] for row in board]).get_best_move(vertical, limit)
if got != want and got == dict(mistakes).get("mover"):
    raise AssertionError(
        "%r: the evaluation is being scored for whoever is to move. It must "
        "always count moves for the vertical passed to get_best_move." % (got,))
assert got == want, (got, want)
""", CASE=TRI_MOVER),
        T("get_best_move across boards, players and limits", """
CASES = @@CASES@@
MESSAGES = {
    "mover": "scored for whoever is to move, not the caller",
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a later move -- replace the move only on >",
    "deeper": "searched one move deeper than the limit",
    "shallower": "searched one move shallower than the limit",
}
for board, vertical, limit, want, mistakes in CASES:
    game = TriominoesGame([row[:] for row in board])
    got = game.get_best_move(vertical, limit)
    assert game.get_board() == board, "get_best_move changed the board"
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("vertical=%s limit=%d on %r: got %r, %s"
                                     % (vertical, limit, board, got,
                                        MESSAGES[name]))
    assert got == want, (board, vertical, limit, got, want)
""", CASES=TRI_CASES),
    ],
)


def take_best(stones, max_take, limit, bug=None):
    def children(state, maxing):
        return [(t, state - t) for t in range(1, min(max_take, state) + 1)]

    def evaluate(state, maxing):
        if state != 0:
            return 0
        if bug == "fixed_sign":
            return -1
        return -1 if maxing else 1

    search_bug = None if bug == "fixed_sign" else bug
    return game_search(stones, children, evaluate, limit, search_bug)


TAKE_MISTAKES = ("fixed_sign", "no_window", "strict_cut", "ties_last")


def take_case(stones, max_take, limit):
    want = take_best(stones, max_take, limit)
    mistakes = [(bug, take_best(stones, max_take, limit, bug))
                for bug in TAKE_MISTAKES]
    return (stones, max_take, limit, want,
            [(name, out) for name, out in mistakes if out != want])


TAKE_CASES = [take_case(s, k, d) for s in range(1, 10) for k in (2, 3, 4)
              for d in range(1, 6)]

TAKE_GIVEN = '''
class TakeAwayGame(object):

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
            yield take, TakeAwayGame(self.stones - take, self.max_take)
'''.strip("\n")

problem(
    id="take-away",
    track="Homework-Style Games",
    title="Last Stone Wins",
    difficulty="hard",
    points=25,
    blurb="No vertical flag, and a score whose sign depends on whose turn it is when the pile runs out.",
    statement="""
<p>A pile of stones sits between two players. On your turn you take between
1 and <code>max_take</code> stones, never more than remain, and whoever takes
the <strong>last</strong> stone wins. So a player who faces an empty pile has
already lost.</p>

<p>The starter gives you the game &mdash; <code>game_over</code>,
<code>legal_moves</code> (smallest take first) and <code>successors</code>.
Write <code>get_best_move(self, limit)</code>: alpha-beta, structured exactly
like the homework, returning <code>(move, value, leaves)</code> for the
player about to move. What changes is the evaluation, which is from that
player's point of view:</p>

<ul>
  <li><code>+1</code> &mdash; the pile is empty and it is the
      <em>opponent's</em> turn: you took the last stone.</li>
  <li><code>-1</code> &mdash; the pile is empty and it is <em>your</em>
      turn: they did.</li>
  <li><code>0</code> &mdash; the depth limit arrived before the game
      ended.</li>
</ul>

<p>There is no <code>vertical</code> flag to pass around, because both
players have the same moves. Whose turn it is lives in your recursion
&mdash; a MAX call is your turn, a MIN call is theirs &mdash; so the
evaluation has to be told which one it's in. An empty pile is not simply
bad.</p>

<p>Nodes where the search stops count as leaves as before, and ties go to
the smallest take.</p>
""",
    examples="""
>>> TakeAwayGame(1).get_best_move(1)
(1, 1, 1)
>>> TakeAwayGame(4).get_best_move(1)
(1, 0, 3)
>>> TakeAwayGame(4).get_best_move(2)
(1, -1, 6)
>>> TakeAwayGame(5).get_best_move(2)
(1, 0, 5)
""",
    starter=TAKE_GIVEN + """

    def get_best_move(self, limit):
        pass
""",
    hints=[
        "Reuse the homework's shape: max_value(game, alpha, beta, depth) and "
        "min_value(...), each returning (value, move, leaves), stopping when "
        "depth == 0 or game.game_over().",
        "The stopping case needs to know whose turn it is. In max_value an "
        "empty pile means you are to move with nothing to take, so it is "
        "-1; in min_value it means the opponent is stuck, so +1. A pile "
        "that still has stones is 0.",
        "If a single stone with limit 1 gives you (1, -1, 1), your empty "
        "pile is scored as a loss in both helpers. Taking that stone "
        "empties the pile on the opponent's turn, which is a win.",
    ],
    solution=TAKE_GIVEN + """

    def get_best_move(self, limit):

        def max_value(game, alpha, beta, depth):
            if game.game_over():
                return -1, None, 1
            if depth == 0:
                return 0, None, 1
            value, move, leaves = float('-inf'), None, 0
            for take, after in game.successors():
                v2, _, l2 = min_value(after, alpha, beta, depth - 1)
                leaves += l2
                if v2 > value:
                    value, move = v2, take
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
            for take, after in game.successors():
                v2, _, l2 = max_value(after, alpha, beta, depth - 1)
                leaves += l2
                if v2 < value:
                    value, move = v2, take
                beta = min(beta, value)
                if value <= alpha:
                    return value, move, leaves
            return value, move, leaves

        value, move, leaves = max_value(self, float('-inf'), float('inf'),
                                        limit)
        return move, value, leaves
""",
    tests=[
        T("returns a (move, value, leaves) tuple", """
got = TakeAwayGame(3).get_best_move(1)
assert isinstance(got, tuple) and len(got) == 3, (
    "expected (move, value, leaves), got %r" % (got,))
"""),
        T("taking the last stone is a win", """
got = TakeAwayGame(1).get_best_move(1)
if got == (1, -1, 1):
    raise AssertionError("(1, -1, 1): after you take the last stone it is "
                         "the opponent who faces the empty pile -- that's +1")
assert got == (1, 1, 1), got
got = TakeAwayGame(3).get_best_move(1)
assert got == @@THREE@@, got
""", THREE=take_best(3, 3, 1)),
        T("a forced loss inside the horizon is -1", """
got = TakeAwayGame(4).get_best_move(2)
assert got == @@FOUR@@, got
""", FOUR=take_best(4, 3, 2)),
        T("a horizon too short to see the end scores 0", """
got = TakeAwayGame(10).get_best_move(2)
assert got == @@TEN@@, got
""", TEN=take_best(10, 3, 2)),
        T("every pile, take limit and depth up to 9, 4 and 5", """
CASES = @@CASES@@
MESSAGES = {
    "fixed_sign": "an empty pile is scored -1 whoever is to move",
    "no_window": "nothing was pruned -- update alpha/beta after each child",
    "strict_cut": "cut-offs use < and > instead of <= and >=",
    "ties_last": "ties went to a larger take -- replace the move only on >",
}
for stones, max_take, limit, want, mistakes in CASES:
    got = TakeAwayGame(stones, max_take).get_best_move(limit)
    if got != want:
        for name, output in mistakes:
            if got == output:
                raise AssertionError("%d stones, max_take %d, limit %d: got "
                                     "%r, %s" % (stones, max_take, limit, got,
                                                 MESSAGES[name]))
    assert got == want, (stones, max_take, limit, got, want)
""", CASES=TAKE_CASES),
    ],
)


TRACKS = [
    ("Recursion on Trees",
     "The recursive shapes every game-tree search is built from."),
    ("Minimax",
     "Alternating players, then a horizon that changes the answer."),
    ("Alpha-Beta in Code",
     "Figure 5.7 as Python, checked leaf by leaf."),
    ("Homework-Style Games",
     "Game classes shaped like DominoesGame, searched with get_best_move."),
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
