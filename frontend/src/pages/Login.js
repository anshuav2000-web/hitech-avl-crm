import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatApiError } from "@/lib/api";
import { ArrowRight } from "lucide-react";
import { HitechLogo } from "@/components/Brand";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@hitechaudio.in");
  const [password, setPassword] = useState("Admin@123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white">
      {/* Left - Form */}
      <div className="flex flex-col px-8 lg:px-16 py-10">
        <div className="flex items-center gap-2.5 mb-auto">
          <HitechLogo className="h-9" />
        </div>

        <div className="max-w-md w-full mx-auto py-12">
          <div className="label-eyebrow mb-4">Sales OS · v1.0</div>
          <h1 className="font-display text-4xl font-bold tracking-tighter text-slate-900 mb-3">
            Sign in to your<br />command center.
          </h1>
          <p className="text-sm text-slate-600 mb-10 leading-relaxed">
            Manage prospects from WhatsApp, email & your website — all in one
            workspace built for the Hitech sales floor.
          </p>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
            <div>
              <label className="label-eyebrow block mb-2">Work Email</label>
              <input
                data-testid="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@hitechaudio.in"
                className="w-full px-4 py-3 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none transition-all"
              />
            </div>
            <div>
              <label className="label-eyebrow block mb-2">Password</label>
              <input
                data-testid="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 border border-slate-200 rounded-md text-sm focus:ring-2 focus:ring-slate-900/10 focus:border-slate-900 outline-none transition-all"
              />
            </div>
            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-md" data-testid="login-error">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit"
              className="w-full text-white font-medium rounded-md px-4 py-3 hover:opacity-90 transition-all flex items-center justify-center gap-2 disabled:opacity-60"
              style={{ background: "#DC2626" }}
            >
              {loading ? "Signing in…" : "Continue"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          <div className="mt-8 text-xs text-slate-500">
            Need a public capture form?{" "}
            <Link to="/capture" className="text-slate-900 font-medium hover:underline" data-testid="capture-link">
              Open lead form →
            </Link>
          </div>
        </div>

        <div className="text-xs text-slate-400 mt-auto">
          © {new Date().getFullYear()} Hitech Audio and Image LLP. All brands distributed under license.
        </div>
      </div>

      {/* Right - Visual */}
      <div className="hidden lg:block relative bg-slate-900 grid-bg overflow-hidden">
        <img
          src="https://images.unsplash.com/photo-1642426028488-04f91c79d233?w=1200&q=80"
          alt="Pro audio"
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-tr from-slate-900/90 via-slate-900/40 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-12 text-white">
          <div className="label-eyebrow text-white/70 mb-4">Built for India · Imported brands</div>
          <div className="font-display text-3xl font-bold leading-tight max-w-md">
            "Every prospect, every brand, every follow-up — in one ruthless workflow."
          </div>
          <div className="mt-6 flex items-center gap-3 text-sm text-white/80">
            <div className="w-12 h-px bg-white/40" />
            Hitech Audio · Operations Playbook
          </div>
        </div>
      </div>
    </div>
  );
}
