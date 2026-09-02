############################################################
# CIS 521: Homework 3
############################################################

############################################################
# Imports
############################################################

# Include your imports here, if any are used.
import random
from queue import PriorityQueue
import math

############################################################

student_name = "Samarth Shah"

############################################################
# Section 1: Tile Puzzle
############################################################


def create_tile_puzzle(rows, cols):
    grid = [[0]*cols for _ in range(rows)]

    count = 1
    for row in range(0, len(grid)):
        for col in range(0, len(grid[0])):
            grid[row][col] = count
            count += 1

    grid[(rows-1)][(cols-1)] = 0
    return TilePuzzle(grid)


class TilePuzzle(object):

    # Required
    def __init__(self, board):
        self.board = board

    def get_board(self):
        return self.board

    def perform_move(self, direction):
        offsets = {"up": (-1, 0), "down": (1, 0), "left": (0, -1)
                   , "right": (0, 1)}
        if direction not in offsets:
            return False

        rows, cols = len(self.board), len(self.board[0])
        dr, dc = offsets[direction]

        for row in range(rows):
            for col in range(cols):
                if self.board[row][col] == 0:
                    r, c = row + dr, col + dc
                    if 0 <= r < rows and 0 <= c < cols:
                        self.board[row][col], self.board[r][c] = self.board[r][c], self.board[row][col]
                        return True
                    return False

        return False

    def scramble(self, num_moves):
        moves = ["up", "down", "left", "right"]
        for _ in range(num_moves):
            self.perform_move(random.choice(moves))

    def is_solved(self):
        flat = [x for row in self.board for x in row]

        return flat == list(range(1, len(flat))) + [0]

    def copy(self):
        return TilePuzzle([row.copy() for row in self.board])

    def successors(self):
        moves = ["up", "down", "left", "right"]

        for move in moves:
            board_copy = self.copy()
            if board_copy.perform_move(move):
                yield (move, board_copy)

    # Required
    def find_solutions_iddfs(self):

        opposite = {"up": "down", "down": "up", "left": "right", "right"
                    : "left"}

        def iddfs_helper(self, limit, moves):
            if len(moves) == limit:
                if self.is_solved():
                    solutions.append(moves)
                return

            for move, mod_board in self.successors():
                if moves and opposite[moves[-1]] == move:
                    continue

                iddfs_helper(mod_board, limit, moves + [move])

        limit_var = 0
        while True:
            solutions = []
            iddfs_helper(self, limit_var, [])

            if solutions:
                for solution in solutions:
                    yield solution
                return
            limit_var += 1


    # Required
    def find_solution_a_star(self):

        def board_heuristic(puzzle):

            curr_board = puzzle.get_board()
            rows, cols = len(curr_board), len(curr_board[0])
            total_distance = 0

            for row in range(0, rows):
                for col in range(0, cols):
                    curr_val = curr_board[row][col]
                    if curr_val == 0:
                        continue
                    goal_row, goal_col = divmod(curr_val-1, cols)
                    total_distance += abs(goal_row-row)+abs(goal_col-col)
            return total_distance

        counter = 0
        prior_queue = PriorityQueue()
        prior_queue.put((board_heuristic(self), counter, self.copy(), []))
        visited_set = set()

        while not prior_queue.empty():
            curr_cost, curr_count, curr_board, moves = prior_queue.get()
            curr_board_tup = tuple(tuple(row) for row in
                                   curr_board.get_board())

            if curr_board_tup in visited_set:
                continue

            visited_set.add(curr_board_tup)

            if curr_board.is_solved():
                return moves

            for move, mod_board in curr_board.successors():
                a_star_calc = board_heuristic(mod_board) + len(moves) + 1
                counter += 1
                prior_queue.put((a_star_calc, counter, mod_board.copy()
                                 , moves + [move]))

        return None



############################################################
# Section 2: Grid Navigation
############################################################


