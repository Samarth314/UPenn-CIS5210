"""Build the CS Gym (Recursion Fundamentals) problem bank.

Same contract as the other gyms: every problem carries a reference solution
and a test suite, and this script runs each reference solution against its
own tests before emitting problems.json, so a broken problem can never reach
the site.
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


TRACKS = [
    ("Base Case & Accumulation",
     "The two halves every recursive function needs, and trusting the "
     "call to have already solved the smaller problem."),
    ("Recursion Meets Structure",
     "Nested lists, branching calls, and returning more than one thing "
     "at once -- the shapes trees need next."),
]


# --------------------------------------------------------------------------
# Track 1
# --------------------------------------------------------------------------

problem(
    id="factorial",
    track="Base Case & Accumulation",
    title="Factorial, the Smallest Possible Recursion",
    difficulty="warmup",
    points=5,
    blurb="One base case, one recursive case, nothing else -- get this reflex automatic first.",
    statement="""
<p>Write <code>factorial(n)</code> recursively: <code>n!</code> is
<code>n * (n - 1) * ... * 1</code>, and <code>0!</code> is <code>1</code> by
definition. Assume <code>n &gt;= 0</code>.</p>

<p>Do not use a loop. The point of this problem is entirely the shape:
one line that stops the recursion, one line that trusts
<code>factorial(n - 1)</code> to already be correct and builds this
call's answer on top of it.</p>
""",
    examples="""
>>> factorial(0)
1
>>> factorial(1)
1
>>> factorial(5)
120
""",
    starter="""
def factorial(n):
    pass
""",
    hints=[
        "The base case is the smallest input you can answer without "
        "recursing at all: n == 0. What is 0! by definition?",
        "For everything else, assume factorial(n - 1) already returns the "
        "correct answer for n - 1 -- don't try to trace through what it "
        "does internally. Given that trusted number, how do you build n!  "
        "from it?",
        "return n * factorial(n - 1). Nothing more is needed.",
    ],
    solution="""
def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n - 1)
""",
    tests=[
        T("the base case itself", "assert factorial(0) == 1"),
        T("small values", """
assert factorial(1) == 1
assert factorial(2) == 2
assert factorial(3) == 6
"""),
        T("checked against a direct loop", """
for n in range(10):
    want = 1
    for k in range(1, n + 1):
        want *= k
    assert factorial(n) == want, (n, factorial(n), want)
"""),
    ],
)


problem(
    id="sum-list",
    track="Base Case & Accumulation",
    title="Summing a List Without a Loop",
    difficulty="easy",
    points=10,
    blurb="The base case is the empty list -- and the recursive call already solved everything after the first element.",
    statement="""
<p>Write <code>sum_list(values)</code>, the sum of a list of numbers,
without using a loop or the built-in <code>sum</code>.</p>

<p>The recursive step splits the list into its first element and
"everything else": <code>values[0]</code> and <code>values[1:]</code>.
Trust that <code>sum_list(values[1:])</code> already correctly adds up
everything after the first element -- don't try to reason about what
happens two or three calls deep. Given that trusted number, what do you
add to it?</p>
""",
    examples="""
>>> sum_list([])
0
>>> sum_list([5])
5
>>> sum_list([1, 2, 3, 4])
10
>>> sum_list([-3, 3])
0
""",
    starter="""
def sum_list(values):
    pass
""",
    hints=[
        "The base case is the empty list -- there is nothing to add, so "
        "what should an empty list sum to?",
        "The recursive case: values[0] + sum_list(values[1:]). The slice "
        "values[1:] is a brand-new, one-shorter list -- that's what makes "
        "the recursion make progress toward the base case.",
        "If you're tempted to write a loop inside this function, stop -- "
        "the recursive call is doing the loop's job. Each call handles "
        "exactly one element, then delegates the rest.",
    ],
    solution="""
def sum_list(values):
    if not values:
        return 0
    return values[0] + sum_list(values[1:])
""",
    tests=[
        T("the empty list sums to zero", "assert sum_list([]) == 0"),
        T("small lists", """
assert sum_list([5]) == 5
assert sum_list([1, 2, 3, 4]) == 10
assert sum_list([-3, 3]) == 0
"""),
        T("negative numbers throughout", """
assert sum_list([-1, -2, -3]) == -6
"""),
        T("random lists, checked against the built-in sum", """
import random
random.seed(3)
for _ in range(200):
    values = [random.randint(-50, 50) for _ in range(random.randint(0, 12))]
    assert sum_list(values) == sum(values), values
"""),
    ],
)


problem(
    id="max-of-list",
    track="Base Case & Accumulation",
    title="The Biggest Number, One Element at a Time",
    difficulty="easy",
    points=10,
    blurb="Compare the first element against what the rest of the list already decided -- not against a value you invent.",
    statement="""
