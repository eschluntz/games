#!/usr/bin/env python3

import time
from typing import Tuple

import numpy as np

WIN_SCORE = 1000


class TicTacToeBoard(object):
    TURNS = ["x", "o"]

    def __init__(self, turn="x"):
        # 3x3 array of chars. ["", "x", "o"]
        self.board = np.full(shape=(3, 3), fill_value=" ", dtype="<U1")
        self.past_moves = []  # used to pop off and undo moves
        self.turn = turn  # "x" or "o"

    def __str__(self):
        output = ""
        for i, row in enumerate(self.board):

            # create underlines to draw the board more compactly
            if i != len(self.board) - 1:
                prefix = "\033[4m"
                postfix = "\033[0m"
            else:
                prefix, postfix = "", ""

            row = prefix + "|".join(row) + postfix + "\n"
            output += row
        return output

    def moves(self):
        """Returns list of available moves, as (r,c) tuples.
        Note: this is actually the same no matter who's turn it is"""
        rs, cs = np.where(self.board == " ")  # get empty spaces
        return list(zip(rs, cs))  # turn two lists into list of tuples of spots

    def next_turn(self):
        """Returns the "x" or "o", whichever is not our current turn"""
        if self.turn == "x":
            return "o"
        else:
            return "x"

    def do_move(self, move):
        """Updates the game board object with the new move taken
        and the next player's turn set.
        move: (r, c) tuple of ints."""

        self.board[move] = self.turn
        self.turn = self.next_turn()
        self.past_moves.append(move)

    def undo_move(self):
        """Pops the last move off the stack"""
        last_move = self.past_moves.pop()
        self.board[last_move] = " "
        self.turn = self.next_turn()


def eval_tictactoe(board) -> Tuple[int, bool]:
    """Evaluates a tictactoe board.
    "x" winning -> positive
    "o" winning -> negative.
    game over -> +/- 1000.
    return (score, game_over)
    """
    for team, team_direction in [("x", 1), ("o", -1)]:

        # I'm not clever enough to come up wth this myself
        # https://stackoverflow.com/questions/46802651/check-for-winner-in-tic-tac-toe-numpy-python
        mask = board.board == team
        win = (
            mask.all(0).any()
            or mask.all(1).any()  # columns
            or np.diag(mask).all()  # rows
            or np.diag(mask[:, ::-1]).all()  # down right  # up right
        )

        if win:
            return team_direction * WIN_SCORE, True

    # check if it's a tie game
    open_positions = np.sum(board.board == " ")
    tie_game = open_positions == 0
    return 0, tie_game


TRANSPOSITION_TABLE = {}
# Maps (board+depth) -> score to avoid repeated work and improve move ordering
# key: str(board.board.flatten()) + depth


def iterative_deepening(board, eval_fn, max_depth, max_t=10.0):
    """Iteratively calls minmax with higher depths.
    1. this allows us to gracefully add a time limit.
    2. NOTE: should fill up the transposition table for better move ordering,
    but using that for move ordering doesn't seem to be better than the straight eval_fn

    Returns: (score, move)
    """
    t0 = time.time()
    score, move = None, None
    for depth in range(max_depth + 1):
        tot_t = time.time() - t0
        if tot_t > max_t:
            break
        score, move = minmax(board, eval_fn, depth)
    return score, move


def minmax(board, eval_fn, max_depth, alpha=-np.inf, beta=np.inf):
    """Finds the best move using MinMax and AlphaBeta pruning.
    Hopefully this function can be used across many different games!

    board: board representation with this interface:
        [...] = board.moves()
        board.do_move(move)
        board.undo_move()
    eval_fn: a function that transforms a board into a score
        score, over = eval_fn(board)
    max_depth: how many more layers to search.
    alpha:  worst possible score for "x" = -inf
    beta:   worst possible score for "o" = +inf


    TODO: make it prefer victories that are sooner, or defeats that are later.
    TODO: sort possible moves by the eval_fn heuristic to improve pruning

    returns: (score, move) the expected score down that path.
    """

    # base cases
    score, done = eval_fn(board)
    if done or max_depth == 0:
        return score, None

    # are we maxing or mining?
    direction = 1.0 if board.turn in ["x", "white"] else -1.0

    # loop!
    best_move = None
    best_score = -np.inf * direction

    all_moves = board.moves()

    # order these nicely to improve alpha beta pruning
    def score_move_heuristic(move):
        board.do_move(move)
        score, _ = eval_fn(board)
        board.undo_move()
        return score

    all_moves.sort(key=score_move_heuristic, reverse=(board.turn == "white"))  # TODO: fix white / x

    # we've already sorted
    if max_depth == 1:
        move = all_moves[0]
        board.do_move(move)
        score, _ = eval_fn(board)
        board.undo_move()
        return score, move

    # search the tree!
    for move in all_moves:
        board.do_move(move)
        # add to transposition table
        key = "".join(board.board.flatten()) + str(max_depth - 1)

        if key in TRANSPOSITION_TABLE:
            score = TRANSPOSITION_TABLE[key]
        else:
            score, _ = minmax(board, eval_fn, max_depth - 1, alpha, beta)
            TRANSPOSITION_TABLE[key] = score

        board.undo_move()

        if score * direction > best_score * direction:
            best_score = score
            best_move = move

        # update heuristics
        if direction > 0:
            alpha = max(alpha, score)  # only if max
        else:
            beta = min(beta, score)  # only if min
        if beta <= alpha:  # we know the parent won't choose us. abandon the search!
            break

    return best_score, best_move


def play_game():
    """Play a friendly game of tic tac toe against the AI"""
    b = TicTacToeBoard()
    while True:
        rc_str = input("row, column: ")
        move = eval(rc_str)  # careful with your input :p
        b.do_move(move)
        print(b)
        score, over = eval_tictactoe(b)
        if over:
            if score == WIN_SCORE:
                print("You win!")
                return WIN_SCORE
            else:
                print("Tie!")
                return 0

        score, move = minmax(b, eval_tictactoe, 9)
        b.do_move(move)
        print(b)
        score, over = eval_tictactoe(b)
        if over:
            if score == -WIN_SCORE:
                print("You lose!")
                return -WIN_SCORE
            else:
                print("Tie!")
                return 0


def time_game():
    """Generate a list of execution times for different search depths"""
    for depth in range(15):
        b = TicTacToeBoard()
        b.board[0, 0] = "o"

        t0 = time.time()
        minmax(b, eval_tictactoe, depth)
        t1 = time.time()
        print((depth, t1 - t0))


if __name__ == "__main__":
    play_game()