def find_path(start, goal, scene):

    if scene[start[0]][start[1]] or scene[goal[0]][goal[1]]:
        return None

    rows, cols = len(scene), len(scene[0])

    def board_heuristic(curr_pos):
        a = curr_pos[0] - goal[0]
        b = curr_pos[1] - goal[1]

        return math.sqrt(a**2 + b**2)

    counter = 0
    priority_queue = PriorityQueue()
    priority_queue.put((board_heuristic(start), counter, [start]))
    visited_set = set()

    directions = [(-1, 0), (1, 0), (0, 1), (0, -1),
                  (1, 1), (1, -1), (-1, 1), (-1, -1)]

    while not priority_queue.empty():
        curr_cost, _, curr_moves = priority_queue.get()
        curr_pos = curr_moves[-1]

        if curr_pos in visited_set:
            continue

        visited_set.add(curr_pos)

        if curr_pos == goal:
            return curr_moves

        curr_pos_row, curr_pos_col = curr_pos

        for direction in directions:
            mod_row = curr_pos_row + direction[0]
            mod_col = curr_pos_col + direction[1]

            if (0 <= mod_row < rows and 0 <= mod_col < cols
                    and not scene[mod_row][mod_col]):
                mod_pos = (mod_row, mod_col)
                step_cost = math.sqrt(direction[0]**2 + direction[1]**2)
                a_star_calc = (curr_cost - board_heuristic(curr_pos)
                               + step_cost + board_heuristic(mod_pos))
                counter += 1
                priority_queue.put((a_star_calc, counter,
                                    curr_moves + [mod_pos]))

    return None

############################################################
# Section 3: Linear Disk Movement, Revisited
############################################################


def solve_distinct_disks(length, n):

    grid = [0]*length
    for i in range(0, n):
        grid[i] = i+1
    grid = tuple(grid)

    goal = [0]*length
    for i in range((length-n), length):
        goal[i] = length - i
    goal = tuple(goal)

    def board_heuristic(curr_board):

        total_distance = 0

        for i in range(0, len(curr_board)):
            curr_val = curr_board[i]
            if curr_val == 0:
                continue
            total_distance += abs(i - (length - curr_val))

        return total_distance / 2

    priority_queue = PriorityQueue()
    visited_set = set()
    parents = {}
    counter = 0
    priority_queue.put((board_heuristic(grid), counter, 0, grid, None, None))

    directions = [1, 2, -1, -2]

    while not priority_queue.empty():
        (curr_cost, curr_count, curr_g, curr_board,
         prev_board, prev_move) = priority_queue.get()

        if curr_board in visited_set:
            continue

        visited_set.add(curr_board)
        parents[curr_board] = (prev_board, prev_move)

        if curr_board == goal:
            curr_moves = []
            board = curr_board
            while parents[board][0] is not None:
                board, move = parents[board]
                curr_moves.append(move)
            curr_moves.reverse()
            return curr_moves

        for i in range(0, len(curr_board)):
            if curr_board[i] != 0:

                for direction in directions:
                    mod_pos = direction + i

                    if direction == 1 and mod_pos < length and curr_board[mod_pos] == 0:
                        curr_board_copy = list(curr_board)
                        curr_board_copy[i], curr_board_copy[mod_pos] = curr_board_copy[mod_pos], curr_board_copy[i]
                        curr_board_copy = tuple(curr_board_copy)
                        if curr_board_copy in visited_set:
                            continue
                        counter += 1
                        priority_queue.put((board_heuristic(curr_board_copy) + curr_g + 1, counter, curr_g + 1, curr_board_copy, curr_board, (i, i+1)))
                    if direction == 2 and mod_pos < length and curr_board[mod_pos] == 0 and curr_board[mod_pos-1] != 0:
                        curr_board_copy = list(curr_board)
                        curr_board_copy[i], curr_board_copy[mod_pos] = curr_board_copy[mod_pos], curr_board_copy[i]
                        curr_board_copy = tuple(curr_board_copy)
                        if curr_board_copy in visited_set:
                            continue
                        counter += 1
                        priority_queue.put((board_heuristic(curr_board_copy) + curr_g + 1, counter, curr_g + 1, curr_board_copy, curr_board, (i, i+2)))
                    if direction == -1 and mod_pos >= 0 and curr_board[mod_pos] == 0:
                        curr_board_copy = list(curr_board)
                        curr_board_copy[i], curr_board_copy[mod_pos] = curr_board_copy[mod_pos], curr_board_copy[i]
                        curr_board_copy = tuple(curr_board_copy)
                        if curr_board_copy in visited_set:
                            continue
                        counter += 1
                        priority_queue.put((board_heuristic(curr_board_copy) + curr_g + 1, counter, curr_g + 1, curr_board_copy, curr_board, (i, i-1)))
                    if direction == -2 and mod_pos >= 0 and curr_board[mod_pos] == 0 and curr_board[mod_pos+1] != 0:
                        curr_board_copy = list(curr_board)
                        curr_board_copy[i], curr_board_copy[mod_pos] = curr_board_copy[mod_pos], curr_board_copy[i]
                        curr_board_copy = tuple(curr_board_copy)
                        if curr_board_copy in visited_set:
                            continue
                        counter += 1
                        priority_queue.put((board_heuristic(curr_board_copy) + curr_g + 1, counter, curr_g + 1, curr_board_copy, curr_board, (i, i-2)))

    return None



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
