import { useId, useState } from "react";

interface DataframeUploadProps {
  isBusy: boolean;
  onUpload: (file: File) => Promise<void>;
}

const ALLOWED_EXTENSIONS = [".csv", ".xlsx"];
const ALLOWED_MIME_TYPES = [
  "text/csv",
  "application/csv",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
];
const MAX_FILE_SIZE_MB = 10;

export function DataframeUpload({ isBusy, onUpload }: DataframeUploadProps) {
  const inputId = useId();
  const [selectedName, setSelectedName] = useState<string>("");
  const [validationError, setValidationError] = useState<string>("");

  function validateFile(file: File): string | null {
    // Check file extension
    const fileName = file.name.toLowerCase();
    const hasValidExtension = ALLOWED_EXTENSIONS.some(ext => fileName.endsWith(ext));
    if (!hasValidExtension) {
      return `Invalid file type. Only CSV and XLSX files are allowed. You selected: ${file.name}`;
    }

    // Check MIME type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return `Invalid file MIME type: ${file.type}. Only CSV and XLSX files are allowed.`;
    }

    // Check file size
    const fileSizeMB = file.size / (1024 * 1024);
    if (fileSizeMB > MAX_FILE_SIZE_MB) {
      return `File size ${fileSizeMB.toFixed(2)}MB exceeds maximum allowed size of ${MAX_FILE_SIZE_MB}MB.`;
    }

    return null;
  }

  async function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      setValidationError("");
      return;
    }

    const error = validateFile(file);
    if (error) {
      setValidationError(error);
      setSelectedName("");
      event.target.value = "";
      return;
    }

    setValidationError("");
    setSelectedName(file.name);
    await onUpload(file);
    event.target.value = "";
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Upload CSV or Excel</h2>
        <p className="text-sm text-slate-600">Supported formats: .csv and .xlsx (max {MAX_FILE_SIZE_MB}MB)</p>
      </div>

      <label
        htmlFor={inputId}
        className="inline-flex cursor-pointer items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
      >
        {isBusy ? "Uploading..." : "Choose file"}
      </label>
      <input
        id={inputId}
        type="file"
        accept=".csv,.xlsx"
        onChange={(event) => void handleChange(event)}
        className="hidden"
        disabled={isBusy}
      />

      {validationError && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
          <p className="text-sm text-rose-700">{validationError}</p>
        </div>
      )}

      {selectedName && !validationError && (
        <p className="text-sm text-slate-500">Selected: {selectedName}</p>
      )}
    </section>
  );
}