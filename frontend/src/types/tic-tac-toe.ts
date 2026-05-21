/**
 * Tic Tac Toe game types — shared across components.
 */

export type CellValue = "X" | "O" | "";
export type BoardState = CellValue[][];
export type GameStatus = "in_progress" | "completed" | "draw";
export type Difficulty = "easy" | "medium" | "hard";

export interface TicTacToeGame {
  id: string;
  board: BoardState;
  current_turn: string;
  status: GameStatus;
  winner: string | null;
  player_symbol: string;
  ai_symbol: string;
  difficulty: Difficulty;
  available_moves: [number, number][];
  ai_reasoning: string | null;
  created_at: string;
  updated_at: string;
}

export interface MoveResponse {
  game: TicTacToeGame;
  player_move: [number, number] | null;
  ai_move: [number, number] | null;
  ai_reasoning: string | null;
  message: string;
}

export interface PlayerMoveRequest {
  game_id: string;
  row: number;
  col: number;
}

export interface GameCreateRequest {
  difficulty: Difficulty;
}
