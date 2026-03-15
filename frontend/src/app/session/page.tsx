"use client";

import { useState, useCallback, useRef, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Square, AlertCircle, Volume2, VolumeX } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSessionWS } from "@/hooks/use-session";
import { useSound } from "@/hooks/use-sound";
import { TaskRenderer } from "@/components/session/task-renderer";
import { ResponseInput } from "@/components/session/response-input";
import { CircularTimer } from "@/components/session/circular-timer";
import { ScoreBoard } from "@/components/session/score-board";
import { RestScreen } from "@/components/session/rest-screen";
import { FeedbackBanner } from "@/components/session/feedback-banner";
import { SessionState, type SessionConfig, type SoundType } from "@/lib/types";

function SessionContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const configStr = searchParams.get("config");

  const {
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
    restComplete,
    stop,
  } = useSessionWS();

  const { playTrialStart, playCorrect, playIncorrect, playRest, playSessionEnd, playTick, playCountdownBeep } = useSound();
  const trialStartRef = useRef<number>(0);
  const [started, setStarted] = useState(false);
  const [inputReady, setInputReady] = useState(false);
  const [sessionConfig, setSessionConfig] = useState<SessionConfig | null>(null);
  const [soundClicks, setSoundClicks] = useState(true);
  const [soundCountdown, setSoundCountdown] = useState(true);
  const [soundType, setSoundType] = useState<SoundType>("tick");

  useEffect(() => {
    if (trial) {
      trialStartRef.current = performance.now();
      playTrialStart();
      setInputReady(false);
      // For keyboard/spacebar tasks (reaction-time sensitive), use a very
      // short delay to prevent accidental carry-over from the previous trial.
      // For text input, allow more time to read the stimulus.
      const isRT = trial.input_mode === "keyboard" || trial.input_mode === "spacebar";
      // For PVT trials, the counter runs for wait_ms before the stimulus
      // appears. Block input until after that delay so the spacebar press
      // is a genuine reaction and not a carry-over keystroke.
      const stim = trial.stimulus as Record<string, unknown>;
      const isPVT = stim?.pvt_counter === true;
      const isDigitSpan = stim?.digit_span === true;
      const isSternberg = stim?.study_time_ms !== undefined;
      // PVT: spacebar handled entirely by PVTDisplay; keep ResponseInput disabled
      const readyDelay = isPVT
        ? 999999
        : isDigitSpan
        ? ((stim?.display_time_ms as number) ?? 3000) + 200
        : isSternberg
        ? ((stim?.study_time_ms as number) ?? 2000) + 200
        : isRT ? 150 : 800;
      const t = setTimeout(() => setInputReady(true), readyDelay);
      return () => clearTimeout(t);
    }
  }, [trial?.trial_id, playTrialStart]);

  useEffect(() => {
    if (!lastResult) return;
    if (lastResult.is_correct) playCorrect();
    else playIncorrect();
  }, [lastResult, playCorrect, playIncorrect]);

  const prevStateRef = useRef<SessionState>(SessionState.IDLE);
  useEffect(() => {
    if (state === SessionState.REST && prevStateRef.current !== SessionState.REST) playRest();
    if (state === SessionState.COMPLETE && prevStateRef.current !== SessionState.COMPLETE) playSessionEnd();
    prevStateRef.current = state;
  }, [state, playRest, playSessionEnd]);

  useEffect(() => {
    if (!configStr) return;
    if (!started) {
      try {
        const config: SessionConfig = JSON.parse(
          decodeURIComponent(configStr)
        );
        setStarted(true);
        setSessionConfig(config);
        setSoundClicks(config.sound_clicks_enabled !== false);
        setSoundCountdown(config.sound_countdown_enabled !== false);
        setSoundType(config.sound_type ?? "tick");
        start(config);
      } catch {
        // Invalid config -- error will show below
      }
    }
  }, [configStr, started, start]);

  const handleResponse = useCallback(
    (response: string) => {
      const rt = performance.now() - trialStartRef.current;
      submitResponse(response, rt, false);
    },
    [submitResponse]
  );

  const handleTimeout = useCallback(() => {
    submitResponse("", 0, true);
  }, [submitResponse]);

  if (error) {
    return (
      <div className="max-w-lg mx-auto py-16">
        <Card>
          <CardContent className="py-8 text-center space-y-4">
            <AlertCircle className="h-10 w-10 text-destructive mx-auto" />
            <p className="text-destructive font-medium">{error}</p>
            <Button variant="outline" onClick={() => router.push("/protocol")}>
              Back to Protocol
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (state === SessionState.COMPLETE && summary) {
    const encoded = encodeURIComponent(JSON.stringify(summary));
    const sf = sessionFile ? `&session=${encodeURIComponent(sessionFile)}` : "";
    router.push(`/results?summary=${encoded}${sf}`);
    return null;
  }

  if (state === SessionState.REST && restInfo) {
    return (
      <div className="max-w-lg mx-auto">
        <RestScreen
          durationSec={restInfo.duration_sec}
          block={restInfo.block}
          totalBlocks={restInfo.total_blocks}
          onComplete={restComplete}
        />
      </div>
    );
  }

  if (!configStr) {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Session</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Timed cognitive assessment with adaptive difficulty
          </p>
        </div>
        <Card>
          <CardContent className="py-8 space-y-5">
            <div className="space-y-3 text-sm text-muted-foreground">
              <p>
                A session presents a sequence of cognitive paradigms under time
                pressure. Difficulty adapts automatically based on your
                performance. Results are saved and can be reviewed in the
                Results tab.
              </p>
              <ul className="list-disc list-inside space-y-1 pl-1">
                <li>Select paradigms and intensity on the Protocol page</li>
                <li>Optionally run a practice round first to get familiar</li>
                <li>Each paradigm has a per-trial time limit that scales with difficulty</li>
              </ul>
            </div>
            <Button onClick={() => router.push("/protocol")}>
              Configure a session in Protocol
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (state === SessionState.IDLE || !trial) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        {state === SessionState.IDLE ? "Connecting to session..." : "Starting session..."}
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <Badge variant="secondary" className="text-sm px-3 py-1">{trial.paradigm_label}</Badge>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-xs tabular-nums">Trial {trialCount}</Badge>
          <Popover>
            <PopoverTrigger render={
              <Button variant="ghost" size="sm">
                {soundType === "none" ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
              </Button>
            } />
            <PopoverContent side="bottom" align="end" className="w-56 space-y-3 p-3">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Sound</div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={soundClicks}
                  onChange={(e) => setSoundClicks(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
                <span className="text-sm">Per-second click</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={soundCountdown}
                  onChange={(e) => setSoundCountdown(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
                <span className="text-sm">Countdown beep (last 5 s)</span>
              </label>
              {soundClicks && (
                <Select value={soundType} onValueChange={(v) => setSoundType(v as SoundType)}>
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tick">Tick</SelectItem>
                    <SelectItem value="beep">Beep</SelectItem>
                    <SelectItem value="soft">Soft tone</SelectItem>
                    <SelectItem value="none">Off</SelectItem>
                  </SelectContent>
                </Select>
              )}
            </PopoverContent>
          </Popover>
          <Button
            variant="ghost"
            size="sm"
            onClick={stop}
            className="text-destructive hover:text-destructive"
          >
            <Square className="h-4 w-4 mr-1" />
            Stop
          </Button>
        </div>
      </div>

      {score && <ScoreBoard score={score} />}

      <FeedbackBanner message={feedback} />

      <AnimatePresence mode="wait">
        <motion.div
          key={trial.trial_id}
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.15 }}
        >
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base text-muted-foreground">
                  {trial.instruction}
                </CardTitle>
                <CircularTimer
                  durationSec={trial.time_limit_sec}
                  onTimeout={handleTimeout}
                  running={!lastResult}
                  size={72}
                  onSecondTick={(s) => {
                    if (soundType === "none") return;
                    if (soundCountdown && s <= 5) playCountdownBeep(s);
                    else if (soundClicks) playTick(soundType);
                  }}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <TaskRenderer trial={trial} onPvtResponse={handleResponse} />

              {lastResult ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className={`text-center py-2 rounded-md text-sm font-medium ${
                    lastResult.is_correct
                      ? "bg-green-500/10 text-green-600 dark:text-green-400"
                      : "bg-red-500/10 text-red-600 dark:text-red-400"
                  }`}
                >
                  {lastResult.is_correct
                    ? "Correct"
                    : lastResult.timed_out
                    ? "Time's up"
                    : `Incorrect (answer: ${trial.correct_answer})`}
                </motion.div>
              ) : (
                // Hide input entirely during memorization phases (digit span, sternberg)
                !inputReady && ((trial.stimulus as Record<string, unknown>).digit_span || (trial.stimulus as Record<string, unknown>).study_time_ms) ? null : (
                <ResponseInput
                  trial={trial}
                  onSubmit={handleResponse}
                  disabled={!inputReady || !!lastResult}
                />
                )
              )}
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      <div className="text-center">
        <Badge variant="outline" className="text-xs">
          Difficulty: {trial.difficulty}
        </Badge>
      </div>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-muted-foreground">Loading...</div>}>
      <SessionContent />
    </Suspense>
  );
}
