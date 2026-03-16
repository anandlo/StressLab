"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { verifyEmail } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type State = "pending" | "success" | "error";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [state, setState] = useState<State>("pending");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("No verification token found in the URL.");
      return;
    }
    verifyEmail(token)
      .then((res) => {
        setState("success");
        setMessage(res.message);
      })
      .catch((err) => {
        setState("error");
        setMessage(err instanceof Error ? err.message : "Verification failed.");
      });
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Email verification</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {state === "pending" && (
            <p className="text-sm text-muted-foreground">Verifying…</p>
          )}
          {state === "success" && (
            <>
              <p className="text-sm text-green-600">{message}</p>
              <Link href="/login" className={cn(buttonVariants(), "w-full justify-center")}>
                Sign in
              </Link>
            </>
          )}
          {state === "error" && (
            <>
              <p className="text-sm text-destructive">{message}</p>
              <Link href="/" className={cn(buttonVariants({ variant: "outline" }), "w-full justify-center")}>
                Back to home
              </Link>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailContent />
    </Suspense>
  );
}
