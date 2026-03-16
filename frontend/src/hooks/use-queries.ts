"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchParadigms, fetchProtocols, listParticipants, listSessions, getSession } from "@/lib/api";

export function useParadigms() {
  return useQuery({
    queryKey: ["paradigms"],
    queryFn: fetchParadigms,
    staleTime: Infinity,
  });
}

export function useProtocols() {
  return useQuery({
    queryKey: ["protocols"],
    queryFn: fetchProtocols,
    staleTime: Infinity,
  });
}

export function useParticipants() {
  return useQuery({
    queryKey: ["participants"],
    queryFn: listParticipants,
    staleTime: 30_000,
  });
}

export function useSessions(token: string | null, participantId?: string) {
  return useQuery({
    queryKey: ["sessions", participantId, !!token],
    queryFn: () => listSessions(token!, participantId),
    staleTime: 10_000,
    enabled: !!token,
  });
}

export function useSession(token: string | null, filename: string | null) {
  return useQuery({
    queryKey: ["session", filename],
    queryFn: () => getSession(token!, filename!),
    enabled: !!filename && !!token,
  });
}
