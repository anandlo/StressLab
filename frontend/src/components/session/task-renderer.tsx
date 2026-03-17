"use client";

import { useState, useEffect, useRef } from "react";
import type { Trial } from "@/lib/types";
import { StimulusType } from "@/lib/types";

/**
 * RuleChangeGate: when a non-empty notice string is provided, shows the
 * notice until the user explicitly clicks "Next" before revealing children.
 */
function RuleChangeGate({
  notice,
  children,
}: {
  notice?: string;
  children: React.ReactNode;
}) {
  const [gated, setGated] = useState(!!notice);

  useEffect(() => {
    if (!notice) { setGated(false); return; }
    setGated(true);
  }, [notice]);

  if (gated && notice) {
    return (
      <div className="flex flex-col items-center justify-center py-10 gap-4">
        <span className="text-xs uppercase tracking-wide font-semibold text-amber-500">Rule Change</span>
        <p className="text-sm text-center max-w-sm font-medium">{notice}</p>
        <button
          className="mt-2 px-4 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          onClick={() => setGated(false)}
        >
          Next
        </button>
      </div>
    );
  }
  return <>{children}</>;
}

/**
 * PVT Counter Display -- countdown variant.
 * After a random wait, a countdown timer starts from countdown_ms toward 0.
 * Pressing spacebar freezes the counter (handled in component). If the
 * countdown reaches 0, the trial is a lapse/failure.
 */
