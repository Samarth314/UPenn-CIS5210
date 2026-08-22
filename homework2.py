############################################################
# CIS 521: Homework 2
############################################################

############################################################
# Imports
############################################################

# Include your imports here, if any are used.

############################################################

student_name = "Samarth Shah"

############################################################
# Section 1: N-Queens
############################################################


def num_placements_all(n):
    import math
    return math.comb(n**2, n)


def num_placements_one_per_row(n):
    return n**n


def n_queens_valid(board):

    # [
    # X  .  .
    # .  .  X
    # ]
    # 2 X 3 GRID (INPUT: [0, 2])

    grid = []
    for i in range(0, len(board)):
        row = i
        col = board[i]
        grid.append((row, col))

    for i in range(0, len(grid)):

        curr_row = grid[i][0]
        curr_col = grid[i][1]

        for j in range(i+1, len(grid)):

            curr_row1 = grid[j][0]
            curr_col1 = grid[j][1]

            if (curr_row == curr_row1
                    or curr_col == curr_col1
                    or abs(curr_row - curr_row1)
                    == abs(curr_col - curr_col1)):
                return False

    return True


# need to change all of the naming stuff for helper below
def n_queens_solutions(n):

    grid = [0]*n

    solutions = []

    def dfs_tree(board, row):
        n = len(board)

        if row == n:
            solutions.append(board[:])
            return

        for col in range(0, n):
            board[row] = col
            if n_queens_valid(board[:(row+1)]):
                dfs_tree(board, row+1)
            board[row] = 0

    dfs_tree(grid, 0)
    return solutions

############################################################
# Section 2: Lights Out
############################################################


class LightsOutPuzzle(object):

    def __init__(self, board):
        self.lights_board = board

    def get_board(self):
        return self.lights_board

    def perform_move(self, row, col):

        self.lights_board[row][col] = not self.lights_board[row][col]

        if (row - 1 >= 0):
            self.lights_board[row - 1][col] = not self.lights_board[
                row - 1][col]
        if (row + 1 < len(self.lights_board)):
            self.lights_board[row + 1][col] = not self.lights_board[
                row + 1][col]
        if (col - 1 >= 0):
            self.lights_board[row][col - 1] = not self.lights_board[row][
                col - 1]
        if (col + 1 < len(self.lights_board[0])):
            self.lights_board[row][col + 1] = not self.lights_board[row][
                col + 1]

    def scramble(self):
        import random

        rows, cols = len(self.lights_board), len(self.lights_board[0])

        for row in range(rows):
            for col in range(cols):
                if random.random() < 0.5:
                    self.perform_move(row, col)

    def is_solved(self):
        return not any(True in row for row in self.lights_board)

    def copy(self):

        new_lights_board = []

        for row in self.lights_board:
            new_lights_board.append(row.copy())

        return LightsOutPuzzle(new_lights_board)

    def successors(self):

        for row in range(0, len(self.lights_board)):
            for col in range(0, len(self.lights_board[0])):
                lights_board_copy = self.copy()
                lights_board_copy.perform_move(row, col)
                yield ((row, col), lights_board_copy)

    def find_solution(self):

        from collections import deque
        queue = deque()
        visited_set = set()

        queue.append((self.copy(), []))

        while queue:

            entry, moves = queue.popleft()

            board_tuple = tuple(tuple(row) for row in entry.get_board())

            if board_tuple in visited_set:
                continue

            visited_set.add(board_tuple)

            if entry.is_solved():
                return moves

            for successor in entry.successors():
                move = successor[0]
                puzzle = successor[1]

                queue.append((puzzle, moves + [move]))

        return None


def create_puzzle(rows, cols):
    return LightsOutPuzzle([[False] * cols for _ in range(rows)])

############################################################
# Section 3: Linear Disk Movement
############################################################


