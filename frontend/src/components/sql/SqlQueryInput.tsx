import { useEffect, useState, type FormEvent } from "react";

interface SqlQueryInputProps {
  onSubmit: (question: string) => Promise<void>;
  isBusy: boolean;
  loadingStage: "idle" | "generating" | "executing";
  initialQuestion?: string;
}

export function SqlQueryInput({ onSubmit, isBusy, loadingStage, initialQuestion }: SqlQueryInputProps) {
  const [question, setQuestion] = useState("");

  useEffect(() => {
    if (initialQuestion?.trim()) {
      setQuestion(initialQuestion.trim());
    }
  }, [initialQuestion]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const cleaned = question.trim();
    if (!cleaned || isBusy) return;

    await onSubmit(cleaned);
  };

  const statusText =
    loadingStage === "generating"
      ? "Generating SQL..."
      : loadingStage === "executing"
        ? "Executing query..."
        : null;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label htmlFor="sql-question" className="block text-sm font-medium text-slate-700">
        Ask a database question
      </label>
      <textarea
        id="sql-question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        rows={4}
        disabled={isBusy}
        placeholder="Example: How many users signed up this month?"
        className="w-full rounded-xl border border-slate-300 bg-white p-3 text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
      />
      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isBusy}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          Ask SQL Chat
        </button>
        {statusText && <span className="text-sm text-slate-600">{statusText}</span>}
      </div>
    </form>
  );
}
