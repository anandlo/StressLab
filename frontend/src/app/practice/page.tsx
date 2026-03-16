"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, CheckCircle2, XCircle, SkipForward } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { generatePracticeTrials } from "@/lib/api";
import type { Trial, SessionConfig } from "@/lib/types";
import { TaskRenderer } from "@/components/session/task-renderer";
import { ResponseInput } from "@/components/session/response-input";

function PracticeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const configStr = searchParams.get("config");

  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [trials, setTrials] = useState<Trial[]>([]);
  const [current, setCurrent] = useState(0);
  const [response, setResponse] = useState<string | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!configStr) {
      setLoading(false);
      return;
    }
    try {
      const parsed: SessionConfig = JSON.parse(decodeURIComponent(configStr));
      setConfig(parsed);
      generatePracticeTrials(parsed.paradigm_ids).then((t) => {
        setTrials(t);
        setLoading(false);
      });
    } catch {
      setLoading(false);
    }
  }, [configStr]);

  const handleResponse = useCallback(
    (resp: string) => {
      setResponse(resp);
      setShowFeedback(true);
    },
    []
  );

  function nextTrial() {
    setResponse(null);
    setShowFeedback(false);
    if (current < trials.length - 1) {
      setCurrent((c) => c + 1);
    } else {
      goToSession();
    }
  }

  function goToSession() {
    if (configStr) {
      router.push(`/session?config=${configStr}`);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-muted-foreground">
        Loading practice trials...
      </div>
    );
  }

  if (!config || trials.length === 0) {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Practice</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Untimed familiarisation with each paradigm
          </p>
        </div>
        <div className="rounded-lg border bg-card px-6 py-8 space-y-5">
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>
              Practice mode lets you try all selected paradigms at an easy
              difficulty with no time pressure. Immediate feedback is shown
              after each response so you can learn the task rules before the
              real session begins.
            </p>
            <ul className="list-disc list-inside space-y-1 pl-1">
              <li>No scores are recorded during practice</li>
              <li>You may skip straight to the session at any time</li>
              <li>Each paradigm receives one or two warm-up trials</li>
            </ul>
          </div>
          <Button onClick={() => router.push("/protocol")}>
            Configure a session in Protocol
          </Button>
        </div>
      </div>
    );
  }

  const trial = trials[current];
  const isCorrect =
    response !== null &&
    response.toLowerCase().trim() ===
      trial.correct_answer.toLowerCase().trim();
  const progress = ((current + (showFeedback ? 1 : 0)) / trials.length) * 100;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Practice</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Untimed familiarization with each paradigm
          </p>
        </div>
        <Button variant="outline" onClick={goToSession}>
          <SkipForward className="mr-2 h-4 w-4" />
          Skip to Session
        </Button>
      </div>

      <div className="flex items-center gap-3">
        <Progress value={progress} className="flex-1" />
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {current + 1} / {trials.length}
        </span>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={trial.trial_id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  {trial.paradigm_label}
                </CardTitle>
                <Badge variant="secondary">Practice</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {trial.instruction}
              </p>
            </CardHeader>
            <CardContent className="space-y-6">
              <TaskRenderer trial={trial} />

              {!showFeedback && (
                <ResponseInput
                  trial={trial}
                  onSubmit={handleResponse}
                  disabled={false}
                />
              )}

              {showFeedback && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-3"
                >
                  <div
                    className={`flex items-center gap-2 rounded-md px-4 py-3 ${
                      isCorrect
                        ? "bg-green-500/10 text-green-600"
                        : "bg-red-500/10 text-red-600"
                    }`}
                  >
                    {isCorrect ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <XCircle className="h-5 w-5" />
                    )}
                    <div>
                      <div className="font-medium text-sm">
                        {isCorrect ? "Correct" : "Incorrect"}
                      </div>
                      <div className="text-xs opacity-80">
                        {!isCorrect && (
                          <>
                            Correct answer: {trial.correct_answer}
                            {response && ` (you answered: ${response})`}
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {trial.explanation && (
                    <p className="text-sm text-muted-foreground">
                      {trial.explanation}
                    </p>
                  )}

                  <Button onClick={nextTrial} className="w-full">
                    {current < trials.length - 1 ? (
                      <>
                        Next Paradigm
                        <ChevronRight className="ml-2 h-4 w-4" />
                      </>
                    ) : (
                      <>
                        Start Session
                        <ChevronRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export default function PracticePage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-muted-foreground">Loading...</div>}>
      <PracticeContent />
    </Suspense>
  );
}
