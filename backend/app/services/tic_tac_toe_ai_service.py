"""
Tic Tac Toe AI service — deterministic Minimax algorithm.
No external API calls, no LLM dependency.
"""
import math
from typing import Literal

from app.services.tic_tac_toe_engine import (
    BoardType,
    MoveType,
    apply_move,
    check_winner,
    copy_board,
    get_available_moves,
    is_board_full,
)


def minimax(
    board: BoardType,
    depth: int,
    is_maximizing: bool,
    ai_symbol: str,
    player_symbol: str,
    alpha: float = -math.inf,
    beta: float = math.inf,
) -> int:
    """
    Minimax algorithm with alpha-beta pruning.
    
    Args:
        board: Current board state
        depth: Current depth in the game tree
        is_maximizing: True if it's the AI's turn (maximizing)
        ai_symbol: The AI's symbol ('X' or 'O')
        player_symbol: The human player's symbol
        alpha: Alpha value for pruning
        beta: Beta value for pruning
    
    Returns:
        Score: +10 for AI win, -10 for player win, 0 for draw
    """
    winner = check_winner(board)
    
    # Terminal states
    if winner == ai_symbol:
        return 10 - depth  # Prefer faster wins
    if winner == player_symbol:
        return depth - 10  # Prefer slower losses
    if is_board_full(board):
        return 0  # Draw
    
    if is_maximizing:
        max_eval = -math.inf
        for row, col in get_available_moves(board):
            new_board = apply_move(board, row, col, ai_symbol)
            eval_score = minimax(new_board, depth + 1, False, ai_symbol, player_symbol, alpha, beta)
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Prune
        return max_eval
    else:
        min_eval = math.inf
        for row, col in get_available_moves(board):
            new_board = apply_move(board, row, col, player_symbol)
            eval_score = minimax(new_board, depth + 1, True, ai_symbol, player_symbol, alpha, beta)
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Prune
        return min_eval


def get_best_move(board: BoardType, ai_symbol: str) -> MoveType | None:
    """
    Find the best move for the AI using Minimax.
    
    Args:
        board: Current board state
        ai_symbol: The AI's symbol ('X' or 'O')
    
    Returns:
        Best move as (row, col) tuple, or None if no moves available
    """
    player_symbol = "X" if ai_symbol == "O" else "O"
    available_moves = get_available_moves(board)
    
    if not available_moves:
        return None
    
    best_score = -math.inf
    best_move: MoveType | None = None
    
    for row, col in available_moves:
        new_board = apply_move(board, row, col, ai_symbol)
        score = minimax(new_board, 0, False, ai_symbol, player_symbol)
        
        if score > best_score:
            best_score = score
            best_move = (row, col)
    
    return best_move


def analyze_board(board: BoardType, ai_symbol: str) -> dict:
    """
    Analyze the current board state for debugging/logging.
    
    Args:
        board: Current board state
        ai_symbol: The AI's symbol
    
    Returns:
        Analysis dictionary with move evaluations
    """
    player_symbol = "X" if ai_symbol == "O" else "O"
    available_moves = get_available_moves(board)
    
    analysis = {
        "available_moves": available_moves,
        "move_scores": {},
        "best_move": None,
        "best_score": None,
    }
    
    best_score = -math.inf
    best_move = None
    
    for row, col in available_moves:
        new_board = apply_move(board, row, col, ai_symbol)
        score = minimax(new_board, 0, False, ai_symbol, player_symbol)
        analysis["move_scores"][(row, col)] = score
        
        if score > best_score:
            best_score = score
            best_move = (row, col)
    
    analysis["best_move"] = best_move
    analysis["best_score"] = best_score
    
    return analysis
