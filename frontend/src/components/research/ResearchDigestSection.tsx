import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { ResearchDigestSection as DigestSection } from "../../types/research";

interface ResearchDigestSectionProps {
  section: DigestSection;
}

export function ResearchDigestSection({ section }: ResearchDigestSectionProps) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
      <h3 className="text-sm md:text-base font-semibold text-slate-900 mb-3">{section.title}</h3>
      <div className="prose prose-sm max-w-none text-slate-700">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
      </div>
    </section>
  );
}
