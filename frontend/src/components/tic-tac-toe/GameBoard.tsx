import type { BoardState } from "../../types/tic-tac-toe";
import GameCell from "./GameCell";

interface GameBoardProps {
  board: BoardState;
  onCellClick: (row: number, col: number) => void;
  disabled: boolean;
  winningCells?: [number, number][];
}

export default function GameBoard({
  board,
  onCellClick,
  disabled,
  winningCells = [],
}: GameBoardProps) {
  const isWinningCell = (row: number, col: number): boolean => {
    return winningCells.some(([r, c]) => r === row && c === col);
  };

  return (
    <div className="inline-grid grid-cols-3 gap-1 p-4 bg-gray-200 dark:bg-gray-900 rounded-lg shadow-lg">
      {board.map((row, rowIndex) =>
        row.map((cell, colIndex) => (
          <GameCell
            key={`${rowIndex}-${colIndex}`}
            value={cell}
            row={rowIndex}
            col={colIndex}
            onClick={onCellClick}
            disabled={disabled}
            isWinningCell={isWinningCell(rowIndex, colIndex)}
          />
        ))
      )}
    </div>
  );
}
