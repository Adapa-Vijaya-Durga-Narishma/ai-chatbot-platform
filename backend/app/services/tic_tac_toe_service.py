"""
Tic Tac Toe service layer — business logic and database operations.
Coordinates game engine and AI service.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tic_tac_toe_game import TicTacToeGame
from app.services.tic_tac_toe_engine import (
    apply_move,
    create_empty_board,
    get_available_moves,
    get_game_status,
    is_valid_move,
)
from app.services.tic_tac_toe_ai_service import get_best_move
from app.ai.agents.tic_tac_toe_agent import get_llm_agent_move


# Constants
PLAYER_SYMBOL = "X"  # Human always plays X
AI_SYMBOL = "O"      # AI always plays O


class GameNotFoundError(Exception):
    """Raised when a game is not found."""
    pass


class InvalidMoveError(Exception):
    """Raised when an invalid move is attempted."""
    pass


class GameAlreadyCompletedError(Exception):
    """Raised when trying to make a move on a completed game."""
    pass


class NotPlayerTurnError(Exception):
    """Raised when trying to make a move when it's not the player's turn."""
    pass


class UnauthorizedGameAccessError(Exception):
    """Raised when a user tries to access another user's game."""
    pass


async def create_new_game(
    db: AsyncSession, 
    user_id: uuid.UUID,
    difficulty: str = "medium"
) -> TicTacToeGame:
    """
    Create a new Tic Tac Toe game.
    Human player (X) always goes first.
    
    Args:
        db: Database session
        user_id: User's ID
        difficulty: 'easy', 'medium' (LLM agent), or 'hard' (Minimax)
    """
    game = TicTacToeGame(
        id=uuid.uuid4(),
        user_id=user_id,
        board_state=create_empty_board(),
        current_turn=PLAYER_SYMBOL,
        status="in_progress",
        winner=None,
        difficulty=difficulty,
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


async def get_game(
    db: AsyncSession, 
    game_id: uuid.UUID, 
    user_id: uuid.UUID
) -> TicTacToeGame:
    """
    Get a game by ID, validating user ownership.
    """
    result = await db.execute(
        select(TicTacToeGame).where(TicTacToeGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    
    if not game:
        raise GameNotFoundError(f"Game {game_id} not found")
    
    if game.user_id != user_id:
        raise UnauthorizedGameAccessError("You do not have access to this game")
    
    return game


async def get_user_games(
    db: AsyncSession, 
    user_id: uuid.UUID, 
    include_completed: bool = True
) -> list[TicTacToeGame]:
    """
    Get all games for a user.
    """
    query = select(TicTacToeGame).where(TicTacToeGame.user_id == user_id)
    
    if not include_completed:
        query = query.where(TicTacToeGame.status == "in_progress")
    
    query = query.order_by(TicTacToeGame.updated_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def make_player_move(
    db: AsyncSession,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
    row: int,
    col: int,
    user_email: str,
) -> tuple[TicTacToeGame, tuple[int, int] | None, tuple[int, int] | None, str, str | None]:
    """
    Process a player move and generate AI response.
    
    Returns:
        Tuple of (updated_game, player_move, ai_move, message, ai_reasoning)
    """
    game = await get_game(db, game_id, user_id)
    
    # Validate game state
    if game.status != "in_progress":
        raise GameAlreadyCompletedError("This game has already ended")
    
    if game.current_turn != PLAYER_SYMBOL:
        raise NotPlayerTurnError("It's not your turn")
    
    board = game.board_state
    
    # Validate and apply player move
    if not is_valid_move(board, row, col):
        raise InvalidMoveError(f"Invalid move: cell ({row}, {col}) is occupied or out of bounds")
    
    board = apply_move(board, row, col, PLAYER_SYMBOL)
    player_move = (row, col)
    ai_move = None
    message = ""
    ai_reasoning = None
    
    # Check game status after player move
    status, winner = get_game_status(board)
    
    if status == "completed":
        game.board_state = board
        game.status = status
        game.winner = winner
        game.current_turn = ""
        await db.commit()
        await db.refresh(game)
        return game, player_move, None, f"Player {winner} wins!", None
    
    if status == "draw":
        game.board_state = board
        game.status = status
        game.winner = None
        game.current_turn = ""
        await db.commit()
        await db.refresh(game)
        return game, player_move, None, "It's a draw!", None
    
    # AI's turn - choose strategy based on difficulty
    if game.difficulty == "hard":
        # Use Minimax for unbeatable play
        ai_move_result = get_best_move(board, AI_SYMBOL)
        ai_reasoning = "Calculated optimal move using Minimax algorithm."
    else:
        # Use LLM agent for easy/medium
        ai_move_result, ai_reasoning = await get_llm_agent_move(
            board=board,
            ai_symbol=AI_SYMBOL,
            difficulty=game.difficulty,
            user_email=user_email,
        )
    
    if ai_move_result:
        ai_row, ai_col = ai_move_result
        board = apply_move(board, ai_row, ai_col, AI_SYMBOL)
        ai_move = (ai_row, ai_col)
        
        # Check game status after AI move
        status, winner = get_game_status(board)
        
        if status == "completed":
            message = f"AI wins!"
            game.current_turn = ""
        elif status == "draw":
            message = "It's a draw!"
            game.current_turn = ""
        else:
            message = "Your turn"
            game.current_turn = PLAYER_SYMBOL
    else:
        game.current_turn = PLAYER_SYMBOL
        message = "Your turn"
    
    # Update game state
    game.board_state = board
    game.status = status
    game.winner = winner
    
    await db.commit()
    await db.refresh(game)
    
    return game, player_move, ai_move, message, ai_reasoning


async def restart_game(
    db: AsyncSession,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> TicTacToeGame:
    """
    Restart a game by resetting its state.
    """
    game = await get_game(db, game_id, user_id)
    
    game.board_state = create_empty_board()
    game.current_turn = PLAYER_SYMBOL
    game.status = "in_progress"
    game.winner = None
    
    await db.commit()
    await db.refresh(game)
    
    return game


def build_game_response(game: TicTacToeGame, ai_reasoning: str | None = None) -> dict:
    """
    Build a response dictionary from a game model.
    """
    return {
        "id": game.id,
        "board": game.board_state,
        "current_turn": game.current_turn,
        "status": game.status,
        "winner": game.winner,
        "player_symbol": PLAYER_SYMBOL,
        "ai_symbol": AI_SYMBOL,
        "difficulty": game.difficulty,
        "available_moves": get_available_moves(game.board_state) if game.status == "in_progress" else [],
        "ai_reasoning": ai_reasoning,
        "created_at": game.created_at,
        "updated_at": game.updated_at,
    }
