interface PdfAttachmentPreviewProps {
  file: File;
  onRemove: () => void;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function PdfAttachmentPreview({ file, onRemove }: PdfAttachmentPreviewProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2">
      <div className="min-w-0">
        <p className="text-sm font-medium text-blue-900 truncate">{file.name}</p>
        <p className="text-xs text-blue-700">PDF • {formatSize(file.size)}</p>
      </div>
      <button
        type="button"
        onClick={onRemove}
        className="text-xs px-2 py-1 rounded border border-blue-300 text-blue-700 hover:bg-white"
      >
        Remove
      </button>
    </div>
  );
}
