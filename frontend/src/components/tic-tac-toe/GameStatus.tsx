import type { GameStatus } from "../../types/tic-tac-toe";

interface GameStatusProps {
  status: GameStatus;
  winner: string | null;
  currentTurn: string;
  playerSymbol: string;
  aiSymbol: string;
  isThinking: boolean;
}

export default function GameStatusDisplay({
  status,
  winner,
  currentTurn,
  playerSymbol,
  aiSymbol,
  isThinking,
}: GameStatusProps) {
  const getStatusMessage = (): string => {
    if (status === "completed") {
      if (winner === playerSymbol) {
        return "You Win!";
      }
      if (winner === aiSymbol) {
        return "AI Wins!";
      }
    }
    if (status === "draw") {
      return "It's a Draw!";
    }
    if (isThinking) {
      return "AI is thinking...";
    }
    if (currentTurn === playerSymbol) {
      return "Your Turn";
    }
    return "AI's Turn";
  };

  const getStatusColor = (): string => {
    if (status === "completed") {
      if (winner === playerSymbol) {
        return "text-green-600 dark:text-green-400";
      }
      return "text-red-600 dark:text-red-400";
    }
    if (status === "draw") {
      return "text-yellow-600 dark:text-yellow-400";
    }
    if (isThinking) {
      return "text-purple-600 dark:text-purple-400";
    }
    return "text-gray-700 dark:text-gray-300";
  };

  return (
    <div className="text-center mb-6">
      <p className={`text-2xl font-bold ${getStatusColor()}`}>
        {getStatusMessage()}
      </p>
      {status === "in_progress" && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          You are{" "}
          <span className="font-bold text-blue-600 dark:text-blue-400">
            {playerSymbol}
          </span>{" "}
          · AI is{" "}
          <span className="font-bold text-red-600 dark:text-red-400">
            {aiSymbol}
          </span>
        </p>
      )}
      {isThinking && (
        <div className="flex items-center justify-center mt-2 space-x-1">
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
        </div>
      )}
    </div>
  );
}
