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
    ("Strings & Numbers",
     "The same two-part shape on new kinds of input: strings, pairs of "
     "numbers, and an integer shrinking by division instead of slicing."),
    ("New Shapes of Recursion",
     "Halving instead of peeling one off, comparing against a lookahead "
     "result, choosing to include or exclude, and building up a list of "
     "moves instead of a single number."),
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


# --------------------------------------------------------------------------
# Track 3 -- strings & numbers
# --------------------------------------------------------------------------

problem(
    id="reverse-string",
    track="Strings & Numbers",
    title="Reversing a String, One Character at a Time",
    difficulty="easy",
    points=10,
    blurb="sum_list's exact shape, on characters instead of numbers.",
    statement="""
<p>Write <code>reverse_string(s)</code> recursively, without slicing the
whole string backwards (<code>s[::-1]</code>) and without a loop.</p>

<p>Same shape as <code>sum_list</code>: peel off one piece
(<code>s[0]</code>), trust the recursive call to correctly handle
everything after it (<code>s[1:]</code>), then decide where the peeled
piece goes relative to that trusted result.</p>
""",
    examples="""
>>> reverse_string("")
''
>>> reverse_string("a")
'a'
>>> reverse_string("abc")
'cba'
""",
    starter="""
def reverse_string(s):
    pass
""",
    hints=[
        "Base case: the empty string reverses to itself.",
        "reverse_string(s[1:]) already correctly reverses everything "
        "after the first character. Where does s[0] belong relative to "
        "that already-reversed piece -- the front of it, or the back?",
        "return reverse_string(s[1:]) + s[0].",
    ],
    solution="""
def reverse_string(s):
    if s == "":
        return s
    return reverse_string(s[1:]) + s[0]
""",
    tests=[
        T("empty and single character", """
assert reverse_string("") == ""
assert reverse_string("a") == "a"
"""),
        T("short strings", """
assert reverse_string("abc") == "cba"
assert reverse_string("hello") == "olleh"
"""),
        T("random strings, checked against slicing", """
import random, string
random.seed(11)
for _ in range(200):
    s = "".join(random.choice(string.ascii_letters)
               for _ in range(random.randint(0, 10)))
    assert reverse_string(s) == s[::-1], s
"""),
    ],
)


problem(
    id="is-palindrome",
    track="Strings & Numbers",
    title="Palindromes, From Both Ends at Once",
    difficulty="easy",
    points=10,
    blurb="A base case with two exits, and a recursive case that shrinks from both sides.",
    statement="""
<p>Write <code>is_palindrome(s)</code>: whether <code>s</code> reads the
same forwards and backwards, recursively.</p>

<p>Unlike the earlier problems, the recursive step here strips one
character off <strong>each end</strong> at once, rather than peeling off
just the first. That means there are two ways to reach a base case: a
string can shrink down to a single character, or it can shrink down to
nothing (from an even-length string). Both are trivially palindromes.</p>
""",
    examples="""
>>> is_palindrome("")
True
>>> is_palindrome("a")
True
>>> is_palindrome("racecar")
True
>>> is_palindrome("hello")
False
""",
    starter="""
def is_palindrome(s):
    pass
""",
    hints=[
        "Base cases: len(s) <= 1 is always a palindrome -- nothing left "
        "to compare.",
        "Otherwise: does s[0] match s[-1]? If not, you already know the "
        "answer is False without recursing at all.",
        "If the ends do match, the whole string is a palindrome exactly "
        "when the middle -- s[1:-1] -- is also a palindrome. That's the "
        "recursive call.",
    ],
    solution="""
def is_palindrome(s):
    if len(s) <= 1:
        return True
    if s[0] != s[-1]:
        return False
    return is_palindrome(s[1:-1])
""",
    tests=[
        T("the base cases", """
assert is_palindrome("") is True
assert is_palindrome("a") is True
"""),
        T("even and odd length palindromes", """
assert is_palindrome("racecar") is True
assert is_palindrome("abba") is True
"""),
        T("non-palindromes, including a near miss", """
assert is_palindrome("hello") is False
assert is_palindrome("abcba ") is False
"""),
        T("random strings, checked against slicing", """
import random, string
random.seed(12)
for _ in range(300):
    n = random.randint(0, 8)
    s = "".join(random.choice("ab") for _ in range(n))
    assert is_palindrome(s) == (s == s[::-1]), s
"""),
    ],
)


