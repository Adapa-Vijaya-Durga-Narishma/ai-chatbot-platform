interface SqlGeneratedQueryProps {
  sql: string;
}

export function SqlGeneratedQuery({ sql }: SqlGeneratedQueryProps) {
  if (!sql) return null;

  return (
    <section className="rounded-xl border border-slate-200 bg-slate-50 p-4">
      <h2 className="mb-2 text-sm font-semibold text-slate-700">Generated SQL</h2>
      <pre className="overflow-x-auto rounded-md bg-slate-900 p-3 text-xs text-slate-100">{sql}</pre>
    </section>
  );
}
