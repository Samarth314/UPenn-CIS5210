############################################################
# CIS 521: Homework 4
############################################################

############################################################
# Imports
############################################################

# Include your imports here, if any are used.
import collections
import copy
import itertools
import random
import math

############################################################

student_name = "Samarth Shah"

############################################################
# Section 1: Dominoes Game
############################################################


def create_dominoes_game(rows, cols):
    return DominoesGame([[False]*cols for _ in range(rows)])


class DominoesGame(object):

    # Required
    def __init__(self, board):
        self.board = board

    def get_board(self):
        return self.board

    def reset(self):
        for row in range(0, len(self.board)):
            for col in range(0, len(self.board[0])):
                self.board[row][col] = False

    def is_legal_move(self, row, col, vertical):
        rows, cols = len(self.board), len(self.board[0])
        if vertical:
            if (0 <= row < rows and 0 <= (row+1) < rows
                    and 0 <= col < cols):
                if self.board[row][col] or self.board[row+1][col]:
                    return False
            else:
                return False
        else:
            if (0 <= row < rows and 0 <= (col+1) < cols
                    and 0 <= col < cols):
                if self.board[row][col] or self.board[row][col+1]:
                    return False
            else:
                return False
        return True

    def legal_moves(self, vertical):
        for row in range(0, len(self.board)):
            for col in range(0, len(self.board[0])):
                if self.is_legal_move(row, col, vertical):
                    yield (row, col)

    def perform_move(self, row, col, vertical):
        row1, col1 = row, col
        if vertical:
            row2, col2 = row+1, col
        else:
            row2, col2 = row, col+1
        self.board[row1][col1] = True
        self.board[row2][col2] = True

    def game_over(self, vertical):

        return next(self.legal_moves(vertical), None) is None

    def copy(self):
        return DominoesGame([row.copy() for row in self.board])

    def successors(self, vertical):
        for row, col in self.legal_moves(vertical):
            board_copy = self.copy()
            board_copy.perform_move(row, col, vertical)
            yield ((row, col), board_copy)

    def get_random_move(self, vertical):
        return random.choice(list(self.legal_moves(vertical)))

    # Required
    def get_best_move(self, vertical, limit):

        def eval_func(game):
            return (len(list(game.legal_moves(vertical)))
                    - len(list(game.legal_moves(not vertical))))

        def max_func(game, vert_flag, a, b, depth):
            if depth == 0 or game.game_over(vert_flag):
                return eval_func(game), None, 1

            value, moves, leaves = float('-inf'), None, 0

            for mod_move, mod_board in game.successors(vert_flag):
                v2, m2, l2 = min_func(mod_board, not vert_flag, a, b, depth-1)
                leaves += l2

                if v2 > value:
                    value, moves = v2, mod_move

                a = max(a, value)
                if value >= b:
                    return value, moves, leaves

            return value, moves, leaves

        def min_func(game, vert_flag, a, b, depth):
            if depth == 0 or game.game_over(vert_flag):
                return eval_func(game), None, 1

            value, moves, leaves = float('inf'), None, 0

            for mod_move, mod_board in game.successors(vert_flag):
                v2, m2, l2 = max_func(mod_board, not vert_flag, a, b, depth-1)
                leaves += l2

                if v2 < value:
                    value, moves = v2, mod_move

                b = min(b, value)
                if value <= a:
                    return value, moves, leaves

            return value, moves, leaves

        value, moves, leaves = max_func(
            self, vertical, float('-inf'), float('inf'), limit)
        return moves, value, leaves

############################################################
# Section 2: Feedback
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
