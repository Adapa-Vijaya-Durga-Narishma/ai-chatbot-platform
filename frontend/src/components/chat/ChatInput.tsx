import { useEffect, useState, useRef, type FormEvent } from "react";
import { AttachmentPreview } from "../attachments/AttachmentPreview";
import { PdfAttachmentPreview } from "../attachments/PdfAttachmentPreview";

type ChatMode = "normal" | "upload" | "upload-pdf" | "generate-image" | "database-query";

interface ChatInputProps {
  onSendMessage: (message: string, files: File[], mode: ChatMode) => void;
  activeThreadId?: string | null;
  isLoading?: boolean;
  isGeneratingImage?: boolean;
  isUploading?: boolean;
  isProcessingPdf?: boolean;
  uploadProgress?: number;
  pdfStatus?: string | null;
}

export function ChatInput({
  onSendMessage,
  activeThreadId,
  isLoading,
  isGeneratingImage,
  isUploading,
  isProcessingPdf,
  uploadProgress,
  pdfStatus,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [unsupportedMessage, setUnsupportedMessage] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>("normal");
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isBusy = Boolean(isLoading || isUploading);

  useEffect(() => {
    if (!unsupportedMessage) return;
    const timer = window.setTimeout(() => setUnsupportedMessage(null), 4000);
    return () => window.clearTimeout(timer);
  }, [unsupportedMessage]);

  useEffect(() => {
    setUnsupportedMessage(null);
    setSelectedFiles([]);
    setShowModeDropdown(false);
    setMode("normal");
  }, [activeThreadId]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    const trimmedMessage = message.trim();
    const requiresFile = mode === "upload-pdf";
    const hasFile = selectedFiles.length > 0;

    if (isBusy) return;
    if (requiresFile && !hasFile && !trimmedMessage) return;
    if (!requiresFile && !trimmedMessage) return;

    onSendMessage(trimmedMessage, mode === "database-query" ? [] : selectedFiles, mode);
    setMessage("");
    setSelectedFiles([]);
    setUnsupportedMessage(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Ctrl+Enter or Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      handleSubmit(e as unknown as FormEvent<HTMLFormElement>);
    }
  };

  const handleModeChange = (newMode: ChatMode) => {
    setMode(newMode);
    setShowModeDropdown(false);
    setSelectedFiles([]);
    setUnsupportedMessage(null);

    // Trigger file selection for upload modes
    if (newMode === "upload" || newMode === "upload-pdf") {
      setTimeout(() => fileInputRef.current?.click(), 0);
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      event.target.value = "";
      return;
    }

    const ALLOWED_MIME_TYPES = new Set([
      "image/jpeg",
      "image/png",
      "image/gif",
      "image/webp",
      "image/bmp",
      "image/svg+xml",
      "video/mp4",
      "video/webm",
      "video/ogg",
      "text/plain",
      "text/markdown",
      "text/csv",
      "text/tab-separated-values",
      "application/csv",
      "application/vnd.ms-excel",
      "text/x-python",
      "text/x-java-source",
      "text/javascript",
      "application/javascript",
      "text/x-c",
      "text/x-c++src",
      "text/x-typescript",
      "application/x-tex",
      "application/pdf",
    ]);

    const supportedFiles = files.filter((file) => {
      if (mode === "upload-pdf") {
        return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      }
      return ALLOWED_MIME_TYPES.has(file.type);
    });
    const unsupportedFiles = files.filter((file) => !supportedFiles.includes(file));

    if (supportedFiles.length > 0) {
      setSelectedFiles((prev) => [...prev, ...supportedFiles]);
      setUnsupportedMessage(null);
    }

    if (unsupportedFiles.length > 0) {
      const listed = unsupportedFiles.slice(0, 3).map((f) => f.name).join(", ");
      const suffix = unsupportedFiles.length > 3 ? ", ..." : "";
      setUnsupportedMessage(
        mode === "upload-pdf"
          ? `Unsupported file format: ${listed}${suffix}. Only PDF files are allowed in PDF mode.`
          : `Unsupported file format: ${listed}${suffix}. Allowed: images, videos, code, text, CSV/tables, formula files, and PDFs.`
      );
    }

    event.target.value = "";
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-slate-200 bg-white/75 backdrop-blur px-4 py-3"
    >
      <div className="flex items-end gap-3">
        <div className="relative flex-1">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === "generate-image"
                ? "Describe the image you want to generate... (Ctrl+Enter to send)"
                : mode === "upload-pdf"
                  ? "Upload a PDF and optionally ask a question... (Ctrl+Enter to send)"
                : mode === "upload"
                  ? "Add files and write a message... (Ctrl+Enter to send)"
                : mode === "database-query"
                  ? "Ask a database question... (Ctrl+Enter to send)"
                  : "Type your message... (Ctrl+Enter to send)"
            }
            disabled={isBusy}
            rows={3}
            className="w-full pl-12 p-3 border border-slate-300 bg-white text-slate-700 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-sky-300 disabled:opacity-50 disabled:cursor-not-allowed"
          />

          <button
            type="button"
            onClick={() => setShowModeDropdown(!showModeDropdown)}
            title="Actions"
            className="absolute left-3 bottom-3 p-1.5 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
          >
            {mode === "generate-image" && (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            )}
            {mode === "upload" && (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            )}
            {mode === "upload-pdf" && (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 4h9l3 3v13H6z" />
                <path d="M15 4v3h3" />
                <path d="M8 13h8M8 17h6" />
              </svg>
            )}
            {mode === "database-query" && (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <ellipse cx="12" cy="5" rx="9" ry="3" />
                <path d="M3 5v14a9 3 0 0 0 9 3a9 3 0 0 0 9-3V5" />
                <path d="M3 12a9 3 0 0 0 9 3a9 3 0 0 0 9-3" />
              </svg>
            )}
            {mode === "normal" && (
              <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
            )}
          </button>

          {showModeDropdown && (
            <div className="absolute left-0 bottom-14 w-48 bg-white border border-slate-300 rounded-lg shadow-lg z-50">
              <button
                type="button"
                onClick={() => {
                  handleModeChange("normal");
                }}
                className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2 first:rounded-t-lg"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <span className="text-sm">Normal Chat</span>
                {mode === "normal" && <span className="ml-auto text-sky-600">✓</span>}
              </button>
              <button
                type="button"
                onClick={() => {
                  handleModeChange("upload");
                }}
                className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <span className="text-sm">Upload Files</span>
                {mode === "upload" && <span className="ml-auto text-sky-600">✓</span>}
              </button>
              <button
                type="button"
                onClick={() => {
                  handleModeChange("upload-pdf");
                }}
                className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M6 4h9l3 3v13H6z" />
                  <path d="M15 4v3h3" />
                  <path d="M8 13h8M8 17h6" />
                </svg>
                <span className="text-sm">Upload PDF (RAG)</span>
                {mode === "upload-pdf" && <span className="ml-auto text-sky-600">✓</span>}
              </button>
              <button
                type="button"
                onClick={() => {
                  handleModeChange("database-query");
                }}
                className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <ellipse cx="12" cy="5" rx="9" ry="3" />
                  <path d="M3 5v14a9 3 0 0 0 9 3a9 3 0 0 0 9-3V5" />
                  <path d="M3 12a9 3 0 0 0 9 3a9 3 0 0 0 9-3" />
                </svg>
                <span className="text-sm">Database Query</span>
                {mode === "database-query" && <span className="ml-auto text-sky-600">✓</span>}
              </button>
              <button
                type="button"
                onClick={() => {
                  handleModeChange("generate-image");
                }}
                className="w-full text-left px-4 py-2 hover:bg-slate-100 flex items-center gap-2 last:rounded-b-lg"
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="currentColor"
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <path d="M21 15l-5-5L5 21" stroke="currentColor" strokeWidth="2" fill="none" />
                </svg>
                <span className="text-sm">Generate Image</span>
                {mode === "generate-image" && <span className="ml-auto text-sky-600">✓</span>}
              </button>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={isBusy || (mode !== "upload-pdf" && !message.trim()) || (mode === "upload-pdf" && !message.trim() && selectedFiles.length === 0)}
          className="px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end"
        >
          {isUploading ? "Uploading..." : isProcessingPdf ? "Processing..." : isGeneratingImage ? "Generating..." : isLoading ? "..." : "Send"}
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={mode === "upload-pdf" ? "application/pdf,.pdf" : "image/*,video/*,.csv,.tsv,.txt,.md,.py,.js,.ts,.tsx,.jsx,.java,.c,.cpp,.sql,.json,.yaml,.yml,.xml,.tex"}
        onChange={handleFileChange}
        className="hidden"
      />

      {isUploading && typeof uploadProgress === "number" && (
        <div className="mt-3">
          <div className="w-full h-2 rounded bg-slate-200 overflow-hidden">
            <div
              className="h-full bg-sky-500 transition-all"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">Upload progress: {uploadProgress}%</p>
        </div>
      )}

      {isProcessingPdf && (
        <p className="mt-2 text-xs text-sky-700 bg-sky-50 border border-sky-200 rounded px-2 py-1">
          Processing PDF...
        </p>
      )}

      {pdfStatus && !isUploading && !isProcessingPdf && (
        <p className="mt-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-1">
          {pdfStatus}
        </p>
      )}

      {(mode === "upload" || mode === "upload-pdf") && selectedFiles.length > 0 && (
        <div className="mt-3 space-y-2">
          {selectedFiles.map((file, index) => (
            mode === "upload-pdf" ? (
              <PdfAttachmentPreview
                key={`${file.name}-${file.size}-${index}`}
                file={file}
                onRemove={() =>
                  setSelectedFiles((prev) => prev.filter((_, currentIndex) => currentIndex !== index))
                }
              />
            ) : (
              <AttachmentPreview
                key={`${file.name}-${file.size}-${index}`}
                file={file}
                onRemove={() =>
                  setSelectedFiles((prev) => prev.filter((_, currentIndex) => currentIndex !== index))
                }
              />
            )
          ))}
        </div>
      )}

      {unsupportedMessage && (
        <p className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
          {unsupportedMessage}
        </p>
      )}
    </form>
  );
}
