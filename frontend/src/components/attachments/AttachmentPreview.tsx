interface AttachmentPreviewProps {
  file: File;
  onRemove: () => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function AttachmentPreview({ file, onRemove }: AttachmentPreviewProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
        <p className="text-xs text-slate-500">{file.type || "unknown"} • {formatSize(file.size)}</p>
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="text-xs px-2 py-1 rounded border border-slate-300 text-slate-600 hover:bg-white"
      >
        Remove
      </button>
    </div>
  );
}
