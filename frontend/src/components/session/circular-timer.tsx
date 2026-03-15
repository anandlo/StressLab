"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";

interface CircularTimerProps {
  durationSec: number;
  onTimeout: () => void;
  running: boolean;
  size?: number;
  onSecondTick?: (secondsLeft: number) => void;
}

export function CircularTimer({
  durationSec,
  onTimeout,
  running,
  size = 80,
  onSecondTick,
}: CircularTimerProps) {
  const [remaining, setRemaining] = useState(durationSec);
  const startTimeRef = useRef<number>(0);
  const rafRef = useRef<number>(0);
  const calledTimeoutRef = useRef(false);
  const lastTickSecRef = useRef<number>(Number.MAX_SAFE_INTEGER);

  const onSecondTickRef = useRef(onSecondTick);
  useEffect(() => {
    onSecondTickRef.current = onSecondTick;
  });

  const stableOnSecondTick = useCallback(
    (s: number) => onSecondTickRef.current?.(s),
    []
  );

  useEffect(() => {
    setRemaining(durationSec);
    calledTimeoutRef.current = false;
    lastTickSecRef.current = Number.MAX_SAFE_INTEGER;
    if (!running) return;

    startTimeRef.current = performance.now();

    function tick() {
      const elapsed = (performance.now() - startTimeRef.current) / 1000;
      const left = Math.max(0, durationSec - elapsed);
      setRemaining(left);

      // Fire onSecondTick once per integer-second boundary
      const s = Math.ceil(left);
      if (s > 0 && s < lastTickSecRef.current) {
        lastTickSecRef.current = s;
        stableOnSecondTick(s);
      }

      if (left <= 0 && !calledTimeoutRef.current) {
        calledTimeoutRef.current = true;
        onTimeout();
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [durationSec, running, onTimeout, stableOnSecondTick]);

  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const fraction = remaining / durationSec;
  const offset = circumference * (1 - fraction);

  const urgentThreshold = durationSec * 0.25;
  const warningThreshold = durationSec * 0.5;

  let strokeColor = "var(--color-primary)";
  if (remaining < urgentThreshold) strokeColor = "var(--color-destructive)";
  else if (remaining < warningThreshold) strokeColor = "oklch(0.75 0.18 55)";

  const fontSize = size >= 100 ? "text-xl" : size >= 64 ? "text-base" : "text-sm";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-muted)"
          strokeWidth={size >= 100 ? 6 : 4}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={size >= 100 ? 6 : 4}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          initial={false}
        />
      </svg>
      <span className={`absolute ${fontSize} font-mono font-bold tabular-nums`}>
        {remaining >= 10
          ? Math.ceil(remaining)
          : remaining.toFixed(1)}
      </span>
    </div>
  );
}
