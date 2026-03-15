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

export function useSessions(participantId?: string) {
  return useQuery({
    queryKey: ["sessions", participantId],
    queryFn: () => listSessions(participantId),
    staleTime: 10_000,
  });
}

export function useSession(filename: string | null) {
  return useQuery({
    queryKey: ["session", filename],
    queryFn: () => getSession(filename!),
    enabled: !!filename,
  });
}
