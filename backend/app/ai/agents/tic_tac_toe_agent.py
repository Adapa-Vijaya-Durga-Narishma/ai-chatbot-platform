"""
Tic Tac Toe LLM Agent — uses LangChain to reason about game moves.
This provides a more "human-like" opponent that can make occasional mistakes.
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.ai.llm import llm
from app.services.tic_tac_toe_engine import (
    BoardType,
    MoveType,
    get_available_moves,
)


class MoveDecision(BaseModel):
    """Schema for the agent's move decision."""
    reasoning: str = Field(description="Brief explanation of the move choice")
    row: int = Field(description="Row index (0, 1, or 2)")
    col: int = Field(description="Column index (0, 1, or 2)")


# System prompt for the Tic Tac Toe agent
SYSTEM_PROMPT = """You are playing Tic Tac Toe as '{ai_symbol}' against a human player '{player_symbol}'.

Current board state (0-indexed, row then column):
{board_display}

Available moves: {available_moves}

RULES:
- You must choose from the available moves only
- Win by getting 3 in a row (horizontal, vertical, or diagonal)
- Block the opponent if they're about to win
- {difficulty_instructions}

Respond with a JSON object containing:
- "reasoning": brief explanation of your move (1-2 sentences)
- "row": the row index (0, 1, or 2)
- "col": the column index (0, 1, or 2)"""

DIFFICULTY_INSTRUCTIONS = {
    "easy": "Play casually. You can make mistakes and don't need to play optimally. Sometimes choose suboptimal moves to give the human a chance.",
    "medium": "Play moderately well. Try to block obvious wins and take winning moves when you see them, but you don't need to analyze every possibility deeply.",
}


def format_board_display(board: BoardType) -> str:
    """Format the board for display in the prompt."""
    lines = []
    lines.append("     Col 0 | Col 1 | Col 2")
    lines.append("    -------+-------+-------")
    for row_idx, row in enumerate(board):
        cells = []
        for cell in row:
            if cell == "":
                cells.append("   ")
            else:
                cells.append(f" {cell} ")
        lines.append(f"Row {row_idx}  {cells[0]}|{cells[1]}|{cells[2]}")
        if row_idx < 2:
            lines.append("    -------+-------+-------")
    return "\n".join(lines)


def format_available_moves(moves: list[MoveType]) -> str:
    """Format available moves for the prompt."""
    return ", ".join([f"({r},{c})" for r, c in moves])


async def get_llm_agent_move(
    board: BoardType,
    ai_symbol: str,
    difficulty: str,
    user_email: str,
) -> tuple[MoveType, str]:
    """
    Get a move from the LLM agent.
    
    Args:
        board: Current board state
        ai_symbol: The AI's symbol ('X' or 'O')
        difficulty: 'easy' or 'medium'
        user_email: User's email for usage tracking
    
    Returns:
        Tuple of (move, reasoning)
    """
    player_symbol = "X" if ai_symbol == "O" else "O"
    available_moves = get_available_moves(board)
    
    if not available_moves:
        raise ValueError("No available moves")
    
    # If only one move available, just return it
    if len(available_moves) == 1:
        return available_moves[0], "Only one move available."
    
    # Build the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Make your move as {ai_symbol}. Return only valid JSON.")
    ])
    
    # Create the chain with JSON output parser
    parser = JsonOutputParser(pydantic_object=MoveDecision)
    chain = prompt | llm | parser
    
    try:
        result = await chain.ainvoke(
            {
                "ai_symbol": ai_symbol,
                "player_symbol": player_symbol,
                "board_display": format_board_display(board),
                "available_moves": format_available_moves(available_moves),
                "difficulty_instructions": DIFFICULTY_INSTRUCTIONS.get(difficulty, DIFFICULTY_INSTRUCTIONS["medium"]),
            },
            config={"metadata": {"user_email": user_email}}
        )
        
        move = (result["row"], result["col"])
        reasoning = result.get("reasoning", "")
        
        # Validate the move is actually available
        if move not in available_moves:
            # Fallback to first available move if LLM made invalid choice
            move = available_moves[0]
            reasoning = f"(Fallback move - LLM suggested invalid move)"
        
        return move, reasoning
        
    except Exception as e:
        # Fallback to first available move on any error
        return available_moves[0], f"(Fallback move - error: {str(e)[:50]})"
