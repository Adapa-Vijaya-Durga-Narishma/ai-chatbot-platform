import { useRef } from "react";

interface PdfUploadButtonProps {
  onPdfSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function PdfUploadButton({ onPdfSelected, disabled }: PdfUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSelect = () => {
    if (!disabled) {
      inputRef.current?.click();
    }
  };

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []).filter(
      (file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
    );
    if (files.length > 0) {
      onPdfSelected(files);
    }
    event.target.value = "";
  };

  return (
    <>
      <button
        type="button"
        onClick={handleSelect}
        disabled={disabled}
        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50"
      >
        Upload PDF
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        onChange={handleChange}
        className="hidden"
      />
    </>
  );
}
