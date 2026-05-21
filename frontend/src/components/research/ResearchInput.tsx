import { useState } from "react";

interface ResearchInputProps {
  isRunning: boolean;
  onSubmit: (topic: string) => Promise<void>;
}

export function ResearchInput({ isRunning, onSubmit }: ResearchInputProps) {
  const [topic, setTopic] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = topic.trim();
    if (!trimmed || isRunning) {
      return;
    }
    await onSubmit(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm">
      <label htmlFor="research-topic" className="block text-sm font-medium text-slate-700 mb-2">
        Research topic
      </label>
      <textarea
        id="research-topic"
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
        placeholder="Recent advances in multimodal RAG systems"
        className="w-full min-h-24 rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-300"
        disabled={isRunning}
      />
      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-slate-500">The agent will search arXiv, evaluate evidence, and stream a digest live.</p>
        <button
          type="submit"
          disabled={isRunning || !topic.trim()}
          className="rounded-lg bg-slate-900 text-white text-sm px-4 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRunning ? "Researching..." : "Start Research"}
        </button>
      </div>
    </form>
  );
}
