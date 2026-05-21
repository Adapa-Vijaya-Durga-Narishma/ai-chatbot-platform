import { useState } from "react";
import type { Attachment } from "../../types/attachment";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface AttachmentListProps {
  attachments: Attachment[];
}

function TypeIcon({ type }: { type: Attachment["attachment_type"] }) {
  if (type === "csv") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M3 10h18M9 4v16M15 4v16" />
      </svg>
    );
  }

  if (type === "code") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M8 16L4 12l4-4M16 8l4 4-4 4" />
      </svg>
    );
  }

  if (type === "pdf") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 4h9l3 3v13H6z" />
        <path d="M15 4v3h3" />
        <path d="M8 13h8M8 17h6" />
      </svg>
    );
  }

  if (type === "text" || type === "formula") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 4h9l3 3v13H6z" />
        <path d="M15 4v3h3" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 text-slate-500" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 4h9l3 3v13H6z" />
      <path d="M15 4v3h3" />
      <path d="M10 12h4" />
    </svg>
  );
}

function getAttachmentUrl(filePath: string): string {
  const normalized = filePath.split("\\").join("/");
  const marker = "/uploads/";
  const markerIndex = normalized.indexOf(marker);

  let relativePath = normalized;
  if (markerIndex >= 0) {
    relativePath = normalized.slice(markerIndex + marker.length);
  } else {
    relativePath = normalized.replace(/^\.?\/?uploads\/?/, "");
  }

  const safePath = relativePath
    .split("/")
    .filter((segment) => segment && segment !== "." && segment !== "..")
    .map((segment) => encodeURIComponent(segment))
    .join("/");

  return `${BASE_URL}/uploads/${safePath}`;
}

function attachmentLabel(type: Attachment["attachment_type"]): string {
  if (type === "generated_image") return "Generated image";
  if (type === "pdf") return "PDF";
  if (type === "csv") return "Table";
  if (type === "formula") return "Formula";
  if (type === "code") return "Code";
  if (type === "text") return "Text";
  return "File";
}

export function AttachmentList({ attachments }: AttachmentListProps) {
  const [expandedImage, setExpandedImage] = useState<{ src: string; alt: string } | null>(null);

  if (!attachments.length) return null;

  return (
    <>
      <div className="space-y-2 mb-2">
        {attachments.map((attachment) => {
          const fileUrl = getAttachmentUrl(attachment.file_path);

          if (attachment.attachment_type === "image" || attachment.attachment_type === "generated_image") {
            return (
              <button
                key={attachment.id}
                type="button"
                onClick={() => setExpandedImage({ src: fileUrl, alt: attachment.original_filename })}
                className="block text-left"
              >
                <img
                  src={fileUrl}
                  alt={attachment.original_filename}
                  className="max-h-56 rounded-lg border border-slate-200 object-cover"
                />
              </button>
            );
          }

          if (attachment.attachment_type === "video") {
            return (
              <video
                key={attachment.id}
                controls
                className="max-h-64 w-full rounded-lg border border-slate-200"
                src={fileUrl}
              />
            );
          }

          return (
            <a
              key={attachment.id}
              href={fileUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white/70 px-3 py-2 hover:bg-white"
            >
              <div className="min-w-0 flex items-center gap-2">
                <TypeIcon type={attachment.attachment_type} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{attachment.original_filename}</p>
                  <p className="text-xs text-slate-500">{attachmentLabel(attachment.attachment_type)} • {attachment.mime_type}</p>
                </div>
              </div>
              <span className="text-xs text-slate-500">Open</span>
            </a>
          );
        })}
      </div>

      {expandedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
          onClick={() => setExpandedImage(null)}
        >
          <img
            src={expandedImage.src}
            alt={expandedImage.alt}
            className="max-h-[90vh] max-w-[90vw] rounded-lg border border-white/20"
          />
        </div>
      )}
    </>
  );
}
