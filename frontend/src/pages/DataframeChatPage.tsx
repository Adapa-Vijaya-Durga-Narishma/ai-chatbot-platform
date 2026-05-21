import { useState } from "react";
import { Link } from "react-router-dom";

import { DataframeAnswer } from "../components/dataframe/DataframeAnswer";
import { DataframeQuestionInput } from "../components/dataframe/DataframeQuestionInput";
import { DataframeUpload } from "../components/dataframe/DataframeUpload";
import { GoogleSheetInput } from "../components/dataframe/GoogleSheetInput";
import { useAuth } from "../context/AuthContext";
import {
  askDataframeQuestion,
  connectGoogleSheet,
  uploadDataframeFile,
} from "../lib/api";
import type { DataframeQueryResponse, DataframeSourceResponse } from "../types/dataframe";

type DataframeSourceMode = "csv" | "google-sheet";

export default function DataframeChatPage() {
  const { user, logout } = useAuth();
  const [sourceMode, setSourceMode] = useState<DataframeSourceMode>("csv");
  const [source, setSource] = useState<DataframeSourceResponse | null>(null);
  const [answer, setAnswer] = useState<DataframeQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "connecting" | "analyzing">("idle");
  const [questionResetTrigger, setQuestionResetTrigger] = useState(0);

  const isUploading = status === "uploading";
  const isConnecting = status === "connecting";
  const isAnalyzing = status === "analyzing";
  const isSourceBusy = isUploading || isConnecting;

  function handleModeChange(newMode: DataframeSourceMode) {
    setSourceMode(newMode);
    setAnswer(null);
    setError(null);
    setQuestionResetTrigger((prev) => prev + 1);
  }

  async function handleUpload(file: File) {
    setError(null);
    setAnswer(null);
    setStatus("uploading");
    try {
      const response = await uploadDataframeFile(file);
      setSource(response);
      setSourceMode("csv");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload dataframe file");
    } finally {
      setStatus("idle");
    }
  }

  async function handleConnect(sheetUrl: string) {
    setError(null);
    setAnswer(null);
    setStatus("connecting");
    try {
      const response = await connectGoogleSheet({ sheet_url: sheetUrl });
      setSource(response);
      setSourceMode("google-sheet");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect Google Sheet");
    } finally {
      setStatus("idle");
    }
  }

  async function handleAsk(question: string) {
    setError(null);
    setStatus("analyzing");
    try {
      const response = await askDataframeQuestion(question);
      setAnswer(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze dataframe");
    } finally {
      setStatus("idle");
    }
  }

  return (
    <div className="h-screen flex flex-col p-3 md:p-5 gap-3 md:gap-4">
      <header className="flex items-center justify-between px-4 md:px-5 py-3 rounded-2xl border border-slate-200/80 bg-white/85 backdrop-blur shadow-sm flex-shrink-0">
        <div>
          <h1 className="text-base md:text-lg font-semibold text-slate-900">Dataframe Chat</h1>
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
        <div className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
          Paste your Google Sheet URL or upload a CSV/XLSX file.
        </div>

        <div className="flex gap-2 border-b border-slate-200">
          <button
            onClick={() => handleModeChange("csv")}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              sourceMode === "csv"
                ? "text-slate-900 border-b-2 border-slate-900"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Upload CSV/XLSX
          </button>
          <button
            onClick={() => handleModeChange("google-sheet")}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              sourceMode === "google-sheet"
                ? "text-slate-900 border-b-2 border-slate-900"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Connect Google Sheet
          </button>
        </div>

        {sourceMode === "csv" && (
          <DataframeUpload isBusy={isUploading} onUpload={handleUpload} />
        )}

        {sourceMode === "google-sheet" && (
          <GoogleSheetInput isBusy={isConnecting} onConnect={handleConnect} />
        )}

        <DataframeQuestionInput
          isBusy={isAnalyzing}
          isDisabled={!source || isSourceBusy}
          resetTrigger={questionResetTrigger}
          onSubmit={handleAsk}
        />

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-sm font-medium text-rose-700">Error</p>
            <p className="text-sm text-rose-600">{error}</p>
          </div>
        )}

        {answer && <DataframeAnswer source={source} answer={answer} />}
      </main>
    </div>
  );
}