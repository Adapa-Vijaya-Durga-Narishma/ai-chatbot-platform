import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { askSqlQuestion } from "../lib/api";
import type { SqlQueryResponse } from "../types/sql";
import { SqlAnswer } from "../components/sql/SqlAnswer";
import { SqlGeneratedQuery } from "../components/sql/SqlGeneratedQuery";
import { SqlQueryInput } from "../components/sql/SqlQueryInput";
import { SqlResultTable } from "../components/sql/SqlResultTable";

export default function SqlChatPage() {
  const { user, logout } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [result, setResult] = useState<SqlQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingStage, setLoadingStage] = useState<"idle" | "generating" | "executing">("idle");
  const [initialQuestion, setInitialQuestion] = useState("");
  const hasAutoSubmittedRef = useRef(false);

  const isBusy = loadingStage !== "idle";

  const handleAskQuestion = useCallback(async (question: string) => {
    setError(null);
    setLoadingStage("generating");

    try {
      setLoadingStage("executing");
      const response = await askSqlQuestion(question);
      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to execute SQL chat query";
      setError(message);
    } finally {
      setLoadingStage("idle");
    }
  }, []);

  useEffect(() => {
    const questionFromQuery = searchParams.get("question")?.trim() ?? "";
    if (!questionFromQuery) {
      return;
    }

    setInitialQuestion(questionFromQuery);

    if (!hasAutoSubmittedRef.current) {
      hasAutoSubmittedRef.current = true;
      void handleAskQuestion(questionFromQuery);

      const next = new URLSearchParams(searchParams);
      next.delete("question");
      setSearchParams(next, { replace: true });
    }
  }, [handleAskQuestion, searchParams, setSearchParams]);

  return (
    <div className="h-screen flex flex-col p-3 md:p-5 gap-3 md:gap-4">
      <header className="flex items-center justify-between px-4 md:px-5 py-3 rounded-2xl border border-slate-200/80 bg-white/85 backdrop-blur shadow-sm flex-shrink-0">
        <div>
          <h1 className="text-base md:text-lg font-semibold text-slate-900">SQL Chat</h1>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/dataframe"
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Dataframe Chat
          </Link>
          <Link
            to="/"
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Back to Chat
          </Link>
          <button
            onClick={logout}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto rounded-2xl border border-slate-200/80 bg-white/80 backdrop-blur shadow-sm p-4 md:p-6 space-y-4">
        <SqlQueryInput
          onSubmit={handleAskQuestion}
          isBusy={isBusy}
          loadingStage={loadingStage}
          initialQuestion={initialQuestion}
        />

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-sm font-medium text-rose-700">Error</p>
            <p className="text-sm text-rose-600">{error}</p>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <SqlGeneratedQuery sql={result.sql} />
            <SqlResultTable rows={result.rows} />
            <SqlAnswer answer={result.answer} />
          </div>
        )}
      </main>
    </div>
  );
}