<p>Write <code>max_of_list(values)</code>: the largest number in a
<strong>non-empty</strong> list, recursively, without the built-in
<code>max</code>.</p>

<p>This is the exact shape a later tree problem needs, so it's worth
getting the instinct right here first: the recursive call
<code>max_of_list(values[1:])</code> already correctly tells you the
largest value among everything after the first element. Your only job at
this call is to compare <code>values[0]</code> against that trusted
number.</p>

<p>A list of one element has nothing to compare against and nothing left to
recurse into -- that's your base case. Watch for negative numbers: a
starting guess of <code>0</code> is wrong if every value in the list is
negative.</p>
""",
    examples="""
>>> max_of_list([7])
7
>>> max_of_list([3, 9, 2])
9
>>> max_of_list([-5, -1, -9])
-1
""",
    starter="""
def max_of_list(values):
    pass
""",
    hints=[
        "Base case: a list with exactly one element. Its max is that "
        "element -- there's nothing to recurse into.",
        "Recursive case: rest_max = max_of_list(values[1:]). That call "
        "has already found the biggest value in everything after the "
        "first element. Now compare values[0] against rest_max directly "
        "-- don't seed a running variable from 0 or from values[0] alone "
        "and then loop.",
        "return values[0] if values[0] > rest_max else rest_max.",
    ],
    solution="""
def max_of_list(values):
    if len(values) == 1:
        return values[0]
    rest_max = max_of_list(values[1:])
    return values[0] if values[0] > rest_max else rest_max
""",
    tests=[
        T("a single element is its own max", "assert max_of_list([7]) == 7"),
        T("small lists, max in different positions", """
assert max_of_list([3, 9, 2]) == 9
assert max_of_list([9, 3, 2]) == 9
assert max_of_list([3, 2, 9]) == 9
"""),
        T("all negative -- zero is not a safe starting guess", """
assert max_of_list([-5, -1, -9]) == -1
assert max_of_list([-1, -2, -3]) == -1
"""),
        T("random lists, checked against the built-in max", """
import random
random.seed(4)
for _ in range(200):
    values = [random.randint(-50, 50) for _ in range(random.randint(1, 12))]
    assert max_of_list(values) == max(values), values
"""),
    ],
)


# --------------------------------------------------------------------------
# Track 2
# --------------------------------------------------------------------------

problem(
    id="count-in-nested",
    track="Recursion Meets Structure",
    title="Counting a Value Through Nested Lists",
    difficulty="medium",
    points=15,
    blurb="No fixed depth to loop over -- a list inside a list inside a list, however deep, needs recursion to reach the bottom.",
    statement="""
<p>A list can hold plain numbers and other lists, nested arbitrarily deep:
<code>[1, [2, 3, [4]], 5]</code>. Write
<code>count_value(nested, target)</code>: how many times <code>target</code>
appears anywhere inside, at any depth.</p>

<p>There is no way to know the nesting depth ahead of time, so a fixed
number of loops can't reach the bottom -- recursion is the only way to
handle "arbitrarily deep." This is exactly the shape of a tree's
<code>children</code> list, just without a <code>Node</code> class wrapped
around it.</p>
""",
    examples="""
>>> count_value([1, 2, 3], 2)
1
>>> count_value([1, [2, 3, [2]], 2], 2)
3
>>> count_value([1, [2, [3, [4, [5]]]]], 5)
1
>>> count_value([], 9)
0
""",
    starter="""
def count_value(nested, target):
    pass
""",
    hints=[
        "Loop over the elements of nested. For each one, check: is this "
        "element itself a list, or a plain number?",
        "isinstance(item, list) tells you which case you're in. If item "
        "is a list, recurse into it: count_value(item, target). If it "
        "isn't, just compare it to target directly.",
        "Keep a running total and add each element's contribution -- "
        "either count_value(item, target) for a nested list, or 1 (if it "
        "equals target) / 0 (if it doesn't) for a plain number.",
    ],
    solution="""
def count_value(nested, target):
    total = 0
    for item in nested:
        if isinstance(item, list):
            total += count_value(item, target)
        elif item == target:
            total += 1
    return total
""",
    tests=[
        T("a flat list", "assert count_value([1, 2, 3], 2) == 1"),
        T("the empty list", "assert count_value([], 9) == 0"),
        T("repeats scattered across depths", """
assert count_value([1, [2, 3, [2]], 2], 2) == 3
"""),
        T("deep nesting, a single match at the bottom", """
assert count_value([1, [2, [3, [4, [5]]]]], 5) == 1
assert count_value([1, [2, [3, [4, [5]]]]], 1) == 1
"""),
        T("random nested lists, checked against a direct flatten", """
import random
random.seed(5)

def make(depth):
    if depth == 0 or random.random() < 0.4:
        return random.randint(0, 4)
    return [make(depth - 1) for _ in range(random.randint(0, 3))]

