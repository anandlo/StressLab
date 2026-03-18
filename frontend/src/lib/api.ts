import type { ParadigmMeta, ProtocolPreset, Participant, SessionListItem, SessionSummary, Trial, User, Project } from "./types";

// In production (Vercel + separate backend), set NEXT_PUBLIC_API_URL to your backend URL,
// e.g. https://your-backend.railway.app
// Locally with FastAPI serving the frontend directly, leave it unset (relative URLs).
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

/** Error thrown by API calls, carrying the HTTP status code. */
export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${url}`, init);
  } catch {
    throw new ApiError(0, "Unable to reach the server. Check your connection.");
  }
  if (!res.ok) {
    let detail: string | undefined;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : undefined;
    } catch { /* body wasn't JSON */ }
    throw new ApiError(res.status, detail ?? `Request failed (${res.status})`);
  }
  return res.json();
}

export function fetchParadigms(): Promise<ParadigmMeta[]> {
  return fetchJSON("/api/paradigms");
}

export function fetchProtocols(): Promise<ProtocolPreset[]> {
  return fetchJSON("/api/protocols");
}

export function createParticipant(
  participantId: string,
  demographics?: Record<string, string | number | null>
): Promise<Participant> {
  return fetchJSON("/api/participants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: participantId, demographics }),
  });
}

export function listParticipants(): Promise<Participant[]> {
  return fetchJSON("/api/participants");
}

export function getParticipant(id: string): Promise<Participant> {
  return fetchJSON(`/api/participants/${encodeURIComponent(id)}`);
}

export function listSessions(token: string, participantId?: string): Promise<SessionListItem[]> {
  const params = participantId ? `?participant_id=${encodeURIComponent(participantId)}` : "";
  return fetchJSON(`/api/sessions${params}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function getSession(token: string, filename: string): Promise<SessionSummary> {
  return fetchJSON(`/api/sessions/${encodeURIComponent(filename)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function generatePracticeTrials(paradigmIds: string[]): Promise<Trial[]> {
  return fetchJSON("/api/practice-trials", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paradigm_ids: paradigmIds }),
  });
}

export function deleteParticipant(id: string): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/participants/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export function downloadSessionCSV(token: string, filename: string): void {
  fetch(`${BASE}/api/sessions/${encodeURIComponent(filename)}/csv`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (!res.ok) throw new Error(`${res.status}`);
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename.replace(".json", ".csv");
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch(() => {/* caller handles via toast */});
}

export function patchSessionNotes(token: string, filename: string, notes: string): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/sessions/${encodeURIComponent(filename)}/notes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ notes }),
  });
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export function registerUser(
  email: string,
  password: string,
  phone?: string,
): Promise<{ message: string; user_id: string }> {
  return fetchJSON("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, phone: phone ?? null }),
  });
}

export function loginUser(
  email: string,
  password: string,
): Promise<{ mfa_required?: boolean; mfa_token?: string; access_token?: string; user?: User }> {
  return fetchJSON("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function mfaVerify(
  mfa_token: string,
  code: string,
): Promise<{ access_token: string; user: User }> {
  return fetchJSON("/api/auth/mfa/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mfa_token, code }),
  });
}

export function getMe(token: string): Promise<User> {
  return fetchJSON("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function mfaSetup(token: string): Promise<{ secret: string; qr_png_b64: string }> {
  return fetchJSON("/api/auth/mfa/setup", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function mfaEnable(token: string, code: string): Promise<{ ok: boolean }> {
  return fetchJSON("/api/auth/mfa/enable", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ code }),
  });
}

export function mfaDisable(token: string): Promise<{ ok: boolean }> {
  return fetchJSON("/api/auth/mfa/disable", {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function resendVerification(email: string): Promise<{ ok: boolean; message: string }> {
  return fetchJSON("/api/auth/resend-verification", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export function changePassword(
  token: string,
  oldPassword: string,
  newPassword: string,
): Promise<{ ok: boolean; access_token?: string }> {
  return fetchJSON("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

export function forgotPassword(email: string): Promise<{ ok: boolean; message: string }> {
  return fetchJSON("/api/auth/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(
  token: string,
  newPassword: string,
): Promise<{ ok: boolean; message: string }> {
  return fetchJSON("/api/auth/reset-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function refreshAuthToken(
  token: string,
): Promise<{ access_token: string; user: User }> {
  return fetchJSON("/api/auth/refresh", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function logoutUser(token: string): Promise<{ ok: boolean }> {
  return fetchJSON("/api/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function updateProfile(
  token: string,
  phone: string | null,
  displayName: string | null,
): Promise<User> {
  return fetchJSON("/api/auth/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ phone, display_name: displayName }),
  });
}

export function deleteSession(token: string, filename: string): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/sessions/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function deleteAccount(
  token: string,
  password: string,
): Promise<{ ok: boolean; message: string }> {
  return fetchJSON("/api/auth/account", {
    method: "DELETE",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ password }),
  });
}

export function verifyEmail(token: string): Promise<{ ok: boolean; message: string }> {
  return fetchJSON(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
}

// ── Projects ──────────────────────────────────────────────────────────────────

export function listProjects(token: string): Promise<Project[]> {
  return fetchJSON("/api/projects", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createProject(
  token: string,
  name: string,
  description: string,
): Promise<Project> {
  return fetchJSON("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ name, description }),
  });
}

export function getProject(token: string, projectId: string): Promise<Project> {
  return fetchJSON(`/api/projects/${encodeURIComponent(projectId)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function deleteProject(token: string, projectId: string): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/projects/${encodeURIComponent(projectId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function attachSessionToProject(
  token: string,
  projectId: string,
  sessionFile: string,
): Promise<Project> {
  return fetchJSON(`/api/projects/${encodeURIComponent(projectId)}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ session_file: sessionFile }),
  });
}

export function detachSessionFromProject(
  token: string,
  projectId: string,
  filename: string,
): Promise<Project> {
  return fetchJSON(
    `/api/projects/${encodeURIComponent(projectId)}/sessions/${encodeURIComponent(filename)}`,
    { method: "DELETE", headers: { Authorization: `Bearer ${token}` } },
  );
}

// --- User field templates ---

export function getFieldTemplates(token: string): Promise<{ templates: string[] }> {
  return fetchJSON("/api/user/field-templates", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function saveFieldTemplates(
  token: string,
  templates: string[],
): Promise<{ templates: string[] }> {
  return fetchJSON("/api/user/field-templates", {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ templates }),
  });
}

// ── User Protocols ────────────────────────────────────────────────────────────

export interface UserProtocolConfig {
  id: string;
  name: string;
  created: string;
  mode: string;
  preset_id: string | null;
  paradigm_ids: string[];
  duration_min: number;
  intensity: string;
  blocks: number;
  rest_duration_sec: number;
  practice_enabled: boolean;
}

export function listUserProtocols(token: string): Promise<UserProtocolConfig[]> {
  return fetchJSON("/api/user-protocols", { headers: { Authorization: `Bearer ${token}` } });
}

export function saveUserProtocol(
  token: string,
  protocol: Omit<UserProtocolConfig, "id" | "created">,
): Promise<UserProtocolConfig> {
  return fetchJSON("/api/user-protocols", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(protocol),
  });
}

export function deleteUserProtocol(token: string, protocolId: string): Promise<{ ok: boolean }> {
  return fetchJSON(`/api/user-protocols/${encodeURIComponent(protocolId)}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}
