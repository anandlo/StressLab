"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mfaSetup, mfaEnable } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function MFASetupPage() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [setup, setSetup] = useState<{ secret: string; qr_png_b64: string } | null>(null);
  const [code, setCode] = useState("");
  const [loadingSetup, setLoadingSetup] = useState(false);
  const [loadingEnable, setLoadingEnable] = useState(false);

  if (!token || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground text-center">
              You must be signed in to set up two-factor authentication.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  async function handleStartSetup() {
    if (!token) return;
    setLoadingSetup(true);
    try {
      const data = await mfaSetup(token);
      setSetup(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setLoadingSetup(false);
    }
  }

  async function handleEnable(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setLoadingEnable(true);
    try {
      await mfaEnable(token, code.trim());
      toast.success("Two-factor authentication enabled");
      router.push("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Invalid code");
      setCode("");
    } finally {
      setLoadingEnable(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Set up two-factor authentication</CardTitle>
          <CardDescription>
            Use an authenticator app (e.g. Google Authenticator, Authy) to scan the QR code.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {!setup ? (
            <Button onClick={handleStartSetup} disabled={loadingSetup} className="w-full">
              {loadingSetup ? "Generating…" : "Generate QR code"}
            </Button>
          ) : (
            <>
              <div className="flex flex-col items-center gap-4">
                <img
                  src={`data:image/png;base64,${setup.qr_png_b64}`}
                  alt="TOTP QR code"
                  className="rounded border border-border w-48 h-48"
                />
                <div className="text-center">
                  <p className="text-xs text-muted-foreground mb-1">Manual entry key</p>
                  <code className="text-sm font-mono bg-muted px-2 py-1 rounded select-all">
                    {setup.secret}
                  </code>
                </div>
              </div>
              <form onSubmit={handleEnable} className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="code">Confirm code from app</Label>
                  <Input
                    id="code"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    autoComplete="one-time-code"
                    placeholder="000000"
                    required
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={loadingEnable || code.length !== 6}
                >
                  {loadingEnable ? "Enabling…" : "Enable two-factor authentication"}
                </Button>
              </form>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
