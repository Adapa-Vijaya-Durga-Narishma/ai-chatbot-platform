interface RestartButtonProps {
  onClick: () => void;
  disabled: boolean;
}

export default function RestartButton({ onClick, disabled }: RestartButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-lg shadow-md transition-colors duration-200 disabled:cursor-not-allowed"
    >
      Restart Game
    </button>
  );
}
