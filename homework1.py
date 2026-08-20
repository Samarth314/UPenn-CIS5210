import numpy
import nltk

############################################################
# CIS 521: Homework 1
############################################################

student_name = "Samarth Shah"

# This is where your grade report will be sent.
student_email = "samarts@engineering.upenn.edu"

############################################################
# Section 1: Python Concepts
############################################################

python_concepts_question_1 = """Python being strongly typed means it has
strict rules on various data types and will not permit implicit type
conversions. Once a Python object has a specific type, Python will not allow
the type to be altered. If this is tried, it will result in a TypeError. An
example is: result = "Age: " + 25 → TypeError: can only concatenate str (not
"int") to str. Python is also dynamically typed which entails that the
interpreter verifies and enforces data types for Python objects during
runtime instead of compilation. With Python, you do not need to declare the
types of variables explicitly. An example is: x = 10, print(type(x)) → <class
'int'>. x = "Hello", print(type(x)) → <class 'str'>. The only drawback is
type errors are caught at runtime."""

python_concepts_question_2 = """The problem with this Python statement is
lists are mutable and unhashable, and thus cannot be used as dictionary keys.
Dictionary keys in Python must be immutable and hashable. A solution to this
problem can be using tuples instead of lists as tuples and immutable and
hashable which would permit them to be used as dictionary keys. Here's what
the revised statement would look like with this solution: points_to_names =
{(0, 0): 'home', (1, 2): 'school', (-1, 1): 'market'}"""

python_concepts_question_3 = """The function concatenate2 is faster than
concatenate1. concatenate1 does result += s repeatedly and because strings
are immutable in Python, this would result in a new string being created each
iteration of the for-loop which is inefficient for memory allocation. As the
result gets longer, more characters would be copied each time and this would
lead to a slower runtime and worse memory allocation. concatenate2 uses the
join function which uses the final size and builds the result string in one
operation which would result in better memory allocation and faster runtime.
Therefore, concatenate2 is the better approach, especially for larger inputs.
"""

############################################################
# Section 2: Working with Lists
############################################################


def extract_and_apply(lst, p, f):
    return [f(elem) for elem in lst if p(elem)]


def concatenate(seqs):
    return [elem for seq in seqs for elem in seq]


def transpose(matrix):
    res = []

    for j in range(0, len(matrix[0])):
        column = []

        for i in range(0, len(matrix)):
            column.append(matrix[i][j])
        res.append(column)

    return res

############################################################
# Section 3: Sequence Slicing
############################################################


def copy(seq):
    return seq[:]


def all_but_last(seq):
    return seq[:-1]


def every_other(seq):
    return seq[::2]

############################################################
# Section 4: Combinatorial Algorithms
############################################################


def prefixes(seq):
    for i in range(0, len(seq)+1):
        yield seq[:i]


def suffixes(seq):
    for i in range(0, len(seq)+1):
        yield seq[i:]


def slices(seq):
    for i in range(0, len(seq)):
        for j in range(i+1, len(seq)+1):
            yield seq[i:j]

############################################################
# Section 5: Text Processing
############################################################


def normalize(text):
    res = text.lower().split()
    return " ".join(res)


def no_vowels(text):
    vowels = "aeiouAEIOU"
    return "".join([char for char in text if char not in vowels])


def digits_to_words(text):
    number_map = {
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
        "4": "four",
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
        "9": "nine"
    }

    return " ".join([number_map[char] for char in text if char in number_map])


def to_mixed_case(name):
    strs = [char for char in name.lower().split("_") if char]
    if not strs:
        return ""
    res = strs[0]

    for i in range(1, len(strs)):
        res += strs[i][0].upper() + strs[i][1:]

    return res

############################################################
# Section 6: Polynomials
############################################################


class Polynomial(object):

    def __init__(self, polynomial):
        self.polynomial = tuple(polynomial)

    def get_polynomial(self):
        return self.polynomial

    def __neg__(self):
        return Polynomial([(-coeff, power)
                           for (coeff, power) in
                           self.polynomial])

    def __add__(self, other):
        return Polynomial(self.polynomial + other.polynomial)

    def __sub__(self, other):
        return Polynomial(self.polynomial + (-other).polynomial)

    def __mul__(self, other):
        return Polynomial([
            (coeff1*coeff2, power1+power2)
            for (coeff1, power1) in self.polynomial
            for (coeff2, power2) in other.polynomial
        ])

    def __call__(self, x):
        return sum(coeff*(x**power) for (coeff, power) in self.polynomial)

    def simplify(self):
        tup_list = list(self.polynomial)
        tup_list.sort(key=lambda x: x[1], reverse=True)

        result = []
        i = 0

        while i < len(tup_list):

            coeff, power = tup_list[i]

            j = i + 1

            while j < len(tup_list) and tup_list[j][1] == power:
                coeff += tup_list[j][0]
                j += 1

            if coeff != 0:
                result.append((coeff, power))
            i = j

        if not result:
            result = [(0, 0)]
        self.polynomial = tuple(result)

    def __str__(self):
        parts = []
        for i, (coeff, power) in enumerate(self.polynomial):
            neg = coeff < 0
            mag = abs(coeff)
            if power == 0:
                term = str(mag)
            else:
                coeff_part = "" if mag == 1 else str(mag)
                power_part = "x" if power == 1 else "x^{}".format(power)
                term = coeff_part + power_part
            if i == 0:
                sign_str = "-" if neg else ""
                parts.append(sign_str + term)
            else:
                sign_str = "-" if neg else "+"
                parts.append(sign_str)
                parts.append(term)
        return " ".join(parts)

############################################################
# Section 7: Python Packages
############################################################


def sort_array(list_of_matrices):
    all_vals = numpy.concatenate([numpy.array(m).flatten()
                                  for m in list_of_matrices])
    return numpy.sort(all_vals)[::-1].astype(int)


def POS_tag(sentence):
    import string
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize

    sentence = sentence.lower()
    tokens = word_tokenize(sentence)
    stop_words = set(stopwords.words('english'))
    filtered = [w for w in tokens if w not in stop_words and
                w not in string.punctuation]
    return nltk.pos_tag(filtered)

############################################################
# Section 8: Feedback
############################################################


# Just an approximation is fine.
feedback_question_1 = """
4 hours
"""

feedback_question_2 = """
The aspects of this assignment I found the most challenging were
Section 6: Polynomials and Section 7: Python Packages. For section 6,
determining whether self.polynomial should be a plain tuple as opposed
to a Polynomial object. It was also a little tricky to figure out how to
implement the simplify() method correctly. For section 7, it took a while
to figure out how to use np.sort() on a list of differently-shaped matrices.
With NLTK, it took some time to figure out how to make sure the stopword and
punctuation removals happened after lowercasing and tokenizing on the input.
"""

feedback_question_3 = """
I enjoyed the way the Polynomial part developed gradually because the use of
__neg__, __add__ and __mul__ first enabled me to re-use those operators to
implement more complex methods such as __sub__ and __call__.
The __str__ operator was my favorite because the way of matching all special
cases (including zero coefficients, coefficients of magnitude 1, power 0 vs
power 1) to match conventional math notation was a fun puzzle to decipher.
What I would have changed is adding some example test cases for simplify
and __str__ because those were the parts which contained many special cases
and one could easily pass the examples without working implementations
of those operators on other inputs."""
