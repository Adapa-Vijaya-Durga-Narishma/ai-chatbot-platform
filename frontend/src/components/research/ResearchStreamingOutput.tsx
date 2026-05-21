import type { ResearchDigestSection, ResearchPaper, ResearchReasoningEvent } from "../../types/research";
import { ResearchDigestSection as ResearchDigestSectionCard } from "./ResearchDigestSection";
import { ResearchPaperCard } from "./ResearchPaperCard";

interface ResearchStreamingOutputProps {
  papers: ResearchPaper[];
  reasoning: ResearchReasoningEvent[];
  sections: ResearchDigestSection[];
}

export function ResearchStreamingOutput({
  papers,
  reasoning,
  sections,
}: ResearchStreamingOutputProps) {
  return (
    <div className="space-y-4">
      {papers.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold tracking-wide text-slate-600 uppercase">Discovered Papers</h2>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {papers.map((paper) => (
              <ResearchPaperCard key={`${paper.arxiv_url}-${paper.arxiv_id}`} paper={paper} />
            ))}
          </div>
        </div>
      )}

      {reasoning.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4">
          <h2 className="text-sm font-semibold tracking-wide text-amber-800 uppercase mb-2">Reasoning Trail</h2>
          <ul className="space-y-2 text-sm text-amber-900">
            {reasoning.map((event) => (
              <li key={`reasoning-${event.iteration}-${event.message.slice(0, 24)}`}>
                <span className="font-semibold">Iteration {event.iteration}:</span> {event.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {sections.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold tracking-wide text-slate-600 uppercase">Research Digest</h2>
          {sections.map((section) => (
            <ResearchDigestSectionCard key={section.title} section={section} />
          ))}
        </div>
      )}
    </div>
  );
}
