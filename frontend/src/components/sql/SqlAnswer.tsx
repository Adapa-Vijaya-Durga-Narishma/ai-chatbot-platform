interface SqlAnswerProps {
  answer: string;
}

export function SqlAnswer({ answer }: SqlAnswerProps) {
  if (!answer) return null;

  return (
    <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
      <h2 className="mb-2 text-sm font-semibold text-emerald-800">Answer</h2>
      <p className="text-sm text-emerald-900 text-justify">{answer}</p>
    </section>
  );
}
