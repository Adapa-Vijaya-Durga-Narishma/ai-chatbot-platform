import React, { useState, useEffect } from "react";

interface DataframeQuestionInputProps {
  isBusy: boolean;
  isDisabled: boolean;
  resetTrigger: number;
  onSubmit: (question: string) => Promise<void>;
}

export function DataframeQuestionInput({
  isBusy,
  isDisabled,
  resetTrigger,
  onSubmit,
}: DataframeQuestionInputProps) {
  const [question, setQuestion] = useState("");

  // Clear question when resetTrigger changes
  useEffect(() => {
    setQuestion("");
  }, [resetTrigger]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    event.stopPropagation();
    const trimmed = question.trim();
    if (!trimmed) {
      return;
    }

    await onSubmit(trimmed);
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Ask a question</h2>
        <p className="text-sm text-slate-600">Examples: highest salary, average revenue by month, top 5 products by sales.</p>
      </div>

      <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={4}
          placeholder="What is the average revenue by month?"
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400"
          disabled={isBusy || isDisabled}
        />
        <button
          type="submit"
          disabled={isBusy || isDisabled || !question.trim()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isBusy ? "Analyzing dataframe..." : "Ask"}
        </button>
      </form>
    </section>
  );
}