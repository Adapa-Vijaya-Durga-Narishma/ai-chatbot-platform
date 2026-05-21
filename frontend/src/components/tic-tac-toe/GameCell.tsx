import type { CellValue } from "../../types/tic-tac-toe";

interface GameCellProps {
  value: CellValue;
  row: number;
  col: number;
  onClick: (row: number, col: number) => void;
  disabled: boolean;
  isWinningCell?: boolean;
}

export default function GameCell({
  value,
  row,
  col,
  onClick,
  disabled,
  isWinningCell = false,
}: GameCellProps) {
  const handleClick = () => {
    if (!disabled && value === "") {
      onClick(row, col);
    }
  };

  const baseClasses =
    "w-24 h-24 text-5xl font-bold flex items-center justify-center border-2 border-gray-300 dark:border-gray-600 transition-all duration-200";

  const stateClasses = disabled
    ? "cursor-not-allowed bg-gray-100 dark:bg-gray-700"
    : value === ""
    ? "cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 bg-white dark:bg-gray-800"
    : "bg-white dark:bg-gray-800";

  const winningClasses = isWinningCell
    ? "bg-green-100 dark:bg-green-900 border-green-500"
    : "";

  const symbolClasses =
    value === "X"
      ? "text-blue-600 dark:text-blue-400"
      : value === "O"
      ? "text-red-600 dark:text-red-400"
      : "";

  return (
    <button
      type="button"
      className={`${baseClasses} ${stateClasses} ${winningClasses} ${symbolClasses}`}
      onClick={handleClick}
      disabled={disabled || value !== ""}
      aria-label={`Cell ${row}-${col}, ${value || "empty"}`}
    >
      {value}
    </button>
  );
}