def flat(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out += flat(item)
        else:
            out.append(item)
    return out

for _ in range(100):
    tree = [make(3) for _ in range(random.randint(0, 4))]
    for target in range(5):
        want = flat(tree).count(target)
        assert count_value(tree, target) == want, (tree, target)
"""),
    ],
)


problem(
    id="flatten",
    track="Recursion Meets Structure",
    title="Flattening a Nested List, Lazily",
    difficulty="medium",
    points=15,
    blurb="yield from a recursive call -- the exact tool a tree's leaf-walk needs next.",
    statement="""
<p>Write <code>flatten(nested)</code> as a <strong>generator</strong> that
yields every non-list element inside <code>nested</code>, at any depth,
left to right.</p>

<p>This is deliberately the same shape as walking every leaf of a tree --
just on plain nested lists instead of <code>Node</code> objects. The trap
is the same one too: calling <code>flatten(item)</code> on a line by
itself creates a generator and throws it away without yielding anything.
You need <code>yield from</code> to forward what an inner call
produces.</p>
""",
    examples="""
>>> list(flatten([1, [2, 3], 4]))
[1, 2, 3, 4]
>>> list(flatten([1, [2, [3, [4]]]]))
[1, 2, 3, 4]
>>> list(flatten([]))
[]
""",
    starter="""
def flatten(nested):
    pass
""",
    hints=[
        "Use yield, never build and return a list. Loop over nested: for "
        "each item, check isinstance(item, list).",
        "If item is a plain value, yield item directly. If item is a "
        "list, you need everything it eventually yields, at whatever "
        "depth -- that's yield from flatten(item).",
        "Writing flatten(item) alone (no yield, no yield from) on its own "
        "line does nothing observable -- it builds a generator object "
        "and immediately discards it without running any of its code.",
    ],
    solution="""
def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item
""",
    tests=[
        T("calling it returns a generator", """
import inspect
result = flatten([1, 2])
assert inspect.isgenerator(result), (
    "flatten returned %s -- use yield, not return" % type(result).__name__)
"""),
        T("flat and nested lists, left to right", """
assert list(flatten([1, [2, 3], 4])) == [1, 2, 3, 4]
assert list(flatten([1, [2, [3, [4]]]])) == [1, 2, 3, 4]
assert list(flatten([])) == []
"""),
        T("the first value arrives without walking the rest", """
class Poisoned(list):
    def __iter__(self):
        raise AssertionError(
            "the rest of the list was walked before the first value was "
            "requested -- yield as you go, using yield from on nested "
            "lists")

late = [2, 3]
tail = Poisoned([late])
gen = flatten([1] + tail)
assert next(gen) == 1
"""),
        T("random nested lists, checked against a direct flatten", """
import random
random.seed(6)

def make(depth):
    if depth == 0 or random.random() < 0.4:
        return random.randint(0, 20)
    return [make(depth - 1) for _ in range(random.randint(0, 3))]

def ref(nested):
    out = []
    for item in nested:
        if isinstance(item, list):
            out += ref(item)
        else:
            out.append(item)
    return out

for _ in range(100):
    tree = [make(3) for _ in range(random.randint(0, 4))]
    assert list(flatten(tree)) == ref(tree), tree
"""),
    ],
)


problem(
    id="index-of-max",
    track="Recursion Meets Structure",
    title="Where the Biggest Number Is, Not Just What It Is",
    difficulty="medium",
    points=20,
    blurb="A recursive call that has to hand back two things at once, because one of them alone can't answer the question.",
    statement="""
<p>Write <code>index_of_max(values)</code>: the index of the largest value
in a <strong>non-empty</strong> list. If several elements tie for largest,
return the index of the <strong>first</strong> one.</p>

<p>This is the same problem as <code>max_of_list</code>, with one twist
that changes everything about the recursion: you now need to report
<em>where</em> the max is, not just what it is. A recursive call on
<code>values[1:]</code> that only returns an index isn't enough on its
own &mdash; you can't tell whether <code>values[0]</code> beats it without
also knowing <em>what value</em> that index points to. And a call that
only returns the value isn't enough either &mdash; you'd have the number
but no position.</p>

<p>The fix is to have the recursive call return <strong>both</strong> the
best value and its index together, as a pair, so every level of the
recursion has everything it needs to make its own comparison. Only the
outermost call needs to throw away the value and keep just the
index &mdash; which is exactly why a small helper that returns the pair,
called once from inside <code>index_of_max</code>, is the natural
shape here.</p>
""",
    examples="""
>>> index_of_max([7])
0
>>> index_of_max([3, 9, 2])
1
>>> index_of_max([9, 3, 2])
0
>>> index_of_max([1, 5, 5, 2])
1
""",
    starter="""
def index_of_max(values):
    pass
""",
    hints=[
        "Write a helper, best(values), that returns (value, index) for "
        "the best element -- the index is relative to whatever list was "
        "passed to that call, not the original list.",
        "Base case of the helper: one element left. Its pair is "
        "(values[0], 0).",
        "Recursive case: rest_value, rest_index = best(values[1:]). If "
        "values[0] is at least as big as rest_value, this call's answer "
        "is (values[0], 0). Otherwise it's (rest_value, rest_index + 1) "
        "-- the +1 shifts the index because rest_index was counted from "
        "the start of the shorter, sliced list, one position to the "
        "right of where values[0] sits.",
        "Use >=, not >, in that comparison. values[0] is always to the "
        "left of everything best(values[1:]) considered, so on an exact "
        "tie it must win -- using a strict > lets the rest of the list "
        "keep a later duplicate instead of yielding to the earlier one.",
        "index_of_max itself is one line: call best(values) and return "
        "only the index half of the pair.",
    ],
    solution="""
def index_of_max(values):

    def best(values):
        if len(values) == 1:
            return values[0], 0
        rest_value, rest_index = best(values[1:])
        if values[0] >= rest_value:
            return values[0], 0
        return rest_value, rest_index + 1

    return best(values)[1]
""",
    tests=[
        T("a single element is at index 0", "assert index_of_max([7]) == 0"),
        T("the max in different positions", """
assert index_of_max([3, 9, 2]) == 1
assert index_of_max([9, 3, 2]) == 0
assert index_of_max([3, 2, 9]) == 2
"""),
        T("ties resolve to the first occurrence", """
got = index_of_max([1, 5, 5, 2])
assert got == 1, ("got %d -- a later tie replaced the earlier one, use a "
                  "strict > comparison" % got)
got = index_of_max([5, 1, 5])
assert got == 0, got
"""),
        T("all negative values", "assert index_of_max([-5, -1, -9]) == 1"),
        T("random lists, checked against a direct scan", """
import random
random.seed(7)
for _ in range(300):
    values = [random.randint(-30, 30) for _ in range(random.randint(1, 12))]
    want = 0
    for i in range(1, len(values)):
        if values[i] > values[want]:
            want = i
    got = index_of_max(values)
    assert got == want, (values, got, want)
"""),
    ],
)


problem(
    id="fibonacci",
    track="Recursion Meets Structure",
    title="Two Recursive Calls, Combined",
    difficulty="medium",
    points=15,
    blurb="Branching recursion: each call spawns two more, the same way a tree node's children each spawn their own subtrees.",
    statement="""
<p>Write <code>fibonacci(n)</code>: the <code>n</code>th Fibonacci number,
where <code>fibonacci(0) = 0</code>, <code>fibonacci(1) = 1</code>, and
every later term is the sum of the two before it. Assume
<code>n &gt;= 0</code>.</p>

<p>Every problem so far had one recursive call per branch. This one has
<strong>two</strong> &mdash; <code>fibonacci(n - 1)</code> and
<code>fibonacci(n - 2)</code> &mdash; combined into one answer, the same
way a tree node with several children combines each child's separately
computed result. Getting comfortable with "make more than one recursive
call, then combine what comes back" is the last piece before moving on to
trees, where a node can have any number of children, not just two.</p>

<p>This one also has <strong>two</strong> base cases, not one &mdash; both
<code>fibonacci(0)</code> and <code>fibonacci(1)</code> are answered
directly, without recursing.</p>
""",
    examples="""
>>> fibonacci(0)
0
>>> fibonacci(1)
1
>>> fibonacci(2)
1
>>> fibonacci(6)
8
""",
    starter="""
def fibonacci(n):
    pass
""",
    hints=[
        "Two base cases: n == 0 returns 0, n == 1 returns 1. Handle both "
        "before anything recursive.",
        "For n >= 2: fibonacci(n - 1) + fibonacci(n - 2). Each of those "
        "calls is trusted to already be correct on its own -- you don't "
        "need to trace through either one by hand.",
        "This is slow for large n because the same smaller value gets "
        "recomputed many times across the branches -- that's fine for "
        "this problem, and it's exactly the same cost tradeoff an "
        "unpruned game tree has.",
    ],
    solution="""
def fibonacci(n):
    if n == 0:
        return 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)
""",
    tests=[
        T("both base cases", """
assert fibonacci(0) == 0
assert fibonacci(1) == 1
"""),
        T("the first several terms", """
assert fibonacci(2) == 1
assert fibonacci(3) == 2
assert fibonacci(4) == 3
assert fibonacci(5) == 5
assert fibonacci(6) == 8
"""),
        T("checked against a direct iterative computation", """
def ref(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

for n in range(15):
    assert fibonacci(n) == ref(n), (n, fibonacci(n), ref(n))
"""),
    ],
)


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
