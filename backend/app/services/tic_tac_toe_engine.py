"""
Tic Tac Toe game engine — contains ALL core game rules.
No database operations, no AI logic — pure game mechanics.
"""
from typing import Literal

BoardType = list[list[str]]
MoveType = tuple[int, int]

# Win conditions: rows, columns, and diagonals
WIN_CONDITIONS = [
    # Rows
    [(0, 0), (0, 1), (0, 2)],
    [(1, 0), (1, 1), (1, 2)],
    [(2, 0), (2, 1), (2, 2)],
    # Columns
    [(0, 0), (1, 0), (2, 0)],
    [(0, 1), (1, 1), (2, 1)],
    [(0, 2), (1, 2), (2, 2)],
    # Diagonals
    [(0, 0), (1, 1), (2, 2)],
    [(0, 2), (1, 1), (2, 0)],
]


def create_empty_board() -> BoardType:
    """Create a new empty 3x3 board."""
    return [["", "", ""], ["", "", ""], ["", "", ""]]


def copy_board(board: BoardType) -> BoardType:
    """Create a deep copy of the board."""
    return [row[:] for row in board]


def is_valid_move(board: BoardType, row: int, col: int) -> bool:
    """Check if a move is valid (within bounds and cell is empty)."""
    if not (0 <= row <= 2 and 0 <= col <= 2):
        return False
    return board[row][col] == ""


def apply_move(board: BoardType, row: int, col: int, symbol: str) -> BoardType:
    """Apply a move to the board and return the new board state."""
    new_board = copy_board(board)
    new_board[row][col] = symbol
    return new_board


def get_available_moves(board: BoardType) -> list[MoveType]:
    """Return all empty cells as (row, col) tuples."""
    moves = []
    for row in range(3):
        for col in range(3):
            if board[row][col] == "":
                moves.append((row, col))
    return moves


def check_winner(board: BoardType) -> str | None:
    """Check if there's a winner. Returns 'X', 'O', or None."""
    for condition in WIN_CONDITIONS:
        cells = [board[r][c] for r, c in condition]
        if cells[0] != "" and cells[0] == cells[1] == cells[2]:
            return cells[0]
    return None


def is_board_full(board: BoardType) -> bool:
    """Check if the board is completely filled."""
    return len(get_available_moves(board)) == 0


def get_game_status(board: BoardType) -> tuple[Literal["in_progress", "completed", "draw"], str | None]:
    """
    Determine game status and winner.
    Returns (status, winner).
    """
    winner = check_winner(board)
    if winner:
        return "completed", winner
    if is_board_full(board):
        return "draw", None
    return "in_progress", None


def get_opponent(symbol: str) -> str:
    """Get the opponent's symbol."""
    return "O" if symbol == "X" else "X"


def count_symbol(board: BoardType, symbol: str) -> int:
    """Count occurrences of a symbol on the board."""
    count = 0
    for row in board:
        for cell in row:
            if cell == symbol:
                count += 1
    return count


def validate_board_state(board: BoardType) -> bool:
    """Validate that a board state is structurally valid."""
    if not isinstance(board, list) or len(board) != 3:
        return False
    for row in board:
        if not isinstance(row, list) or len(row) != 3:
            return False
        for cell in row:
            if cell not in ("", "X", "O"):
                return False
    return True
