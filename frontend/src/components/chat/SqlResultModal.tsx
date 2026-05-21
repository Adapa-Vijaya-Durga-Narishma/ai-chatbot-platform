import type { SqlQueryResponse } from "../../types/sql";
import { SqlAnswer } from "../sql/SqlAnswer";
import { SqlGeneratedQuery } from "../sql/SqlGeneratedQuery";
import { SqlResultTable } from "../sql/SqlResultTable";

interface SqlResultModalProps {
  result: SqlQueryResponse | null;
  isOpen: boolean;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}

export function SqlResultModal({ result, isOpen, isLoading, error, onClose }: SqlResultModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Database Query Results</h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-700 transition-colors"
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-4">
          {isLoading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-center">
                <div className="h-8 w-8 border-4 border-slate-200 border-t-sky-600 rounded-full animate-spin mx-auto mb-2" />
                <p className="text-sm text-slate-600">Executing query...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
              <p className="text-sm font-medium text-rose-700">Error</p>
              <p className="text-sm text-rose-600 mt-1">{error}</p>
            </div>
          )}

          {result && !isLoading && (
            <>
              <SqlGeneratedQuery sql={result.sql} />
              <SqlResultTable rows={result.rows} />
              <SqlAnswer answer={result.answer} />
            </>
          )}
        </div>

        <div className="sticky bottom-0 bg-white border-t border-slate-200 px-6 py-4">
          <button
            onClick={onClose}
            className="w-full rounded-lg bg-slate-100 hover:bg-slate-200 px-4 py-2 text-sm font-medium text-slate-900 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