problem(
    id="power",
    track="Strings & Numbers",
    title="Exponentiation, Recursively",
    difficulty="easy",
    points=10,
    blurb="Two arguments this time -- and only one of them shrinks toward the base case.",
    statement="""
<p>Write <code>power(base, exponent)</code>, computing
<code>base ** exponent</code> recursively, for
<code>exponent &gt;= 0</code>, without using <code>**</code> or a
loop.</p>

<p>This has two parameters, but only <code>exponent</code> moves toward a
base case -- <code>base</code> stays fixed across every recursive call.
That is completely normal: not every argument needs to shrink, only
enough of them to guarantee the recursion eventually stops.</p>
""",
    examples="""
>>> power(2, 0)
1
>>> power(2, 5)
32
>>> power(5, 1)
5
""",
    starter="""
def power(base, exponent):
    pass
""",
    hints=[
        "Base case: anything to the power 0 is 1.",
        "Recursive case: power(base, exponent - 1) already correctly "
        "computes base ** (exponent - 1). Multiply that trusted result "
        "by base once more to get base ** exponent.",
        "base itself is never passed anything different across the "
        "recursive calls -- it's exponent that counts down to the base "
        "case.",
    ],
    solution="""
def power(base, exponent):
    if exponent == 0:
        return 1
    return base * power(base, exponent - 1)
""",
    tests=[
        T("the base case", """
assert power(2, 0) == 1
assert power(-7, 0) == 1
"""),
        T("small exponents", """
assert power(2, 5) == 32
assert power(5, 1) == 5
assert power(3, 3) == 27
"""),
        T("negative bases", "assert power(-2, 3) == -8"),
        T("random bases and exponents, checked against **", """
import random
random.seed(13)
for _ in range(200):
    base = random.randint(-10, 10)
    exponent = random.randint(0, 8)
    assert power(base, exponent) == base ** exponent, (base, exponent)
"""),
    ],
)


problem(
    id="gcd",
    track="Strings & Numbers",
    title="Greatest Common Divisor, the Euclidean Way",
    difficulty="medium",
    points=15,
    blurb="The recursive call gets a transformed pair, not a smaller slice -- a new kind of shrinking.",
    statement="""
<p>Write <code>gcd(a, b)</code> for non-negative integers, using
Euclid's algorithm: <code>gcd(a, 0)</code> is <code>a</code>, and
otherwise <code>gcd(a, b)</code> equals <code>gcd(b, a % b)</code>.</p>

<p>Every earlier problem shrank its input by removing one element or
subtracting one from a count. This one shrinks differently: the pair
<code>(a, b)</code> becomes the pair <code>(b, a % b)</code>, and
<code>b</code> is guaranteed to strictly decrease each time (since
<code>a % b &lt; b</code>), which is what guarantees the recursion still
reaches <code>b == 0</code> eventually.</p>
""",
    examples="""
>>> gcd(12, 8)
4
>>> gcd(17, 5)
1
>>> gcd(9, 0)
9
>>> gcd(0, 9)
9
""",
    starter="""
def gcd(a, b):
    pass
""",
    hints=[
        "Base case: b == 0. The answer is just a.",
        "Recursive case: return gcd(b, a % b). Notice the arguments swap "
        "places -- the old second argument becomes the new first one.",
        "Trust that gcd(b, a % b) is already correct; you don't combine "
        "its result with anything else here, you just return it directly.",
    ],
    solution="""
def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)
""",
    tests=[
        T("one argument already zero", """
assert gcd(9, 0) == 9
assert gcd(0, 9) == 9
assert gcd(0, 0) == 0
"""),
        T("small pairs", """
assert gcd(12, 8) == 4
assert gcd(17, 5) == 1
assert gcd(100, 75) == 25
"""),
        T("random pairs, checked against math.gcd", """
import random, math
random.seed(14)
for _ in range(300):
    a = random.randint(0, 500)
    b = random.randint(0, 500)
    assert gcd(a, b) == math.gcd(a, b), (a, b)
"""),
    ],
)


