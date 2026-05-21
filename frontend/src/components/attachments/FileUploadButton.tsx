import { useRef } from "react";

interface FileUploadButtonProps {
  onFilesSelected: (files: File[]) => void;
  onUnsupportedFiles?: (fileNames: string[]) => void;
  disabled?: boolean;
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

export function FileUploadButton({ onFilesSelected, onUnsupportedFiles, disabled }: FileUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (!disabled) {
      inputRef.current?.click();
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) {
      event.target.value = "";
      return;
    }

    const supportedFiles = files.filter((file) => ALLOWED_MIME_TYPES.has(file.type));
    const unsupportedFiles = files.filter((file) => !ALLOWED_MIME_TYPES.has(file.type));

    if (supportedFiles.length > 0) {
      onFilesSelected(supportedFiles);
    }

    if (unsupportedFiles.length > 0) {
      onUnsupportedFiles?.(unsupportedFiles.map((file) => file.name));
    }

    event.target.value = "";
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        title="Upload files"
        className="p-2 rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </button>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*,video/*,.csv,.tsv,.txt,.md,.py,.js,.ts,.tsx,.jsx,.java,.c,.cpp,.sql,.json,.yaml,.yml,.xml,.tex,.pdf,application/pdf"
        onChange={handleChange}
        className="hidden"
      />
    </>
  );
}
