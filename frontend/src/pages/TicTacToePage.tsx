import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import {
  createTicTacToeGame,
  makeTicTacToeMove,
  restartTicTacToeGame,
} from "../lib/api";
import type { TicTacToeGame, Difficulty } from "../types/tic-tac-toe";
import { GameBoard, GameStatus, RestartButton } from "../components/tic-tac-toe";

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string; description: string }[] = [
  { value: "easy", label: "Easy", description: "LLM Agent - Makes mistakes" },
  { value: "medium", label: "Medium", description: "LLM Agent - Moderate play" },
  { value: "hard", label: "Hard", description: "Minimax - Unbeatable" },
];

export default function TicTacToePage() {
  const { user, logout } = useAuth();
  const [game, setGame] = useState<TicTacToeGame | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty>("medium");
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [aiReasoning, setAiReasoning] = useState<string | null>(null);

  // Create new game mutation
  const createGameMutation = useMutation({
    mutationFn: (difficulty: Difficulty) => createTicTacToeGame(difficulty),
    onSuccess: (newGame) => {
      setGame(newGame);
      setError(null);
      setAiReasoning(null);
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to create game");
    },
  });

  // Make move mutation
  const makeMovesMutation = useMutation({
    mutationFn: ({ gameId, row, col }: { gameId: string; row: number; col: number }) =>
      makeTicTacToeMove(gameId, row, col),
    onMutate: () => {
      setIsThinking(true);
      setError(null);
    },
    onSuccess: (response) => {
      setGame(response.game);
      setAiReasoning(response.ai_reasoning);
      setIsThinking(false);
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to make move");
      setIsThinking(false);
    },
  });

  // Restart game mutation
  const restartMutation = useMutation({
    mutationFn: (gameId: string) => restartTicTacToeGame(gameId),
    onSuccess: (restartedGame) => {
      setGame(restartedGame);
      setError(null);
      setAiReasoning(null);
    },
    onError: (err: Error) => {
      setError(err.message || "Failed to restart game");
    },
  });

  const handleCellClick = useCallback(
    (row: number, col: number) => {
      if (!game || game.status !== "in_progress" || isThinking) {
        return;
      }
      if (game.current_turn !== game.player_symbol) {
        return;
      }
      makeMovesMutation.mutate({ gameId: game.id, row, col });
    },
    [game, isThinking, makeMovesMutation]
  );

  const handleRestart = useCallback(() => {
    if (game) {
      restartMutation.mutate(game.id);
    }
  }, [game, restartMutation]);

  const handleStartGame = useCallback(() => {
    createGameMutation.mutate(selectedDifficulty);
  }, [createGameMutation, selectedDifficulty]);

  const isLoading =
    createGameMutation.isPending ||
    makeMovesMutation.isPending ||
    restartMutation.isPending;

  const isBoardDisabled =
    !game ||
    game.status !== "in_progress" ||
    isThinking ||
    game.current_turn !== game.player_symbol;

  // Show difficulty selection if no game exists
  if (!game) {
    return (
      <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
        <header className="flex items-center justify-between px-4 md:px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
          <div>
            <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">
              Tic Tac Toe
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Back to Chat
            </Link>
            <button
              onClick={logout}
              className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        <main className="flex-1 flex flex-col items-center justify-center p-6">
          {error && (
            <div className="mb-6 px-4 py-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300">
              {error}
            </div>
          )}

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 max-w-md w-full">
            <h2 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-6">
              Select Difficulty
            </h2>

            <div className="space-y-3 mb-8">
              {DIFFICULTY_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setSelectedDifficulty(option.value)}
                  className={`w-full p-4 rounded-lg border-2 text-left transition-all ${
                    selectedDifficulty === option.value
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30"
                      : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500"
                  }`}
                >
                  <div className="font-semibold text-gray-900 dark:text-white">
                    {option.label}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {option.description}
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={handleStartGame}
              disabled={createGameMutation.isPending}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg shadow-md transition-colors duration-200"
            >
              {createGameMutation.isPending ? "Starting..." : "Start Game"}
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="flex items-center justify-between px-4 md:px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">
            Tic Tac Toe
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{user?.email}</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            Back to Chat
          </Link>
          <button
            onClick={logout}
            className="text-sm px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-6">
        {/* Error Message */}
        {error && (
          <div className="mb-6 px-4 py-3 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Loading State */}
        {createGameMutation.isPending && !game && (
          <div className="text-gray-500 dark:text-gray-400">Creating game...</div>
        )}

        {/* Game Content */}
        {game && (
          <div className="flex flex-col items-center">
            {/* Difficulty Badge */}
            <div className="mb-4">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                game.difficulty === "easy"
                  ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                  : game.difficulty === "medium"
                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
                  : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
              }`}>
                {game.difficulty === "easy" ? "Easy (LLM)" : game.difficulty === "medium" ? "Medium (LLM)" : "Hard (Minimax)"}
              </span>
            </div>

            <GameStatus
              status={game.status}
              winner={game.winner}
              currentTurn={game.current_turn}
              playerSymbol={game.player_symbol}
              aiSymbol={game.ai_symbol}
              isThinking={isThinking}
            />

            <GameBoard
              board={game.board}
              onCellClick={handleCellClick}
              disabled={isBoardDisabled}
            />

            {/* AI Reasoning */}
            {aiReasoning && game.difficulty !== "hard" && (
              <div className="mt-6 max-w-md p-4 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 rounded-lg">
                <p className="text-sm font-medium text-purple-800 dark:text-purple-300 mb-1">
                  AI's Reasoning:
                </p>
                <p className="text-sm text-purple-700 dark:text-purple-400 italic">
                  "{aiReasoning}"
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="mt-8 flex gap-4">
              <RestartButton
                onClick={handleRestart}
                disabled={isLoading || isThinking}
              />
              <button
                type="button"
                onClick={() => setGame(null)}
                disabled={isLoading || isThinking}
                className="px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold rounded-lg shadow-md transition-colors duration-200 disabled:cursor-not-allowed"
              >
                New Game
              </button>
            </div>

            {/* Game Info */}
            <div className="mt-8 text-sm text-gray-500 dark:text-gray-400 text-center">
              {game.difficulty === "hard" ? (
                <>
                  <p>Playing against an unbeatable AI</p>
                  <p className="mt-1">The AI uses the Minimax algorithm</p>
                </>
              ) : (
                <>
                  <p>Playing against an LLM-powered AI Agent</p>
                  <p className="mt-1">The AI reasons about each move</p>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
