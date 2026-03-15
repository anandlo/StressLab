"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { mfaVerify } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function MFAVerifyContent() {
  const searchParams = useSearchParams();
  const mfaToken = searchParams.get("token") ?? "";
  const { setTokenAndUser } = useAuth();
  const router = useRouter();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!mfaToken) {
      toast.error("Missing MFA token. Please sign in again.");
      router.push("/login");
    }
  }, [mfaToken, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await mfaVerify(mfaToken, code.trim());
      setTokenAndUser(result.access_token, result.user);
      toast.success("Signed in");
      router.push("/");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Invalid code");
      setCode("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Two-factor authentication</CardTitle>
          <CardDescription>
            Enter the 6-digit code from your authenticator app.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="code">Code</Label>
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
            <Button type="submit" className="w-full" disabled={loading || code.length !== 6}>
              {loading ? "Verifying…" : "Verify"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function MFAVerifyPage() {
  return (
    <Suspense>
      <MFAVerifyContent />
    </Suspense>
  );
}
