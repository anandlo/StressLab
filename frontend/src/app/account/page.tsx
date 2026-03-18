"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { CheckCircle2, AlertCircle, Shield, ShieldOff, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { UserAvatar } from "@/components/user-avatar";
import { PasswordStrength } from "@/components/password-strength";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  changePassword,
  updateProfile,
  resendVerification,
  deleteAccount,
  mfaSetup,
  mfaEnable,
  mfaDisable,
  ApiError,
} from "@/lib/api";

export default function AccountPage() {
  const { user, token, loading, logout, refreshUser, setTokenAndUser } = useAuth();
  const router = useRouter();

  // Profile
  const [phone, setPhone] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // Change password
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [savingPw, setSavingPw] = useState(false);

  // MFA
  const [mfaQr, setMfaQr] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaLoading, setMfaLoading] = useState(false);

  // Delete account
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Resend verification
  const [resending, setResending] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
    if (user) {
      setPhone(user.phone ?? "");
      setDisplayName(user.display_name ?? "");
    }
  }, [user, loading, router]);

  if (loading || !user) return null;

  // ── Profile ──────────────────────────────────────────────────────────────

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSavingProfile(true);
    try {
      await updateProfile(token, phone.trim() || null, displayName.trim() || null);
      await refreshUser();
      toast.success("Profile updated");
    } catch (err) {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("Server is temporarily unavailable. Try again shortly.");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to update profile");
      }
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleResendVerification() {
    if (!user) return;
    setResending(true);
    try {
      await resendVerification(user.email);
      toast.success("Verification link sent — check your email");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to resend link");
    } finally {
      setResending(false);
    }
  }

  // ── Change password ───────────────────────────────────────────────────────

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (newPw !== confirmPw) {
      toast.error("New passwords do not match");
      return;
    }
    if (newPw.length < 8) {
      toast.error("New password must be at least 8 characters");
      return;
    }
    setSavingPw(true);
    try {
      const result = await changePassword(token, oldPw, newPw);
      // Backend increments token_version on password change; use the fresh token
      // it returns so this session stays valid.
      if (result.access_token && user) {
        setTokenAndUser(result.access_token, user);
      }
      toast.success("Password changed");
      setOldPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Current password is incorrect");
      } else if (err instanceof ApiError && err.status === 503) {
        toast.error("Server is temporarily unavailable. Try again shortly.");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to change password");
      }
    } finally {
      setSavingPw(false);
    }
  }

  // ── MFA ───────────────────────────────────────────────────────────────────

  async function handleMfaSetup() {
    if (!token) return;
    setMfaLoading(true);
    try {
      const result = await mfaSetup(token);
      setMfaQr(result.qr_png_b64);
      setMfaCode("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start MFA setup");
    } finally {
      setMfaLoading(false);
    }
  }

  async function handleMfaEnable(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setMfaLoading(true);
    try {
      await mfaEnable(token, mfaCode);
      await refreshUser();
      setMfaQr(null);
      setMfaCode("");
      toast.success("Two-factor authentication enabled");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Invalid code — try again");
    } finally {
      setMfaLoading(false);
    }
  }

  async function handleMfaDisable() {
    if (!token) return;
    if (!confirm("Disable two-factor authentication? Your account will be less secure.")) return;
    setMfaLoading(true);
    try {
      await mfaDisable(token);
      await refreshUser();
      toast.success("Two-factor authentication disabled");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to disable MFA");
    } finally {
      setMfaLoading(false);
    }
  }

  // ── Delete account ────────────────────────────────────────────────────────

  async function handleDeleteAccount(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setDeleting(true);
    try {
      await deleteAccount(token, deletePassword);
      logout();
      toast.success("Account deleted");
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Incorrect password");
      } else if (err instanceof ApiError && err.status === 503) {
        toast.error("Server is temporarily unavailable. Try again shortly.");
      } else {
        toast.error(err instanceof Error ? err.message : "Failed to delete account");
      }
    } finally {
      setDeleting(false);
      setDeleteDialogOpen(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Account</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your profile, security settings, and account.
        </p>
      </div>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
          <CardDescription>Your email address and contact information.</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Avatar preview */}
          <div className="flex items-center gap-4 mb-6 p-4 rounded-lg bg-muted/40">
            <UserAvatar name={displayName.trim() || user.email} size={64} />
            <div>
              <p className="text-sm font-medium">{displayName.trim() || user.email.split("@")[0]}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Avatar generated from your display name.
              </p>
            </div>
          </div>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="space-y-1">
              <Label>Email</Label>
              <div className="flex items-center gap-2">
                <Input value={user.email} disabled className="flex-1" />
                {user.email_verified ? (
                  <Badge variant="secondary" className="gap-1 shrink-0">
                    <CheckCircle2 className="h-3 w-3 text-green-500" />
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="outline" className="gap-1 shrink-0 border-amber-500/40 text-amber-500">
                    <AlertCircle className="h-3 w-3" />
                    Unverified
                  </Badge>
                )}
              </div>
              {!user.email_verified && (
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs text-muted-foreground"
                  onClick={handleResendVerification}
                  disabled={resending}
                >
                  {resending ? "Sending…" : "Resend verification email"}
                </Button>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="display-name">Display name (optional)</Label>
              <Input
                id="display-name"
                type="text"
                autoComplete="nickname"
                placeholder="Your name"
                maxLength={64}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">Shown in the sidebar. Defaults to your email prefix.</p>
            </div>
            <div className="space-y-1">
              <Label htmlFor="phone">Phone (optional)</Label>
              <Input
                id="phone"
                type="tel"
                autoComplete="tel"
                placeholder="+1 555 000 0000"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={savingProfile}>
              {savingProfile ? "Saving…" : "Save profile"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Change password */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
          <CardDescription>Must be at least 8 characters.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="old-pw">Current password</Label>
              <Input
                id="old-pw"
                type="password"
                autoComplete="current-password"
                required
                value={oldPw}
                onChange={(e) => setOldPw(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new-pw">New password</Label>
              <Input
                id="new-pw"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={newPw}
                onChange={(e) => setNewPw(e.target.value)}
              />
              <PasswordStrength password={newPw} />
            </div>
            <div className="space-y-1">
              <Label htmlFor="confirm-pw">Confirm new password</Label>
              <Input
                id="confirm-pw"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPw}
                onChange={(e) => setConfirmPw(e.target.value)}
              />
            </div>
            <Button type="submit" disabled={savingPw}>
              {savingPw ? "Updating…" : "Update password"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* MFA */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Two-factor authentication</CardTitle>
              <CardDescription>
                {user.mfa_enabled
                  ? "Your account is protected with an authenticator app."
                  : "Add an extra layer of security using an authenticator app."}
              </CardDescription>
            </div>
            {user.mfa_enabled ? (
              <Shield className="h-5 w-5 text-green-500 shrink-0" />
            ) : (
              <ShieldOff className="h-5 w-5 text-muted-foreground shrink-0" />
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {user.mfa_enabled ? (
            <Button
              variant="outline"
              onClick={handleMfaDisable}
              disabled={mfaLoading}
            >
              {mfaLoading ? "Disabling…" : "Disable two-factor authentication"}
            </Button>
          ) : mfaQr ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Scan this QR code with your authenticator app (Google Authenticator,
                Authy, etc.), then enter the 6-digit code to confirm.
              </p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`data:image/png;base64,${mfaQr}`}
                alt="TOTP QR code"
                className="rounded-md border w-48 h-48"
              />
              <form onSubmit={handleMfaEnable} className="flex gap-2 max-w-xs">
                <Input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  placeholder="000000"
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ""))}
                  required
                />
                <Button type="submit" disabled={mfaLoading || mfaCode.length < 6}>
                  {mfaLoading ? "Verifying…" : "Enable"}
                </Button>
              </form>
              <Button variant="ghost" size="sm" onClick={() => setMfaQr(null)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button onClick={handleMfaSetup} disabled={mfaLoading}>
              {mfaLoading ? "Loading…" : "Set up two-factor authentication"}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Delete account</CardTitle>
          <CardDescription>
            Permanently removes your account, projects, and saved protocols.
            Session records are kept for research integrity.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogTrigger>
              <Button variant="destructive" size="sm">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete my account
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete account</DialogTitle>
                <DialogDescription>
                  This action is permanent and cannot be undone. Enter your current
                  password to confirm.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleDeleteAccount} className="space-y-4">
                <div className="space-y-1">
                  <Label htmlFor="del-pw">Current password</Label>
                  <Input
                    id="del-pw"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                  />
                </div>
                <DialogFooter>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setDeleteDialogOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="destructive" disabled={deleting}>
                    {deleting ? "Deleting…" : "Delete account"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  );
}