function PVTDisplay({
  waitMs,
  countdownMs,
  waitText,
  windowScale = 1.0,
  onPvtResponse,
}: {
  waitMs: number;
  countdownMs: number;
  waitText?: string;
  windowScale?: number;
  onPvtResponse?: (response: string) => void;
}) {
  const [phase, setPhase] = useState<"wait" | "counter" | "frozen" | "early">("wait");
  const [displayMs, setDisplayMs] = useState(countdownMs);
  const startRef = useRef(0);
  const rafRef = useRef(0);
  const deadlineRef = useRef(countdownMs);

  useEffect(() => {
    setPhase("wait");
    setDisplayMs(countdownMs);
    deadlineRef.current = countdownMs;
    const waitTimer = setTimeout(() => {
      setPhase("counter");
      startRef.current = performance.now();
      const tick = () => {
        const elapsed = performance.now() - startRef.current;
        const remaining = Math.max(0, deadlineRef.current - Math.round(elapsed));
        setDisplayMs(remaining);
        if (remaining > 0) {
          rafRef.current = requestAnimationFrame(tick);
        }
      };
      rafRef.current = requestAnimationFrame(tick);
    }, waitMs);
    return () => {
      clearTimeout(waitTimer);
      cancelAnimationFrame(rafRef.current);
    };
  }, [waitMs, countdownMs]);

  // PVTDisplay owns ALL spacebar handling — block propagation to ResponseInput
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key !== " " && e.code !== "Space") return;
      e.preventDefault();
      e.stopImmediatePropagation();
      if (phase === "counter") {
        cancelAnimationFrame(rafRef.current);
        setPhase("frozen");
        onPvtResponse?.("GO");
      } else if (phase === "wait") {
        setPhase("early");
        onPvtResponse?.("EARLY");
      }
    };
    window.addEventListener("keydown", handler, true); // capture phase
    return () => window.removeEventListener("keydown", handler, true);
  }, [phase, onPvtResponse]);

  if (phase === "early") {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <span className="text-lg font-bold text-red-500 animate-pulse">Too early!</span>
        <span className="text-xs text-muted-foreground">Wait for the countdown to appear before pressing.</span>
      </div>
    );
  }

  if (phase === "wait") {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <div className="flex flex-col items-center gap-2">
          <div className="w-4 h-4 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
          <span className="text-xs text-muted-foreground">
            {waitText ?? "Stare at the dot. Wait..."}
          </span>
        </div>
      </div>
    );
  }

  const pct = countdownMs > 0 ? displayMs / countdownMs : 0;
  const isCritical = pct < 0.3;

  return (
    <div
      className="flex flex-col items-center justify-center py-8 gap-2 transition-all duration-300"
      style={{ transform: `scale(${windowScale})`, transformOrigin: "center" }}
    >
      {/* Dot disappears, counter takes its place */}
      <div className="flex items-center justify-center" style={{ height: "7rem", width: "12rem" }}>
        <span
          className={`font-mono font-bold tabular-nums transition-all duration-75 ${isCritical ? "text-red-600 animate-pulse" : "text-red-500"}`}
          style={{ fontSize: phase === "frozen" ? "2.5rem" : `${Math.max(2, 4.5 * pct + 2)}rem` }}
        >
          {displayMs}
        </span>
      </div>
      <span className="text-xs text-muted-foreground">
        {phase === "frozen" ? "Stopped" : "ms remaining \u2014 press SPACE"}
      </span>
      {/* Shrinking bar */}
      <div className="w-48 h-2 bg-muted rounded-full overflow-hidden mt-1">
        <div
          className={`h-full rounded-full transition-all duration-75 ${isCritical ? "bg-red-500" : "bg-red-400"}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  );
}

/**
 * Stop-Signal display. Shows an arrow, then after SSD ms the arrow turns red
 * and a "STOP!" label appears. On go trials, the arrow stays in primary color.
 */
function StopSignalDisplay({
  arrow,
  ssdMs,
  isStop,
  stopLabel,
  arrowSizeClass,
}: {
  arrow: string;
  ssdMs: number;
  isStop: boolean;
  stopLabel?: string;
  arrowSizeClass?: string;
}) {
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    setStopped(false);
    if (!isStop) return;
    const t = setTimeout(() => setStopped(true), ssdMs);
    return () => clearTimeout(t);
  }, [isStop, ssdMs]);

  return (
    <div className="flex flex-col items-center justify-center py-8 gap-2">
      <span
        className={`${arrowSizeClass ?? "text-6xl"} font-mono font-bold transition-colors duration-100`}
        style={{ color: stopped ? "#ef4444" : "var(--color-primary)" }}
      >
        {arrow}
      </span>
      {stopped && stopLabel && (
        <span className="text-2xl font-bold text-red-500 animate-pulse">
          {stopLabel}
        </span>
      )}
      {!isStop && (
        <span className="text-xs text-muted-foreground mt-1">
          Press the matching arrow key
        </span>
      )}
    </div>
  );
}

/**
 * Sternberg two-phase display.
 * Phase 1: show memory set for study_time_ms (row or matrix layout).
 * Phase 2: hide set, show probe.
 */
function SternbergDisplay({
  setDisplay,
  probe,
  studyTimeMs,
  matrix,
  matrixCols,
}: {
  setDisplay: string;
  probe: number;
  studyTimeMs: number;
  matrix?: number[][] | null;
  matrixCols?: number;
}) {
  const [phase, setPhase] = useState<"study" | "probe">("study");

  useEffect(() => {
    setPhase("study");
    const t = setTimeout(() => setPhase("probe"), studyTimeMs);
    return () => clearTimeout(t);
  }, [studyTimeMs, setDisplay]);

  if (phase === "study") {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-3">
        <span className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">
          Memorize these digits
        </span>
        {matrix && matrix.length > 0 ? (
          <div
            className="inline-grid gap-2"
            style={{ gridTemplateColumns: `repeat(${matrixCols || 3}, 1fr)` }}
          >
            {matrix.flat().map((d, i) => (
              <span key={i} className="text-3xl font-mono font-bold bg-muted rounded-md px-3 py-2 text-center">
                {d}
              </span>
            ))}
          </div>
        ) : (
          <div className="flex gap-3">
            {setDisplay.split("  ").map((d, i) => (
              <span key={i} className="text-3xl font-mono font-bold bg-muted rounded-md px-3 py-2">
                {d}
              </span>
            ))}
          </div>
        )}
        <span className="text-xs text-muted-foreground">
          A probe digit will appear shortly...
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-8 gap-3">
      <span className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">
        Was this digit in the set?
      </span>
      <span className="text-7xl font-mono font-bold text-primary">{probe}</span>
    </div>
  );
}

/**
 * Digit Span display: shows digits for display_time_ms, then hides them.
 */
function DigitSpanDisplay({
  digits,
  direction,
  displayTimeMs,
}: {
  digits: number[];
  direction: string;
  displayTimeMs: number;
}) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    const t = setTimeout(() => setVisible(false), displayTimeMs);
    return () => clearTimeout(t);
  }, [displayTimeMs, digits]);

  if (visible) {
    return (
      <div className="flex flex-col items-center justify-center py-8 gap-3">
        <span className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">
          Memorize
        </span>
        <div className="flex gap-2">
          {digits.map((d, i) => (
            <span key={i} className="text-3xl font-mono font-bold bg-muted rounded-md px-3 py-2">
              {d}
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-8 gap-3">
      <span className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">
        Recall
      </span>
      <span className="text-lg font-medium">
        Type the digits {direction === "BACKWARDS" ? "in reverse order" : "in the same order"}
      </span>
    </div>
  );
}

function TaskRendererInner({ trial, onPvtResponse }: { trial: Trial; onPvtResponse?: (r: string) => void }) {
  const s = trial.stimulus;

  switch (trial.stimulus_type) {
    case StimulusType.STROOP: {
      const fontFamily = (s.font_family as string) ?? undefined;
      const borderColor = (s.border_color as string) ?? undefined;
      const bgColor = (s.bg_color as string) ?? undefined;
      const fontSize = (s.font_size as string) ?? undefined;
      const letterSpacing = (s.letter_spacing as string) ?? undefined;
      const overflowSafe = s.overflow_safe === true;
      // Cap font size for fonts that tend to overflow (cursive/fantasy)
      const safeFontSize = overflowSafe
        ? (fontSize ? `min(${fontSize}, 2.8rem)` : "2.5rem")
        : (fontSize ?? "3rem");
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <div
            className="inline-flex items-center justify-center rounded-lg px-6 py-3 overflow-hidden"
            style={{
              ...(borderColor ? { border: `5px solid ${borderColor}` } : {}),
              ...(bgColor ? { backgroundColor: bgColor } : {}),
              maxWidth: "90vw",
            }}
          >
            <span
              className="font-bold"
              style={{
                color: s.ink_color as string,
                fontFamily: fontFamily,
                fontSize: safeFontSize,
                letterSpacing: letterSpacing,
                wordBreak: "break-word" as const,
                overflowWrap: "break-word" as const,
              }}
            >
              {s.word as string}
            </span>
          </div>
          {s.distractor ? (
            <span className="text-sm font-medium text-muted-foreground/70">
              {s.distractor as string}
            </span>
          ) : null}
        </div>
      );
    }

    case StimulusType.ARROWS: {
      const yOff = (s.y_offset_vh as number) ?? 0;
      const xOff = (s.x_offset_vw as number) ?? 0;
      const arrowSizeClass = (s.arrow_size as string) ?? "text-5xl";
      // Stop-Signal task: delayed color change from primary to red
      if (s.stop_signal === true) {
        const arrow = (s.display as string) ?? (s.arrow as string) ?? "";
        const ssArrowSize = (s.arrow_size as string) ?? "text-5xl";
        return (
          <StopSignalDisplay
            arrow={arrow}
            ssdMs={(s.stop_signal_delay_ms as number) ?? 250}
            isStop={(s.is_stop_trial as boolean) ?? (s.is_stop as boolean) ?? false}
            stopLabel={(s.stop_label as string) ?? "STOP!"}
            arrowSizeClass={ssArrowSize}
          />
        );
      }
      // Flanker: pre-formatted arrow string
      const arrowDisplay =
        (s.display as string | undefined) ??
        (s.arrows as string[] | undefined)?.join("") ??
        (s.arrow as string | undefined) ??
        "";
      const tight = s.tight_spacing === true;
      const perChar = s.per_char_render === true;
      const arrowsArray = (s.arrows_array as string[] | undefined) ?? [];
      const charRots = (s.char_rotations as number[] | undefined) ?? [];
      const charSizes = (s.char_sizes as string[] | undefined) ?? [];

      // Per-character rendering for Flanker at high difficulty
      if (perChar && arrowsArray.length > 0) {
        return (
          <div
            className="flex items-center justify-center py-8 overflow-hidden"
            style={{
              transform: `translate(clamp(-10vw, ${xOff}vw, 10vw), clamp(-6vh, ${yOff}vh, 6vh))`,
              maxWidth: "100%",
            }}
          >
            <div className="flex items-center" style={{ gap: "1px" }}>
              {arrowsArray.map((ch, i) => (
                <span
                  key={i}
                  className={`${charSizes[i] || arrowSizeClass} font-mono font-bold text-primary inline-block`}
                  style={{
                    transform: charRots[i] ? `rotate(${charRots[i]}deg)` : undefined,
                    lineHeight: 1,
                  }}
                >
                  {ch}
                </span>
              ))}
            </div>
          </div>
        );
      }

      return (
        <div
          className="flex items-center justify-center py-8 overflow-hidden"
          style={{
            transform: `translate(clamp(-10vw, ${xOff}vw, 10vw), clamp(-6vh, ${yOff}vh, 6vh))`,
            maxWidth: "100%",
          }}
        >
          <span
            className={`${arrowSizeClass} font-mono font-bold text-primary ${
              tight ? "" : "tracking-widest"
            }`}
            style={tight ? { letterSpacing: "-0.02em" } : undefined}
          >
            {arrowDisplay}
          </span>
        </div>
      );
    }

    case StimulusType.SHAPE: {
      // Simon Task carries a `position` field ("left" / "right") that must be honoured
      const position = s.position as string | undefined;
      const bgColor =
        (s.color_hex as string | undefined) ??
        (s.color as string | undefined) ??
        "#3b82f6";
      const shapeSize = (s.size as number) ?? 64;
      const ruleNotice = s.rule_change_notice as string | undefined;
      return (
        <RuleChangeGate notice={ruleNotice}>
        <div
          className={`flex items-center py-8 ${
            position === "left"
              ? "justify-start pl-16"
              : position === "right"
              ? "justify-end pr-16"
              : "justify-center"
          }`}
        >
          {s.shape === "triangle" ? (
            <div className="flex flex-col items-center justify-center">
              <div
                style={{
                  width: 0,
                  height: 0,
                  borderLeft: `${shapeSize / 2}px solid transparent`,
                  borderRight: `${shapeSize / 2}px solid transparent`,
                  borderBottom: `${shapeSize}px solid ${bgColor}`,
                }}
              />
              {s.label ? (
                <span className="text-white text-sm font-bold -mt-10">
                  {s.label as string}
                </span>
              ) : null}
            </div>
          ) : (
            <div
              className={`flex items-center justify-center text-white text-lg font-bold ${
                s.shape === "circle"
                  ? "rounded-full"
                  : s.shape === "diamond"
                  ? "rotate-45"
                  : ""
              }`}
              style={{ backgroundColor: bgColor, width: shapeSize, height: shapeSize }}
            >
              {s.label as string}
            </div>
          )}
        </div>
        </RuleChangeGate>
      );
    }

    case StimulusType.SEQUENCE: {
      // Digit Span: show digits for display_time_ms, then hide and prompt recall
      if (s.digit_span === true && s.display_time_ms) {
        return (
          <DigitSpanDisplay
            digits={(s.digits as number[]) ?? []}
            direction={(s.direction as string) ?? "FORWARDS"}
            displayTimeMs={s.display_time_ms as number}
          />
        );
      }
      return (
        <div className="flex items-center justify-center py-8 gap-3 flex-wrap">
          {((s.sequence ?? s.digits) as (string | number)[])?.map((item, i) => (
            <span
              key={i}
              className="text-2xl font-mono bg-muted rounded-md px-3 py-2"
            >
              {item}
            </span>
          ))}
          {s.missing !== undefined && (
            <span className="text-2xl font-mono bg-primary/20 text-primary rounded-md px-3 py-2">
              ?
            </span>
          )}
          {s.direction !== undefined && (
            <div className="w-full text-center mt-2">
              <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground bg-muted/50 rounded px-2 py-0.5">
                {s.direction === "FORWARDS" ? "recall in order" : "recall in reverse"}
              </span>
            </div>
          )}
        </div>
      );
    }

    case StimulusType.CARDS: {
      // WCST: target is a single card dict {shape, color, color_hex, count}
      //       choices is an array of 4 card dicts
      const wcstTarget = s.target as Record<string, unknown> | undefined;
      const wcstChoices = s.choices as Record<string, unknown>[] | undefined;

      function renderWCSTCard(card: Record<string, unknown>, index?: number) {
        const SHAPE_CHAR: Record<string, string> = {
          circle: "●", triangle: "▲", square: "■", star: "★",
        };
        const sym = SHAPE_CHAR[card.shape as string] ?? "?";
        const count = (card.count as number) ?? 1;
        const hex = (card.color_hex as string) ?? "#888";
        return (
          <div
            key={index}
            className="flex flex-col items-center gap-1 rounded-lg border-2 px-3 py-2 min-w-[56px]"
            style={{ borderColor: hex }}
          >
            {index !== undefined && (
              <span className="text-[10px] font-bold text-muted-foreground">{index + 1}</span>
            )}
            <div className="flex gap-0.5">
              {Array.from({ length: count }).map((_, i) => (
                <span key={i} className="text-xl leading-none" style={{ color: hex }}>
                  {sym}
                </span>
              ))}
            </div>
          </div>
        );
      }

      if (wcstTarget && wcstChoices) {
        return (
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Target card
            </div>
            {renderWCSTCard(wcstTarget)}
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mt-2">
              Which card matches? (press 1-4)
            </div>
            <div className="flex gap-3">
              {wcstChoices.map((card, i) => renderWCSTCard(card, i))}
            </div>
          </div>
        );
      }
      // Legacy / fallback
      return (
        <div className="flex flex-col items-center py-4 gap-2">
          <div className="text-sm text-muted-foreground">Target:</div>
          <div className="text-lg font-mono">{JSON.stringify(wcstTarget)}</div>
        </div>
      );
    }

    case StimulusType.GRID: {
      // Tower of London: has `initial`, `goal`, `peg_labels`
      if (s.initial && s.goal) {
        const BALL_COLOR: Record<string, string> = {
          R: "#ef4444", G: "#22c55e", B: "#3b82f6",
          Y: "#eab308", P: "#a855f7",
        };
        const pegLabels = (s.peg_labels as string[]) ?? ["A", "B", "C"];

        function renderPegs(pegs: string[][]) {
          return (
            <div className="flex gap-4 items-end">
              {pegs.map((peg, pi) => (
                <div key={pi} className="flex flex-col items-center gap-1">
                  <div className="flex flex-col-reverse gap-1 min-h-[88px] justify-start">
                    {peg.length === 0 ? (
                      <div className="w-8 h-8 rounded-full border-2 border-dashed border-muted-foreground/30" />
                    ) : (
                      peg.map((ball, bi) => (
                        <div
                          key={bi}
                          className="w-8 h-8 rounded-full border border-black/10 shadow-sm"
                          style={{ backgroundColor: BALL_COLOR[ball] ?? "#888" }}
                        />
                      ))
                    )}
                  </div>
                  <div className="w-full h-1 bg-foreground/20 rounded" />
                  <span className="text-xs font-bold text-muted-foreground">
                    {pegLabels[pi]}
                  </span>
                </div>
              ))}
            </div>
          );
        }

        return (
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="flex items-start gap-10">
              <div className="flex flex-col items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Current
                </span>
                {renderPegs(s.initial as string[][])}
              </div>
              <span className="text-2xl text-muted-foreground/40 mt-10">→</span>
              <div className="flex flex-col items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Goal
                </span>
                {renderPegs(s.goal as string[][])}
              </div>
            </div>
          </div>
        );
      }

      // Visual Search: has `grid`, `target`, `size`
      const gridSize = (s.size as number) ?? 3;
      const gridTarget = s.target as string | undefined;
      return (
        <div className="flex flex-col items-center gap-4 py-4">
          {gridTarget && (
            <div className="flex items-center gap-3 rounded-lg border px-5 py-2 bg-muted/50">
              <span className="text-sm text-muted-foreground">Find:</span>
              <span className="text-3xl font-bold text-primary">{gridTarget}</span>
            </div>
          )}
          <div
            className="gap-2"
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${gridSize}, minmax(0, 1fr))`,
            }}
          >
            {(() => {
              const flatGrid = (s.grid as (string | number)[][])?.flat() ?? [];
              const flatRots = (s.rotations as number[][] | undefined)?.flat() ?? [];
              const flatColors = (s.colors as (string | null)[][] | undefined)?.flat() ?? [];
              return flatGrid.map((cell, i) => (
                <div
                  key={i}
                  className="w-12 h-12 rounded-md border flex items-center justify-center text-xl bg-muted select-none"
                  style={flatColors[i] ? { color: flatColors[i] as string } : {}}
                >
                  <span
                    style={flatRots[i] ? { display: "inline-block", transform: `rotate(${flatRots[i]}deg)` } : {}}
                  >
                    {cell}
                  </span>
                </div>
              ));
            })()}
          </div>
        </div>
      );
    }

    case StimulusType.TIMER_ONLY:
      return (
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <div className="text-xl font-medium">
            {s.title as string}
          </div>
          {s.instructions ? (
            <p className="text-sm text-muted-foreground text-center max-w-md">
              {s.instructions as string}
            </p>
          ) : null}
        </div>
      );

    case StimulusType.LETTER_STREAM: {
      const cptGrid = s.grid as string[][] | undefined;
      const ctxHint = s.context_hint as string | undefined;
      const cptFontSize = (s.font_size as string) ?? "6rem";
      const cptRuleNotice = s.rule_change_notice as string | undefined;
      if (cptGrid && cptGrid.length > 0) {
        // Grid mode: letter embedded among distractors
        return (
          <RuleChangeGate notice={cptRuleNotice}>
          <div className="flex flex-col items-center justify-center py-6 gap-3">
            <div className="text-xs text-muted-foreground">
              Find '{s.target as string}' and press SPACE
            </div>
            <div className="inline-grid gap-1" style={{gridTemplateColumns: `repeat(${cptGrid[0].length}, 1fr)`}}>
              {cptGrid.flat().map((ch, i) => (
                <span
                  key={i}
                  className="flex items-center justify-center font-mono font-bold border border-border rounded bg-muted/50"
                  style={{ fontSize: cptFontSize, width: "2.5em", height: "2.5em" }}
                >
                  {ch}
                </span>
              ))}
            </div>
          </div>
          </RuleChangeGate>
        );
      }
      return (
        <RuleChangeGate notice={cptRuleNotice}>
        <div className="flex flex-col items-center justify-center py-8 gap-2">
          <span className="font-mono font-bold text-primary" style={{ fontSize: cptFontSize }}>
            {s.letter as string}
          </span>
          {ctxHint && <div className="text-xs text-muted-foreground mt-1">{ctxHint}</div>}
        </div>
        </RuleChangeGate>
      );
    }

    case StimulusType.DUAL:
      // Operation span (encode phase): math equation + letter to remember
      if (s.ospan === true && s.phase === "encode") {
        return (
          <div className="flex flex-col items-center justify-center py-6 gap-5">
            <div className="text-lg font-mono bg-muted rounded-md px-4 py-2">
              {s.math as string}
            </div>
            <div className="text-xs text-muted-foreground">
              Is this equation correct? Type YES or NO.
            </div>
            <div className="flex flex-col items-center gap-1 border-2 border-primary/30 rounded-lg px-6 py-3 bg-primary/5">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">Remember this letter</span>
              <span className="text-4xl font-bold text-primary">{s.letter as string}</span>
              <span className="text-[10px] text-muted-foreground">Letter {s.position as number} of {s.set_size as number}</span>
            </div>
          </div>
        );
      }
      // Operation span (recall phase): prompt to type all letters
      if (s.ospan === true && s.phase === "recall") {
        return (
          <div className="flex flex-col items-center justify-center py-8 gap-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">Recall</div>
            <p className="text-lg font-medium text-center">
              Type all {s.set_size as number} letters you saw, in order
            </p>
            <p className="text-xs text-muted-foreground">No spaces. Example: BFKM</p>
          </div>
        );
      }
      // Default dual display (e.g. DualTask, MIST)
      return (
        <div className="flex flex-col items-center justify-center py-6 gap-4">
          {s.math ? (
            <div className="text-lg font-mono bg-muted rounded-md px-4 py-2">
              {s.math as string}
            </div>
          ) : null}
          {s.math_question ? (
            <div className="text-lg font-mono bg-muted rounded-md px-4 py-2">
              {s.math_question as string}
            </div>
          ) : null}
          {s.letter && !s.ospan ? (
            <div className="text-sm text-muted-foreground">
              Letter: <span className="font-mono font-bold text-foreground">{s.letter as string}</span>
            </div>
          ) : null}
          {s.letter_display ? (
            <div className="text-sm text-muted-foreground">
              Letters: <span className="font-mono font-bold text-foreground tracking-wider">{s.letter_display as string}</span>
            </div>
          ) : null}
          {s.comparison ? (
            <div className="w-full max-w-xs space-y-2 mt-2">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>You: {(s.comparison as Record<string, unknown>).user_pct as number}%</span>
                <span>Avg: {(s.comparison as Record<string, unknown>).avg_participant_pct as number}%</span>
              </div>
              <div className="relative h-3 rounded-full bg-muted overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-red-500/70"
                  style={{ width: `${(s.comparison as Record<string, unknown>).user_pct as number}%` }}
                />
                <div
                  className="absolute inset-y-0 left-0 rounded-full border-r-2 border-green-500"
                  style={{ width: `${(s.comparison as Record<string, unknown>).avg_participant_pct as number}%` }}
                />
              </div>
              {(s.comparison as Record<string, unknown>).stress_message ? (
                <p className="text-xs text-red-500 font-medium text-center animate-pulse">
                  {(s.comparison as Record<string, unknown>).stress_message as string}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      );

    case StimulusType.TEXT:
    default: {
      // PVT: counter-based (new) or legacy text-based
      const pvtWaitMs = s.wait_ms as number | undefined;
      if (pvtWaitMs !== undefined && (s.pvt_counter === true || s.stimulus_text !== undefined)) {
        return (
          <PVTDisplay
            waitMs={pvtWaitMs}
            countdownMs={(s.countdown_ms as number) ?? 700}
            waitText={s.instruction_during_wait as string | undefined}
            windowScale={(s.window_scale as number) ?? 1.0}
            onPvtResponse={onPvtResponse}
          />
        );
      }
      // Sternberg: two-phase study-then-probe
      if (s.sternberg === true) {
        return (
          <SternbergDisplay
            setDisplay={(s.set_display as string) ?? ""}
            probe={(s.probe as number) ?? 0}
            studyTimeMs={(s.study_time_ms as number) ?? 2000}
            matrix={s.matrix as number[][] | null | undefined}
            matrixCols={(s.matrix_cols as number) ?? 3}
          />
        );
      }
      // PASAT: show only the current number -- participant must remember the previous one
      const pasatCurr = s.current as number | undefined;
      if (s.pasat === true && pasatCurr !== undefined) {
        const isFirst = s.is_first === true;
        return (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <span className="text-8xl font-mono font-bold text-primary">{pasatCurr}</span>
            <span className="text-xs text-muted-foreground">
              {isFirst
                ? "This is the first number. Type it to confirm, then the next trial will ask you to add."
                : "Add this to the previous number"}
            </span>
          </div>
        );
      }
      // N-Back: show ONLY the current number. The participant must remember the one from N steps back.
      if (s.n_back === true) {
        const nbackN = s.n as number;
        const nbackCurrent = s.current as number;
        // Intro trials (first N presentations): just show the number, no match question
        if (s.is_intro === true) {
          return (
            <div className="flex flex-col items-center justify-center py-8 gap-4">
              <span className="text-8xl font-mono font-bold text-primary">{nbackCurrent}</span>
              <span className="text-sm text-muted-foreground">
                Remember this number.
              </span>
            </div>
          );
        }
        return (
          <div className="flex flex-col items-center justify-center py-8 gap-4">
            <span className="text-8xl font-mono font-bold text-primary">{nbackCurrent}</span>
            <span className="text-xs text-muted-foreground">
              Does this match the number from {nbackN} step{nbackN > 1 ? "s" : ""} ago?
            </span>
          </div>
        );
      }
      // Legacy n-back fallback (old data format with comparator)
      const nbackCurrent = s.current as number | undefined;
      const nbackComparator = s.comparator as number | undefined;
      const nbackN = s.n as number | undefined;
      if (nbackCurrent !== undefined && nbackComparator !== undefined && !s.n_back) {
        return (
          <div className="flex items-center justify-center py-6 gap-8">
            <div className="flex flex-col items-center gap-1">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">{nbackN}-back</span>
              <span className="text-5xl font-mono font-bold text-muted-foreground">{nbackComparator}</span>
            </div>
            <div className="text-2xl text-muted-foreground/40">→</div>
            <div className="flex flex-col items-center gap-1">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">now</span>
              <span className="text-5xl font-mono font-bold text-primary">{nbackCurrent}</span>
            </div>
          </div>
        );
      }
      // Task Switching: show the number large with the rule cue above
      if (s.task_switching === true && s.cue) {
        return (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <span className="text-sm font-semibold uppercase tracking-wide text-muted-foreground bg-muted rounded-md px-3 py-1">
              {s.cue as string}
            </span>
            <span className="text-7xl font-mono font-bold text-primary">
              {s.number as number}
            </span>
          </div>
        );
      }
      // Rapid Comparison: show two sets side by side
      if (s.rapid_comparison === true && s.display_a) {
        return (
          <div className="flex flex-col items-center justify-center py-6 gap-4">
            <div className="flex items-center gap-8">
              <div className="flex flex-col items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Set A</span>
                <span className="text-xl font-mono font-bold bg-muted rounded-md px-4 py-2">{s.display_a as string}</span>
              </div>
              <span className="text-2xl text-muted-foreground/40">vs</span>
              <div className="flex flex-col items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Set B</span>
                <span className="text-xl font-mono font-bold bg-muted rounded-md px-4 py-2">{s.display_b as string}</span>
              </div>
            </div>
            <span className="text-xs text-muted-foreground">Which set has the larger total? Press A or B.</span>
          </div>
        );
      }
      const display = s.display as string | undefined;
      const question = s.question as string | undefined;
      const text = s.text as string | undefined;
      const prompt = s.prompt as string | undefined;
      return (
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            {display ? (
              <div className="text-2xl font-mono font-bold">{display}</div>
            ) : question ? (
              <div className="text-2xl font-mono font-bold">{question}</div>
            ) : text ? (
              <div className="text-2xl font-mono font-bold">{text}</div>
            ) : prompt ? (
              <div className="text-xl">{prompt}</div>
            ) : (
              <div className="text-xl font-mono">{JSON.stringify(s)}</div>
            )}
          </div>
        </div>
      );
    }
  }
}

/**
 * Global wrapper: SHAPE and LETTER_STREAM render their own internal RuleChangeGate.
 * All other stimulus types use this outer gate so rule_change_notice is always shown.
 */
export function TaskRenderer({ trial, onPvtResponse }: { trial: Trial; onPvtResponse?: (r: string) => void }) {
  const s = trial.stimulus;
  const usesInternalGate =
    trial.stimulus_type === StimulusType.SHAPE ||
    trial.stimulus_type === StimulusType.LETTER_STREAM;
  const topNotice = usesInternalGate
    ? undefined
    : (s.rule_change_notice as string | undefined);
  return (
    <RuleChangeGate notice={topNotice}>
      <TaskRendererInner trial={trial} onPvtResponse={onPvtResponse} />
    </RuleChangeGate>
  );
}
