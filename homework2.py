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

            if (curr_row == curr_row1 or curr_col == curr_col1
            or abs(curr_row - curr_row1) == abs(curr_col - curr_col1)):
                return False

    return True


# need to change all of the naming stuff for helper below
def n_queens_solutions(n):

    grid = [0]*n

    solutions = []

    def dfs_tree(board, row):
        n = len(board)

        if row == n:
            if n_queens_valid(board):
                solutions.append(board[:])
                return

        for col in range(0, n):
            board[row] = col
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
            self.lights_board[row - 1][col] = not self.lights_board[row - 1][col]
        if (row + 1 < len(self.lights_board)):
            self.lights_board[row + 1][col] = not self.lights_board[row + 1][col]
        if (col - 1 >= 0):
            self.lights_board[row][col - 1] = not self.lights_board[row][col - 1]
        if (col + 1 < len(self.lights_board[0])):
            self.lights_board[row][col + 1] = not self.lights_board[row][col + 1]

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
        pass

    def successors(self):
        pass

    def find_solution(self):
        pass


def create_puzzle(rows, cols):
    return LightsOutPuzzle([[False] * cols for _ in range(rows)])

############################################################
# Section 3: Linear Disk Movement
############################################################


def solve_identical_disks(length, n):
    pass


def solve_distinct_disks(length, n):
    pass

############################################################
# Section 4: Feedback
############################################################


# Just an approximation is fine.
feedback_question_1 = """
Type your response here.
Your response may span multiple lines.
Do not include these instructions in your response.
"""

feedback_question_2 = """
Type your response here.
Your response may span multiple lines.
Do not include these instructions in your response.
"""

feedback_question_3 = """
Type your response here.
Your response may span multiple lines.
Do not include these instructions in your response.
"""
