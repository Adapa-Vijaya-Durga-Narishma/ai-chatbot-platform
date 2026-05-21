import { useState } from "react";

interface GoogleSheetInputProps {
  isBusy: boolean;
  onConnect: (sheetUrl: string) => Promise<void>;
}

export function GoogleSheetInput({ isBusy, onConnect }: GoogleSheetInputProps) {
  const [sheetUrl, setSheetUrl] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    event.stopPropagation();
    await onConnect(sheetUrl);
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-slate-900">Connect Google Sheet</h2>
        <p className="text-sm text-slate-600">Paste a Google Sheets URL shared with your service account.</p>
      </div>

      <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <input
          type="url"
          value={sheetUrl}
          onChange={(event) => setSheetUrl(event.target.value)}
          placeholder="https://docs.google.com/spreadsheets/d/..."
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400"
          disabled={isBusy}
        />
        <button
          type="submit"
          disabled={isBusy || !sheetUrl.trim()}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {isBusy ? "Connecting to Google Sheets..." : "Connect sheet"}
        </button>
      </form>
    </section>
  );
}