problem(
    id="digit-sum",
    track="Strings & Numbers",
    title="Summing an Integer's Digits",
    difficulty="easy",
    points=10,
    blurb="Shrinking an integer with // and % instead of slicing a list.",
    statement="""
<p>Write <code>digit_sum(n)</code> for <code>n &gt;= 0</code>: the sum of
its decimal digits, recursively, without converting it to a string.</p>

<p>There's no list or string to slice here, so the recursive step needs a
different way to peel off "the last piece and everything else":
<code>n % 10</code> is the last digit, and <code>n // 10</code> is every
digit before it, as a smaller integer.</p>
""",
    examples="""
>>> digit_sum(0)
0
>>> digit_sum(7)
7
>>> digit_sum(123)
6
>>> digit_sum(9999)
36
""",
    starter="""
def digit_sum(n):
    pass
""",
    hints=[
        "Base case: n == 0. There are no digits left to add, but be "
        "careful -- digit_sum(0) itself, as a top-level call, should "
        "still give 0, not skip a real digit that happens to be 0.",
        "Recursive case: n % 10 is the last digit. n // 10 is the number "
        "with that last digit removed -- strictly smaller, moving toward "
        "the base case.",
        "return n % 10 + digit_sum(n // 10).",
    ],
    solution="""
def digit_sum(n):
    if n == 0:
        return 0
    return n % 10 + digit_sum(n // 10)
""",
    tests=[
        T("zero and single digits", """
assert digit_sum(0) == 0
assert digit_sum(7) == 7
"""),
        T("multi-digit numbers", """
assert digit_sum(123) == 6
assert digit_sum(9999) == 36
assert digit_sum(1000) == 1
"""),
        T("random numbers, checked against a string-based sum", """
import random
random.seed(15)
for _ in range(300):
    n = random.randint(0, 10 ** 6)
    assert digit_sum(n) == sum(int(c) for c in str(n)), n
"""),
    ],
)


# --------------------------------------------------------------------------
# Track 4 -- new shapes of recursion
# --------------------------------------------------------------------------

problem(
    id="binary-search",
    track="New Shapes of Recursion",
    title="Cutting the List in Half Each Time",
    difficulty="medium",
    points=15,
    blurb="Every earlier problem shrank by one element. This one shrinks by half.",
    statement="""
<p>Write <code>binary_search(values, target)</code>: given a list sorted
in increasing order, return the index of <code>target</code>, or
<code>-1</code> if it isn't present.</p>

<p>Every recursive problem so far shrank its input by removing exactly
one element (<code>values[1:]</code>, <code>n - 1</code>, one character
off an end). This one shrinks by throwing away <strong>half</strong> the
list every call -- the reason binary search is fast. Slicing a list is
possible but wasteful here (it copies half the list every call); track
the search window instead with a <code>low</code> and <code>high</code>
index into the original list, and shrink the gap between them.</p>
""",
    examples="""
>>> binary_search([1, 3, 5, 7, 9], 7)
3
>>> binary_search([1, 3, 5, 7, 9], 4)
-1
>>> binary_search([], 5)
-1
""",
    starter="""
def binary_search(values, target):

    def search(low, high):
        pass

    return search(0, len(values) - 1)
""",
    hints=[
        "Base case: low > high means the window is empty -- nothing left "
        "to check, target isn't here. Return -1.",
        "Otherwise look at the midpoint: mid = (low + high) // 2. If "
        "values[mid] == target, you're done -- return mid directly, no "
        "recursion needed.",
        "If values[mid] is too small, the target (if present) must be to "
        "the right: recurse on search(mid + 1, high). If it's too big, "
        "recurse on search(low, mid - 1). Either way the window is at "
        "least half the previous size.",
    ],
    solution="""
def binary_search(values, target):

    def search(low, high):
        if low > high:
            return -1
        mid = (low + high) // 2
        if values[mid] == target:
            return mid
        if values[mid] < target:
            return search(mid + 1, high)
        return search(low, mid - 1)

    return search(0, len(values) - 1)
""",
    tests=[
        T("empty list", "assert binary_search([], 5) == -1"),
        T("found at various positions", """
values = [1, 3, 5, 7, 9]
assert binary_search(values, 7) == 3
assert binary_search(values, 1) == 0
assert binary_search(values, 9) == 4
"""),
        T("not present, including gaps and out of range", """
values = [1, 3, 5, 7, 9]
assert binary_search(values, 4) == -1
assert binary_search(values, 0) == -1
assert binary_search(values, 100) == -1
"""),
        T("random sorted lists, checked against a linear scan", """
import random
random.seed(16)
for _ in range(300):
    values = sorted(random.sample(range(200), random.randint(0, 15)))
    target = random.choice(values) if values and random.random() < 0.6 \\
        else random.randint(-5, 205)
    want = values.index(target) if target in values else -1
    got = binary_search(values, target)
    if want == -1:
        assert got == -1, (values, target, got)
    else:
        assert values[got] == target, (values, target, got)
"""),
    ],
)


