"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  SessionConfig,
  Trial,
  SessionScore,
  SessionSummary,
  WSIncomingMessage,
  WSOutgoingMessage,
} from "@/lib/types";
import { SessionState } from "@/lib/types";

export interface LiveResult {
  is_correct: boolean;
  correct_answer: string;
  user_response: string;
  timed_out: boolean;
  response_time_ms: number;
}

interface UseSessionReturn {
  state: SessionState;
  trial: Trial | null;
  trialCount: number;
  score: SessionScore | null;
  feedback: string | null;
  lastResult: LiveResult | null;
  summary: SessionSummary | null;
  sessionFile: string | null;
  restInfo: { duration_sec: number; block: number; total_blocks: number } | null;
  error: string | null;
  start: (config: SessionConfig) => void;
  submitResponse: (response: string, responseTimeMs: number, timedOut: boolean) => void;
  requestTrial: () => void;
  restComplete: () => void;
  stop: () => void;
  discard: () => void;
}

export function useSessionWS(): UseSessionReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [state, setState] = useState<SessionState>(SessionState.IDLE);
  const [trial, setTrial] = useState<Trial | null>(null);
  const [score, setScore] = useState<SessionScore | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<LiveResult | null>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [restInfo, setRestInfo] = useState<{
    duration_sec: number;
    block: number;
    total_blocks: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [trialCount, setTrialCount] = useState<number>(0);
  const [sessionFile, setSessionFile] = useState<string | null>(null);

  function send(msg: WSOutgoingMessage) {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }

  function connect() {
    // Derive WebSocket URL from NEXT_PUBLIC_API_URL when set (Vercel + separate backend).
    // Falls back to same-origin when FastAPI is serving the frontend directly (local dev).
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const wsUrl = apiUrl
      ? apiUrl.replace(/^https:/, "wss:").replace(/^http:/, "ws:") + "/ws/session"
      : (() => {
          const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
          return `${proto}//${window.location.host}/ws/session`;
        })();
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg: WSIncomingMessage = JSON.parse(event.data);

      switch (msg.type) {
        case "session_started":
          setState(SessionState.RUNNING);
          if (msg.score) setScore(msg.score);
          send({ type: "request_trial" });
          break;

        case "trial":
          setTrial(msg.data as Trial);
          setFeedback(null);
          setLastResult(null);
          setState(SessionState.RUNNING);
          setTrialCount((prev) => prev + 1);
          break;

        case "result": {
          const d = msg.data as { correct: boolean; correct_answer: string; user_response: string; timed_out: boolean; response_time_ms: number; score: SessionScore; feedback: string | null };
          setLastResult({
            is_correct: d.correct,
            correct_answer: d.correct_answer,
            user_response: d.user_response,
            timed_out: d.timed_out,
            response_time_ms: d.response_time_ms,
          });
          setScore(d.score);
          if (d.feedback) setFeedback(d.feedback);
          setTimeout(() => send({ type: "request_trial" }), 600);
          break;
        }

        case "rest":
          setState(SessionState.REST);
          setRestInfo({
            duration_sec: (msg.data as { duration_sec: number; block_completed: number; total_blocks: number }).duration_sec,
            block: (msg.data as { block_completed: number }).block_completed,
            total_blocks: (msg.data as { total_blocks: number }).total_blocks,
          });
          break;

        case "session_complete":
          setState(SessionState.COMPLETE);
          setSummary(msg.data as SessionSummary);
          setSessionFile(msg.session_file ?? null);
          break;

        case "session_discarded":
          setState(SessionState.COMPLETE);
          setSummary(null);
          setSessionFile(null);
          break;

        case "error":
          setError(msg.message);
          break;
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error. Is the backend running on port 8000?");
    };

    ws.onclose = () => {
      if (state !== SessionState.COMPLETE) {
        wsRef.current = null;
      }
    };
  }

  const start = useCallback(
    (config: SessionConfig) => {
      setError(null);
      setSummary(null);
      setScore(null);
      setTrial(null);
      setFeedback(null);
      setLastResult(null);
      setRestInfo(null);
      setTrialCount(0);
      setSessionFile(null);
      connect();
      // Wait for connection, then send start
      const check = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          clearInterval(check);
          setState(SessionState.RUNNING);
          // Include the JWT so the backend knows whether to persist the session
          // server-side. Guests (no token) run fully in-memory.
          const token = typeof window !== "undefined"
            ? (localStorage.getItem("stresslab_token") ?? undefined)
            : undefined;
          send({ type: "start_session", config, ...(token ? { auth_token: token } : {}) });
        }
      }, 50);
      // Timeout after 5s -- surface error so the user isn't silently stuck
      setTimeout(() => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) {
          clearInterval(check);
          setError("Could not connect to session server. Is the backend running on port 8000?");
        }
      }, 5000);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const submitResponse = useCallback(
    (response: string, responseTimeMs: number, timedOut: boolean) => {
      if (!trial) return;
      send({
        type: "submit_response",
        trial_id: trial.trial_id,
        response,
        response_time_ms: responseTimeMs,
        timed_out: timedOut,
      });
    },
    [trial]
  );

  const requestTrial = useCallback(() => {
    send({ type: "request_trial" });
  }, []);

  const restComplete = useCallback(() => {
    send({ type: "rest_complete" });
    setRestInfo(null);
    setState(SessionState.RUNNING);
  }, []);

  const stop = useCallback(() => {
    send({ type: "stop_session" });
  }, []);

  const discard = useCallback(() => {
    send({ type: "discard_session" });
  }, []);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return {
    state,
    trial,
    trialCount,
    score,
    feedback,
    lastResult,
    summary,
    sessionFile,
    restInfo,
    error,
    start,
    submitResponse,
    requestTrial,
    restComplete,
    stop,
    discard,
  };
}
