import { useState } from "react";
import { Link } from "react-router-dom";

import { ResearchInput } from "../components/research/ResearchInput";
import { ResearchProgressIndicator } from "../components/research/ResearchProgressIndicator";
import { ResearchStreamingOutput } from "../components/research/ResearchStreamingOutput";
import { useAuth } from "../context/AuthContext";
import { startResearchDigest } from "../lib/api";
import type {
  ResearchDigestSection,
  ResearchPaper,
  ResearchReasoningEvent,
  ResearchStatusEvent,
  ResearchStreamEvent,
} from "../types/research";

type ResearchStage = "idle" | "searching" | "evaluating" | "generating" | "completed" | "error";

export default function ResearchDigestPage() {
  const { user, logout } = useAuth();
  const [papers, setPapers] = useState<ResearchPaper[]>([]);
  const [sections, setSections] = useState<ResearchDigestSection[]>([]);
  const [reasoning, setReasoning] = useState<ResearchReasoningEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [statusMessage, setStatusMessage] = useState("Enter a topic and start autonomous research.");
  const [stage, setStage] = useState<ResearchStage>("idle");
  const [iteration, setIteration] = useState<number | undefined>(undefined);
  const [threadId, setThreadId] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  async function handleStart(topic: string) {
    let failed = false;

    setIsRunning(true);
    setError(null);
    setPapers([]);
    setSections([]);
    setReasoning([]);
    setStage("searching");
    setStatusMessage("Searching papers...");
    setIteration(undefined);

    try {
      await startResearchDigest(
        topic,
        (event: ResearchStreamEvent) => {
          if (event.type === "thread") {
            setThreadId(event.thread_id);
            return;
          }

          if (event.type === "status") {
            const statusEvent = event as ResearchStatusEvent;
            setStatusMessage(statusEvent.message);
            setStage(statusEvent.stage);
            setIteration(statusEvent.iteration);
            return;
          }

          if (event.type === "paper") {
            setPapers((prev) => {
              if (prev.some((paper) => paper.arxiv_url === event.paper.arxiv_url)) {
                return prev;
              }
              return [...prev, event.paper];
            });
            return;
          }

          if (event.type === "reasoning") {
            setReasoning((prev) => [...prev, event]);
            return;
          }

          if (event.type === "digest_section") {
            setSections((prev) => {
              const exists = prev.some((section) => section.title === event.section.title);
              if (exists) {
                return prev.map((section) =>
                  section.title === event.section.title ? event.section : section
                );
              }
              return [...prev, event.section];
            });
            return;
          }

          if (event.type === "done") {
            setStage("completed");
            setStatusMessage(`Completed with ${event.paper_count} papers across ${event.iterations_used} iterations.`);
            return;
          }

          if (event.type === "error") {
            failed = true;
            setStage("error");
            setError(event.message);
            setStatusMessage("Research run failed.");
            setIsRunning(false);
          }
        },
        threadId
      );

      setIsRunning(false);
      if (!failed) {
        setStage("completed");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to run research digest";
      setError(message);
      setStage("error");
      setStatusMessage("Research run failed.");
      setIsRunning(false);
    }
  }

  return (
    <div className="h-screen flex flex-col p-3 md:p-5 gap-3 md:gap-4">
      <header className="flex items-center justify-between px-4 md:px-5 py-3 rounded-2xl border border-slate-200/80 bg-white/85 backdrop-blur shadow-sm flex-shrink-0">
        <div>
          <h1 className="text-base md:text-lg font-semibold text-slate-900">Research Digest Agent</h1>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        <div className="flex items-center gap-2">
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
        <ResearchInput isRunning={isRunning} onSubmit={handleStart} />
        <ResearchProgressIndicator
          stage={stage}
          statusMessage={statusMessage}
          iteration={iteration}
          paperCount={papers.length}
        />

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-sm font-medium text-rose-700">Error</p>
            <p className="text-sm text-rose-600">{error}</p>
          </div>
        )}

        <ResearchStreamingOutput papers={papers} sections={sections} reasoning={reasoning} />
      </main>
    </div>
  );
}
