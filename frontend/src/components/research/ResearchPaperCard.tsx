import type { ResearchPaper } from "../../types/research";

interface ResearchPaperCardProps {
  paper: ResearchPaper;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleDateString();
}

export function ResearchPaperCard({ paper }: ResearchPaperCardProps) {
  const abstractPreview = paper.abstract.length > 300 ? `${paper.abstract.slice(0, 297)}...` : paper.abstract;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
      <h3 className="text-sm md:text-base font-semibold text-slate-900">{paper.title}</h3>
      <p className="mt-1 text-xs text-slate-500">{paper.authors.join(", ") || "Unknown authors"}</p>
      <p className="mt-2 text-xs text-slate-500">Published: {formatDate(paper.published)}</p>
      <p className="mt-3 text-sm text-slate-700 leading-6">{abstractPreview}</p>
      <a
        href={paper.arxiv_url}
        target="_blank"
        rel="noreferrer"
        className="mt-3 inline-flex text-xs font-medium text-sky-700 hover:text-sky-900"
      >
        View on arXiv
      </a>
    </article>
  );
}
