import type { DataframeQueryResponse, DataframeSourceResponse } from "../../types/dataframe";

interface DataframeAnswerProps {
  source: DataframeSourceResponse | null;
  answer: DataframeQueryResponse | null;
}

export function DataframeAnswer({ source, answer }: DataframeAnswerProps) {
  if (!answer) {
    return null;
  }

  const listAnswer = parseListAnswer(answer.answer);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-slate-900">Answer</p>
        {listAnswer && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
            {listAnswer.items.length} items
          </span>
        )}
      </div>

      {listAnswer ? (
        <div className="space-y-2">
          <p className="text-sm text-slate-700 text-justify">{listAnswer.leadIn}</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 max-h-72 overflow-y-auto">
            {listAnswer.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-sm text-slate-700 whitespace-pre-wrap text-justify">{answer.answer}</p>
      )}

      {source && (
        <p className="text-xs text-slate-500">Source: {source.source_name}</p>
      )}
    </div>
  );
}

function parseListAnswer(rawAnswer: string): { leadIn: string; items: string[] } | null {
  const text = rawAnswer.trim();
  const delimiterIndex = text.indexOf(":");

  if (delimiterIndex === -1) {
    return null;
  }

  const leadIn = text.slice(0, delimiterIndex + 1).trim();
  const valuesSection = text.slice(delimiterIndex + 1).trim();

  if (!valuesSection.includes(",")) {
    return null;
  }

  const items = valuesSection
    .split(",")
    .map((item) => item.trim().replace(/[.\s]+$/, ""))
    .filter(Boolean);

  if (items.length < 3) {
    return null;
  }

  return { leadIn, items };
}