problem(
    id="is-sorted",
    track="New Shapes of Recursion",
    title="Checking Order, One Adjacent Pair at a Time",
    difficulty="easy",
    points=10,
    blurb="A recursive AND -- the whole list is sorted only if every piece agrees.",
    statement="""
<p>Write <code>is_sorted(values)</code>: whether the list is in
non-decreasing order, recursively, without a loop.</p>

<p>The list is sorted exactly when its first two elements are in order
<strong>and</strong> everything from the second element onward is also
sorted. That "and" is doing real work: both halves have to hold, so a
single <code>False</code> anywhere should make the whole answer
<code>False</code>, however early it's found.</p>
""",
    examples="""
>>> is_sorted([])
True
>>> is_sorted([5])
True
>>> is_sorted([1, 2, 2, 5])
True
>>> is_sorted([3, 1, 2])
False
""",
    starter="""
def is_sorted(values):
    pass
""",
    hints=[
        "Base case: a list with 0 or 1 elements has no adjacent pair to "
        "violate order, so it's trivially sorted.",
        "Recursive case: check values[0] <= values[1]. If that's already "
        "False, the whole list is unsorted -- no need to look further.",
        "If the first pair is fine, the answer depends entirely on "
        "whether values[1:] is sorted: return "
        "values[0] <= values[1] and is_sorted(values[1:]).",
    ],
    solution="""
def is_sorted(values):
    if len(values) <= 1:
        return True
    return values[0] <= values[1] and is_sorted(values[1:])
""",
    tests=[
        T("the base cases", """
assert is_sorted([]) is True
assert is_sorted([5]) is True
"""),
        T("sorted lists, with and without duplicates", """
assert is_sorted([1, 2, 2, 5]) is True
assert is_sorted([1, 1, 1]) is True
"""),
        T("unsorted, including a violation only at the very end", """
assert is_sorted([3, 1, 2]) is False
assert is_sorted([1, 2, 3, 4, 2]) is False
"""),
        T("random lists, checked against sorted()", """
import random
random.seed(17)
for _ in range(300):
    values = [random.randint(0, 5) for _ in range(random.randint(0, 10))]
    assert is_sorted(values) == (values == sorted(values)), values
"""),
    ],
)


