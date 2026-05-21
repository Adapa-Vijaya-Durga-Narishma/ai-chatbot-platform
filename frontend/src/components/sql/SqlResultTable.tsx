interface SqlResultTableProps {
  rows: Record<string, unknown>[];
}

export function SqlResultTable({ rows }: SqlResultTableProps) {
  if (!rows.length) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Rows</h2>
        <p className="text-sm text-slate-500">No rows returned.</p>
      </section>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Rows ({rows.length})</h2>
      <div className="max-h-[420px] overflow-auto rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th key={column} className="whitespace-nowrap px-3 py-2 font-semibold text-slate-700">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {columns.map((column) => (
                  <td key={`${rowIndex}-${column}`} className="whitespace-nowrap px-3 py-2 text-slate-600">
                    {String(row[column] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
