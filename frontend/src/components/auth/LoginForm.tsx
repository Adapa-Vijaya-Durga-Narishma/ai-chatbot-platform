import { useState, type FormEvent } from "react";
import { getGoogleLoginUrl, login } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";

interface Props {
  onSwitchToRegister: () => void;
}

export function LoginForm({ onSwitchToRegister }: Props) {
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password });
      setUser(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  function handleGoogleLogin() {
    window.location.href = getGoogleLoginUrl();
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-transparent">
      <div className="w-full max-w-md p-8 bg-white/90 border border-slate-200 rounded-3xl shadow-sm backdrop-blur">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2 text-center">
          Sign in
        </h1>
        <p className="text-center text-sm text-slate-500 mb-6">Welcome back to your workspace</p>

        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-rose-50 text-rose-700 text-sm border border-rose-200">
            {error}
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
              Password
            </label>
            <input
              type="password"
              required
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
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-4">
          <button
            type="button"
            onClick={handleGoogleLogin}
            className="w-full py-2.5 px-4 border border-slate-300 bg-white text-slate-700 font-semibold rounded-xl transition-colors hover:bg-slate-50"
          >
            Login with Google
          </button>
        </div>

        <p className="mt-4 text-center text-sm text-slate-500">
          No account?{" "}
          <button
            onClick={onSwitchToRegister}
            className="text-sky-700 hover:underline font-medium"
          >
            Register
          </button>
        </p>
      </div>
    </div>
  );
}