problem(
    id="remove-duplicates-sorted",
    track="New Shapes of Recursion",
    title="Dropping Repeats From a Sorted List",
    difficulty="medium",
    points=20,
    blurb="Whether to keep the first element depends on what the recursive call decides to do with the second.",
    statement="""
<p>Write <code>remove_duplicates(values)</code>: given a list sorted in
non-decreasing order, return a new list with consecutive duplicates
collapsed down to one copy each.</p>

<p>The earlier list problems could look at <code>values[0]</code> in
isolation. This one can't: whether to keep <code>values[0]</code> depends
on whether it's equal to <code>values[1]</code> -- which means peeking
one element ahead, not just delegating everything after the first
element to the recursive call unseen.</p>
""",
    examples="""
>>> remove_duplicates([])
[]
>>> remove_duplicates([5])
[5]
>>> remove_duplicates([1, 1, 2, 2, 2, 3])
[1, 2, 3]
>>> remove_duplicates([1, 2, 3])
[1, 2, 3]
""",
    starter="""
def remove_duplicates(values):
    pass
""",
    hints=[
        "Base case: 0 or 1 elements. There's nothing that could be a "
        "duplicate of anything else, so return values unchanged.",
        "Recursive case: rest = remove_duplicates(values[1:]) already "
        "correctly de-duplicates everything after the first element -- "
        "so rest[0], if rest is non-empty, is the next distinct value "
        "after values[0].",
        "If values[0] == values[1], values[0] is a duplicate that should "
        "be dropped -- return rest as-is. Otherwise values[0] is a new "
        "distinct value -- return [values[0]] + rest.",
    ],
    solution="""
def remove_duplicates(values):
    if len(values) <= 1:
        return values
    rest = remove_duplicates(values[1:])
    if values[0] == values[1]:
        return rest
    return [values[0]] + rest
""",
    tests=[
        T("the base cases", """
assert remove_duplicates([]) == []
assert remove_duplicates([5]) == [5]
"""),
        T("runs of duplicates, and none at all", """
assert remove_duplicates([1, 1, 2, 2, 2, 3]) == [1, 2, 3]
assert remove_duplicates([1, 2, 3]) == [1, 2, 3]
"""),
        T("every element the same", """
assert remove_duplicates([4, 4, 4, 4]) == [4]
"""),
        T("random sorted lists, checked against a direct de-dup", """
import random
random.seed(18)
for _ in range(300):
    values = sorted(random.randint(0, 6)
                    for _ in range(random.randint(0, 10)))
    want = []
    for v in values:
        if not want or want[-1] != v:
            want.append(v)
    assert remove_duplicates(values) == want, values
"""),
    ],
)


problem(
    id="all-subsets",
    track="New Shapes of Recursion",
    title="Every Subset: Include It, or Don't",
    difficulty="medium",
    points=20,
    blurb="Two recursive calls representing a choice, not two halves of a computation -- the shape every backtracking search is built from.",
    statement="""
<p>Write <code>all_subsets(values)</code>, returning every subset of
<code>values</code> (as a list of lists; order among the subsets does not
matter). A list of <code>n</code> elements has <code>2 ** n</code>
subsets, including the empty one and the whole list itself.</p>

<p><code>fibonacci</code> made two recursive calls and added their
results together. This one also makes two recursive calls, but they
mean something different: <code>without_first</code> is every subset
that <strong>excludes</strong> <code>values[0]</code>, and pairing
<code>values[0]</code> onto the front of each of those same subsets
gives every subset that <strong>includes</strong> it. Every subset falls
into exactly one of those two groups, so the full answer is both groups
combined.</p>

<p>This "include it, or don't, for every element" pattern is the
foundation of backtracking search -- the same choice, made once per
element, with recursion handling every combination of choices for you.</p>
""",
    examples="""
>>> sorted(all_subsets([]))
[[]]
>>> sorted(all_subsets([1]))
[[], [1]]
>>> sorted(all_subsets([1, 2]))
[[], [1], [1, 2], [2]]
""",
    starter="""
def all_subsets(values):
    pass
""",
    hints=[
        "Base case: the empty list has exactly one subset -- itself. "
        "Return [[]], a list containing one empty list -- not [], which "
        "would mean zero subsets.",
        "Recursive case: without_first = all_subsets(values[1:]). That's "
        "every subset of the rest of the list, already computed, none of "
        "which contain values[0].",
        "with_first = [[values[0]] + subset for subset in without_first] "
        "-- the same subsets, each with values[0] added on. Every real "
        "subset is in exactly one of the two groups, so the answer is "
        "with_first + without_first.",
    ],
    solution="""
def all_subsets(values):
    if not values:
        return [[]]
    without_first = all_subsets(values[1:])
    with_first = [[values[0]] + subset for subset in without_first]
    return with_first + without_first
""",
    tests=[
        T("the empty list has one subset: itself", """
assert all_subsets([]) == [[]]
"""),
        T("small lists against the exact expected sets", """
def norm(subsets):
    return sorted(sorted(s) for s in subsets)

assert norm(all_subsets([1])) == norm([[], [1]])
assert norm(all_subsets([1, 2])) == norm([[], [1], [2], [1, 2]])
"""),
        T("the count is always 2**n, with no duplicates and no omissions", """
import itertools
for n in range(6):
    values = list(range(n))
    subsets = all_subsets(values)
    assert len(subsets) == 2 ** n, (n, len(subsets))
    as_sets = [frozenset(s) for s in subsets]
    assert len(set(as_sets)) == len(as_sets), "a subset was produced twice"
    want = {frozenset(c) for k in range(n + 1)
           for c in itertools.combinations(values, k)}
    assert set(as_sets) == want, values
"""),
    ],
)


