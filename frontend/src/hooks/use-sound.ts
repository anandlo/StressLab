"use client";

import { useRef, useCallback } from "react";

function tone(
  ctx: AudioContext,
  freq: number,
  durationSec: number,
  type: OscillatorType,
  gainPeak: number,
  startDelay = 0
) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.type = type;
  osc.frequency.setValueAtTime(freq, ctx.currentTime + startDelay);
  gain.gain.setValueAtTime(0.001, ctx.currentTime + startDelay);
  gain.gain.linearRampToValueAtTime(gainPeak, ctx.currentTime + startDelay + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startDelay + durationSec);
  osc.start(ctx.currentTime + startDelay);
  osc.stop(ctx.currentTime + startDelay + durationSec + 0.02);
}

export function useSound() {
  const ctxRef = useRef<AudioContext | null>(null);

  function getCtx(): AudioContext | null {
    if (typeof window === "undefined") return null;
    try {
      if (!ctxRef.current || ctxRef.current.state === "closed") {
        ctxRef.current = new AudioContext();
      }
      if (ctxRef.current.state === "suspended") {
        ctxRef.current.resume().catch(() => {});
      }
    } catch {
      return null;
    }
    return ctxRef.current;
  }

  const playTrialStart = useCallback(() => {
    const ctx = getCtx();
    if (!ctx) return;
    tone(ctx, 880, 0.07, "sine", 0.18);
  }, []);

  const playCorrect = useCallback(() => {
    const ctx = getCtx();
    if (!ctx) return;
    tone(ctx, 523, 0.10, "sine", 0.22, 0);
    tone(ctx, 659, 0.12, "sine", 0.22, 0.11);
  }, []);

  const playIncorrect = useCallback(() => {
    const ctx = getCtx();
    if (!ctx) return;
    tone(ctx, 220, 0.18, "sawtooth", 0.10);
  }, []);

  const playRest = useCallback(() => {
    const ctx = getCtx();
    if (!ctx) return;
    tone(ctx, 440, 0.5, "sine", 0.16);
  }, []);

  const playSessionEnd = useCallback(() => {
    const ctx = getCtx();
    if (!ctx) return;
    tone(ctx, 440, 0.12, "sine", 0.22, 0);
    tone(ctx, 554, 0.12, "sine", 0.22, 0.15);
    tone(ctx, 659, 0.30, "sine", 0.22, 0.30);
  }, []);

  // Subtle metronome tick played each second of a trial
  const playTick = useCallback((type: "tick" | "beep" | "soft" = "tick") => {
    const ctx = getCtx();
    if (!ctx) return;
    if (type === "beep") tone(ctx, 660, 0.08, "sine", 0.20);
    else if (type === "soft") tone(ctx, 440, 0.10, "sine", 0.14);
    else tone(ctx, 900, 0.025, "sine", 0.05); // tick (default)
  }, []);

  // Escalating countdown beep for the last 5 seconds of a trial
  const playCountdownBeep = useCallback((secondsLeft: number) => {
    const ctx = getCtx();
    if (!ctx) return;
    const clamped = Math.min(Math.max(secondsLeft, 1), 5);
    const freq = 440 + (6 - clamped) * 60; // 500 Hz at 5s up to 740 Hz at 1s
    const gain = clamped <= 2 ? 0.35 : 0.25;
    tone(ctx, freq, 0.1, "sine", gain);
  }, []);

  return { playTrialStart, playCorrect, playIncorrect, playRest, playSessionEnd, playTick, playCountdownBeep };
}
