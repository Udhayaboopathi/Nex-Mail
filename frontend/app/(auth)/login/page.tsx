"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Eye, EyeOff, Mail } from "lucide-react";
import { authApi } from "../../../lib/api";
import { setToken } from "../../../lib/auth";
import { toast } from "../../../components/ui/Toast";
import type { Role } from "../../../types";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [totpStep, setTotpStep] = useState(false);
  const [totpCode, setTotpCode] = useState("");
  const [tempToken, setTempToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      if ((res as unknown as { requires_totp: boolean }).requires_totp) {
        setTempToken((res as unknown as { temp_token: string }).temp_token);
        setTotpStep(true);
      } else {
        finalize(res.access_token, res.role ?? "user");
      }
    } catch (err) {
      setError((err as Error).message ?? "Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  async function handleTotp(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.verifyTotp(tempToken, totpCode);
      finalize(res.access_token, res.role ?? "user");
    } catch {
      setError("Invalid TOTP code");
    } finally {
      setLoading(false);
    }
  }

  function finalize(token: string, role: Role | undefined) {
    setToken(token, role ?? "user");
    if (typeof window !== "undefined") {
      localStorage.setItem("nex_email", email);
    }
    if (role === "super_admin") router.push("/super-admin");
    else if (role === "domain_admin") router.push("/domain-admin");
    else router.push("/mail/inbox");
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-indigo-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-indigo-600 rounded-2xl mb-4 shadow-lg">
            <Mail className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Nex Mail</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">Sign in to your account</p>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-100 dark:border-gray-800 p-8">
          {!totpStep ? (
            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm"
                  placeholder="you@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPw ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    className="w-full px-4 py-2.5 pr-11 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 text-sm"
                    placeholder="••••••••"
                  />
                  <button type="button" onClick={() => setShowPw((o) => !o)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {error ? (
                <p
                  role="alert"
                  className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg border border-red-100 dark:border-red-900/40"
                >
                  {error}
                </p>
              ) : null}

              <div className="flex items-start justify-between gap-3 text-sm">
                <label className="flex items-center gap-2 cursor-pointer text-gray-600 dark:text-gray-400 shrink-0">
                  <input type="checkbox" className="accent-indigo-600" /> Remember me
                </label>
                <Link href="/forgot-password" className="text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap">
                  Forgot password?
                </Link>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white font-medium transition-colors disabled:opacity-60"
              >
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleTotp} className="space-y-5">
              <div className="text-center">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Two-factor authentication</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Enter the 6-digit code from your authenticator app.</p>
              </div>
              <input
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                className="w-full px-4 py-3 text-center text-2xl tracking-widest rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
              {error && <p className="text-sm text-red-600 dark:text-red-400 text-center">{error}</p>}
              <button type="submit" disabled={loading || totpCode.length < 6} className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium disabled:opacity-60">
                {loading ? "Verifying…" : "Verify"}
              </button>
              <button type="button" onClick={() => setTotpStep(false)} className="w-full text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">← Back to login</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