HANOI_MOVE_COUNT = {n: 2 ** n - 1 for n in range(8)}


problem(
    id="hanoi-moves",
    track="New Shapes of Recursion",
    title="Towers of Hanoi: the Move List Itself",
    difficulty="medium",
    points=25,
    blurb="Two recursive calls, both used -- and the answer is built by gluing three pieces together, not by comparing or summing them.",
    statement="""
<p>Move <code>n</code> disks from peg <code>source</code> to peg
<code>target</code>, using a third peg <code>spare</code>, one disk at a
time, never placing a bigger disk on a smaller one. Write
<code>hanoi_moves(n, source, target, spare)</code>, returning the full
list of moves as <code>(from_peg, to_peg)</code> pairs, in order.</p>

<p>The classic insight: to move <code>n</code> disks from
<code>source</code> to <code>target</code>, first move the top
<code>n - 1</code> disks out of the way onto <code>spare</code> (using
<code>target</code> as the extra space during that detour), then move
the one big disk directly from <code>source</code> to <code>target</code>,
then move those <code>n - 1</code> disks from <code>spare</code> onto
<code>target</code> (using <code>source</code> as the extra space this
time).</p>

<p>That's <strong>two</strong> recursive calls again, like
<code>all_subsets</code> -- but this time neither call's result gets
compared or filtered. Both lists of moves are used in full, concatenated
together around the one move in the middle.</p>
""",
    examples="""
>>> hanoi_moves(1, "A", "C", "B")
[('A', 'C')]
>>> hanoi_moves(2, "A", "C", "B")
[('A', 'B'), ('A', 'C'), ('B', 'C')]
>>> len(hanoi_moves(3, "A", "C", "B"))
7
""",
    starter="""
def hanoi_moves(n, source, target, spare):
    pass
""",
    hints=[
        "Base case: n == 0. No disks to move, so the list of moves is "
        "empty.",
        "Recursive case, three pieces glued together in order: "
        "hanoi_moves(n - 1, source, spare, target) -- notice target and "
        "spare swap roles here, since target is the extra space during "
        "this detour.",
        "Then one move of your own: (source, target). Then "
        "hanoi_moves(n - 1, spare, target, source) -- here source becomes "
        "the extra space. Concatenate all three with +.",
    ],
    solution="""
def hanoi_moves(n, source, target, spare):
    if n == 0:
        return []
    return (hanoi_moves(n - 1, source, spare, target)
            + [(source, target)]
            + hanoi_moves(n - 1, spare, target, source))
""",
    tests=[
        T("zero disks is no moves at all", """
assert hanoi_moves(0, "A", "C", "B") == []
"""),
        T("one and two disks against the exact expected moves", """
assert hanoi_moves(1, "A", "C", "B") == [("A", "C")]
assert hanoi_moves(2, "A", "C", "B") == [
    ("A", "B"), ("A", "C"), ("B", "C")]
"""),
        T("the move count is always 2**n - 1", """
COUNTS = @@COUNTS@@
for n, want in COUNTS.items():
    got = hanoi_moves(n, "A", "C", "B")
    assert len(got) == want, (n, len(got), want)
""", COUNTS=HANOI_MOVE_COUNT),
        T("every move is legal: no disk ever lands on a smaller one", """
for n in range(1, 7):
    pegs = {"A": list(range(n, 0, -1)), "B": [], "C": []}
    for src, dst in hanoi_moves(n, "A", "C", "B"):
        assert pegs[src], (n, src, dst, "moved from an empty peg")
        disk = pegs[src].pop()
        assert not pegs[dst] or pegs[dst][-1] > disk, (
            n, src, dst, "placed a disk on a smaller one")
        pegs[dst].append(disk)
    assert pegs["C"] == list(range(n, 0, -1)), (n, pegs)
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
