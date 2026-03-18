"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { ApiError, resendVerification } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [resending, setResending] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setUnverifiedEmail(null);
    setLoading(true);
    try {
      const result = await login(email.trim(), password);
      if (result.mfa_required && result.mfa_token) {
        sessionStorage.setItem("mfa_pending_token", result.mfa_token);
        router.push("/mfa-verify");
      } else {
        toast.success("Signed in");
        router.push("/");
      }
    } catch (err) {
      if (err instanceof ApiError) {
        switch (err.status) {
          case 401:
            toast.error("Invalid email or password");
            break;
          case 403:
            setUnverifiedEmail(email.trim());
            toast.error("Please verify your email address before signing in.");
            break;
          case 423:
            toast.error("Account temporarily locked. Too many failed attempts — try again in 15 minutes.");
            break;
          case 429:
            toast.error("Too many attempts. Please wait a few minutes.");
            break;
          case 503:
            toast.error("Server is temporarily unavailable. Try again shortly.");
            break;
          default:
            toast.error(err.message);
        }
      } else {
        toast.error("Login failed");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleResendVerification() {
    if (!unverifiedEmail) return;
    setResending(true);
    try {
      await resendVerification(unverifiedEmail);
      toast.success("Verification link sent — check your inbox");
    } catch {
      toast.error("Failed to resend verification email");
    } finally {
      setResending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>Sign in to save and manage your projects.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="text-right">
              <Link href="/forgot-password" className="text-sm text-muted-foreground underline underline-offset-2 hover:text-foreground">
                Forgot password?
              </Link>
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </Button>            {unverifiedEmail && (
              <p className="text-center text-sm text-muted-foreground">
                Didn&apos;t get the email?{" "}
                <button
                  type="button"
                  className="underline underline-offset-2 hover:text-foreground"
                  disabled={resending}
                  onClick={handleResendVerification}
                >
                  {resending ? "Sending\u2026" : "Resend verification"}
                </button>
              </p>
            )}            <p className="text-center text-sm text-muted-foreground">
              No account?{" "}
              <Link href="/register" className="underline underline-offset-2 hover:text-foreground">
                Register
              </Link>
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
