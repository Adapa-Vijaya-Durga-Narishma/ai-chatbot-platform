interface ResearchProgressIndicatorProps {
  statusMessage: string;
  stage: "idle" | "searching" | "evaluating" | "generating" | "completed" | "error";
  iteration?: number;
  paperCount: number;
}

const stageLabelMap: Record<ResearchProgressIndicatorProps["stage"], string> = {
  idle: "Idle",
  searching: "Searching papers",
  evaluating: "Evaluating evidence",
  generating: "Generating digest",
  completed: "Completed",
  error: "Error",
};

export function ResearchProgressIndicator({
  statusMessage,
  stage,
  iteration,
  paperCount,
}: ResearchProgressIndicatorProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/85 p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="inline-flex rounded-full bg-slate-900 px-3 py-1 text-xs font-medium text-white">
          {stageLabelMap[stage]}
        </span>
        {typeof iteration === "number" && (
          <span className="inline-flex rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800">
            Iteration {iteration}
          </span>
        )}
        <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
          {paperCount} papers
        </span>
      </div>
      <p className="text-sm text-slate-700">{statusMessage}</p>
    </div>
  );
}
