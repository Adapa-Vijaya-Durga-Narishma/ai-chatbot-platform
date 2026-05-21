import { useState, type FormEvent } from "react";
import { register } from "../../lib/api";

interface Props {
  onSwitchToLogin: () => void;
}

export function RegisterForm({ onSwitchToLogin }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      await register({ email, password });
      setSuccess("Registration successful. Please sign in.");
      setEmail("");
      setPassword("");
      onSwitchToLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-transparent">
      <div className="w-full max-w-md p-8 bg-white/90 border border-slate-200 rounded-3xl shadow-sm backdrop-blur">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2 text-center">
          Create account
        </h1>
        <p className="text-center text-sm text-slate-500 mb-6">Set up your workspace access</p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-rose-50 text-rose-700 text-sm border border-rose-200">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-emerald-50 text-emerald-700 text-sm border border-emerald-200">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Password{" "}
              <span className="text-slate-400 font-normal">(min 8 chars)</span>
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-300"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white font-semibold rounded-xl transition-colors"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          Already have an account?{" "}
          <button
            onClick={onSwitchToLogin}
            className="text-sky-700 hover:underline font-medium"
          >
            Sign in
          </button>
        </p>
      </div>
    </div>
  );
}