def solve_identical_disks(length, n):
    from collections import deque

    disk_arr = [0]*length
    for i in range(0, n):
        disk_arr[i] = 1
    # [1, 1, 0, 0] / [1, 1, 0, 0, 0]

    moves = []

    queue = deque()
    visited_set = set()

    queue.append((disk_arr, []))

    while queue:
        entry, moves = queue.popleft()

        entry_tuple = tuple(entry)

        if entry_tuple in visited_set:
            continue

        visited_set.add(entry_tuple)

        if 0 not in entry[(length-n):]:
            return moves

        for i in range(0, length):
            if entry[i] == 1:

                if (i + 1) < length and entry[i + 1] == 0:
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i + 1] = new_entry[
                        i + 1], new_entry[i]
                    queue.append((new_entry, moves + [(i, i + 1)]))

                if ((i + 2) < length and
                        entry[i + 2] == 0 and
                        entry[i + 1] == 1):
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i + 2] = new_entry[
                        i + 2], new_entry[i]
                    queue.append((new_entry, moves + [(i, i + 2)]))

                if (i - 1) >= 0 and entry[i - 1] == 0:
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i - 1] = new_entry[
                        i - 1], new_entry[i]
                    queue.append((new_entry, moves + [(i, i - 1)]))

                if (i - 2) >= 0 and entry[i - 2] == 0 and entry[i - 1] == 1:
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i - 2] = new_entry[
                        i - 2], new_entry[i]
                    queue.append((new_entry, moves + [(i, i - 2)]))

    return None


def solve_distinct_disks(length, n):
    from collections import deque

    queue = deque()
    visited_set = set()

    disks = [-1]*length
    for i in range(0, n):
        disks[i] = i

    # [1, 1, -1, -1] / [1, 1, -1, -1, -1]

    queue.append((disks, []))

    while queue:
        entry, moves = queue.popleft()

        entry_tuple = tuple(entry)

        if entry_tuple in visited_set:
            continue

        visited_set.add(entry_tuple)

        goal = True

        for i in range(0, n):
            if entry[length - 1 - i] != i:
                goal = False
                break

        if goal:
            return moves

        for i in range(0, length):
            if entry[i] != -1:
                if (i + 1) < length and entry[i + 1] == -1:
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i + 1] = new_entry[
                        i + 1], new_entry[i]
                    queue.append((new_entry, moves + [(i, i + 1)]))

                if ((i + 2) < length and
                        entry[i + 2] == -1 and
                        entry[i + 1] != -1):
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i + 2] = new_entry[
                        i + 2], new_entry[i]
                    queue.append((new_entry, moves + [(i, i + 2)]))

                if (i - 1) >= 0 and entry[i - 1] == -1:
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i - 1] = new_entry[
                        i - 1], new_entry[i]
                    queue.append((new_entry, moves + [(i, i - 1)]))

                if ((i - 2) >= 0 and
                        entry[i - 2] == -1 and
                        entry[i - 1] != -1):
                    new_entry = entry.copy()
                    new_entry[i], new_entry[i - 2] = new_entry[
                        i - 2], new_entry[i]
                    queue.append((new_entry, moves + [(i, i - 2)]))

    return None

############################################################
# Section 4: Feedback
############################################################


# Just an approximation is fine.
feedback_question_1 = """
4 hours
"""

feedback_question_2 = """
The aspects of this assignment I found the most challenging were Section 1:
N-Queens and Section 3: Linear Disk Movement. Section 1 was a little tricky
because it took some time to understand how to use recursion to discover all
of the possible board configurations. It also took some time to understand
how a board (2D object) can be represented as a 1D list, as each index of the
list represented each row. Section 3 was very challenging as it took time to
figure out how to represent the board and generate all of the possible moves
while also ensuring that my BFS solution would return the solution with a
minimum number of moves.
"""

feedback_question_3 = """
I liked the gradual development of the search algorithms needed for this
assignment as it started off on the easier side and gradually got harder.
The N-Queens problem allowed me to better understand how DFS can be used to
explore different possibilities. The other BFS-involved problems allowed me
to better understand how to use search algorithms to find shortest solutions.
I liked the Linear Disk Movement section as representing the board as a list
and then uncovering the possible moves made it easier for me to visualize and
draw out the search process. Something I would change is adding more example
test cases to each problem to help me and other students look at different
possibilities for inputs to better program the functions.
"""
