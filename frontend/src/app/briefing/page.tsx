"use client";

import { useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronRight, Clock, Keyboard } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useParadigms } from "@/hooks/use-queries";
import type { SessionConfig, ParadigmMeta } from "@/lib/types";

const INPUT_MODE_LABELS: Record<string, string> = {
  text: "Type your answer",
  keyboard: "Arrow keys",
  spacebar: "Press spacebar",
  click: "Click a button",
  none: "Timer only",
};

const INPUT_MODE_EXAMPLES: Record<string, string> = {
  text: "A text field will appear. Type your answer and press Enter.",
  keyboard: "Use the arrow keys on your keyboard to indicate your choice.",
  spacebar: "Press the spacebar when you see the target stimulus.",
  click: "Click one of the displayed buttons to respond.",
  none: "Watch the screen and follow the on-screen instructions. No key press is needed.",
};

/* Detailed briefing text shown to participants before the session starts.
   Keyed by paradigm id. Falls back to ParadigmMeta.description when absent. */
const PARADIGM_BRIEFINGS: Record<string, string> = {
  // -- Arithmetic --
  serial_subtraction:
    "You will be given a starting number and a subtraction value. On each trial, subtract that value from your previous answer and type the result. For example, if you start at 1022 and subtract by 13, you would type 1009, then 996, then 983, and so on. This task is based on the Trier Social Stress Test (TSST) arithmetic protocol and measures sustained mental effort under pressure.",
  mental_arithmetic:
    "You will see a multi-step arithmetic expression (e.g., 7 + 3 x 2 - 4). Calculate the result mentally and type your answer. Expressions grow more complex at higher difficulty levels. This task measures mental computation ability and working memory.",
  backwards_counting:
    "You will count backwards from a starting number by a fixed step. Each trial shows you the current number and the step size. Type the next number in the sequence. For example, if counting back from 100 by 7, you would type 93, then 86, then 79. Based on the TSST protocol.",
  pasat:
    "The Paced Auditory Serial Addition Test. Numbers appear one at a time. For each new number, add it to the number that appeared immediately before it and type the sum. The first number is just for remembering, no addition is needed. For example, if you see 3 then 7, type 10. If the next number is 2, add it to 7 (not to 10) and type 9. This task measures working memory and processing speed.",

  // -- Attention --
  stroop:
    "A color word (e.g., RED, BLUE, GREEN) will appear in a different ink color. Your job is to type the INK COLOR, not the word itself. For example, if the word BLUE is printed in red ink, type 'red'. At higher difficulty, a small distractor word may also appear below the main word. This is a classic measure of selective attention and inhibitory control.",
  emotional_stroop:
    "Words will appear in colored ink. Some words are emotionally charged (e.g., stress-related), others are neutral. Regardless of what the word says, type the INK COLOR of the word. For example, if the word DEADLINE appears in green ink, type 'green'. At higher difficulty, distractor text may appear. This task measures attentional bias toward emotionally relevant stimuli.",
  flanker:
    "A row of arrows will appear (e.g., <<><<). Identify the direction of the CENTER arrow and press the corresponding arrow key. Ignore the surrounding (flanker) arrows, which may point in a different direction. This task measures focused attention and conflict resolution.",
  pvt:
    "Stare at the screen and wait. After a random delay, a visual stimulus will appear. Press the spacebar as quickly as possible when you see it. If no stimulus appears within the time window, the trial ends. This task measures sustained attention and psychomotor vigilance.",
  cpt:
    "Letters will appear one at a time. Press the spacebar ONLY when you see the target letter (shown in the instructions). Withhold your response for all other letters. This task measures sustained attention and impulse control.",
  go_nogo:
    "Symbols will appear on screen. For GO stimuli (green circles), press the spacebar as quickly as possible. For NO-GO stimuli (red squares), do NOT press anything. This task measures response inhibition.",
  stop_signal:
    "An arrow will appear pointing left or right. Press the corresponding arrow key as quickly as possible. However, on some trials a stop signal (the arrow turns red) will appear shortly after. When you see the stop signal, try to withhold your response. This task measures the ability to cancel an already-initiated action.",
  ant:
    "An arrow appears at the center of a row of flanker arrows. Identify the direction of the CENTER arrow using arrow keys. Before the arrows appear, you may or may not see a spatial cue. This task assesses three attention networks: alerting, orienting, and executive control.",
  visual_search:
    "A grid of symbols appears on screen. Determine whether a target symbol (indicated in the instructions) is present among the distractors. Press the right arrow if the target is present, left arrow if absent. The number of items increases with difficulty. This task measures visual search efficiency.",

  // -- Memory --
  n_back:
    "A series of numbers will appear one at a time. Your task is to determine whether the current number matches the one from N steps ago. For a 2-back you compare the current number to the one shown two trials earlier. Press the right arrow for a match and the left arrow for no match. You must hold previous numbers in memory because only the current number is displayed. This task measures working memory capacity.",
  digit_span:
    "A sequence of digits will appear briefly on screen. Memorize them. You will then be asked to type the digits back either in the same order (forward span) or reversed (backward span). The sequence length increases with difficulty. This task measures short-term memory capacity and, for backward span, working memory.",
  operation_span:
    "This task has two alternating phases. In the encode phase, you see a math equation (e.g., 3 + 4 = 8, is this correct?) and a letter to remember. Judge whether the math is correct by typing YES or NO. At the same time, memorize the letter. After several encode trials, a recall phase asks you to type all the letters you saw, in order. The number of letters per set increases with difficulty. This task measures working memory span.",
  sternberg:
    "A set of digits will appear for you to memorize. Then a single probe digit appears. Determine whether the probe was in the memorized set. Press the right arrow for Yes and the left arrow for No. The set size increases with difficulty. This task measures short-term memory scanning speed.",

  // -- Executive --
  wcst:
    "Cards with varying shapes, colors, and numbers will appear. Match each card to one of the reference piles by pressing 1, 2, 3, or 4. The sorting rule (color, shape, or number) is hidden and changes without warning after several correct matches. Use feedback (correct/incorrect) to figure out the current rule. This task measures cognitive flexibility and set-shifting.",
  trail_making:
    "You will see an alternating sequence of numbers and letters (e.g., 1-A-2-B-3-C). Type the next item in the sequence. The sequence alternates between ascending numbers and ascending letters. This task measures processing speed and cognitive flexibility.",
  tower_of_london:
    "You will see a current arrangement and a goal arrangement of colored discs on pegs. Determine the minimum number of moves required to reach the goal configuration. Type the number. This task measures planning ability and problem solving.",
  task_switching:
    "Two classification rules alternate. A cue tells you which rule to apply (e.g., odd/even vs. greater/less than 5). Press the left or right arrow key based on the active rule. This task measures cognitive flexibility and switch cost.",

  // -- Spatial --
  mental_rotation:
    "You will see a sequence of rotation instructions (e.g., rotate 90 degrees clockwise, then 45 degrees counter-clockwise). Track the cumulative rotation mentally and select the final orientation using the arrow keys. This task measures spatial reasoning.",
  simon_task:
    "A colored stimulus appears on the left or right side of the screen. Respond based on the COLOR (e.g., left arrow for red, right arrow for blue), not its screen position. The stimulus position sometimes conflicts with the correct response. This task measures spatial interference and conflict resolution.",
  pattern_completion:
    "A numerical sequence with a missing element is shown (e.g., 2, 4, ?, 8). Identify the pattern and type the missing number. Patterns grow more complex at higher difficulty. This task measures fluid reasoning.",

  // -- Adaptive --
  mist:
    "Solve arithmetic problems under time pressure. A progress bar shows your performance compared to a supposed average of other participants. This comparison is deliberately manipulated to induce social-evaluative stress regardless of your actual performance. Based on the Montreal Imaging Stress Task (MIST) protocol.",
  rapid_comparison:
    "Two sets of numbers appear side by side. Determine which set has the larger total. Press the right arrow for the right set and the left arrow for the left set. The number of items per set increases with difficulty.",
  dual_task:
    "You must handle two tasks at once: solve an arithmetic problem and identify a displayed letter. Type the arithmetic answer. After several trials, you may be asked to recall the letters. This task measures divided attention and multitasking ability.",

  // -- Social-evaluative / Physical --
  speech_prep:
    "Read the given topic and mentally prepare a speech about it. This is a passive task: no typing or key presses are needed. Use the time to organize your thoughts as if you were about to deliver the speech to evaluators. Based on the speech preparation phase of the TSST.",
  cold_pressor:
    "This screen provides timing and instructions for the cold pressor procedure. Submerge your hand in cold water as directed and keep it there for the indicated duration. No key presses are needed. This is a physical stressor used in pain and stress research.",
  mast:
    "This protocol alternates between mental arithmetic trials and cold pressor immersion blocks. During arithmetic blocks, solve problems and type answers. During cold pressor blocks, follow the immersion instructions on screen. Based on the Maastricht Acute Stress Test.",
};

function BriefingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const configStr = searchParams.get("config");

  const { data: allParadigms } = useParadigms();

  const config: SessionConfig | null = useMemo(() => {
    if (!configStr) return null;
    try {
      return JSON.parse(decodeURIComponent(configStr));
    } catch {
      return null;
    }
  }, [configStr]);

  const paradigms: ParadigmMeta[] = useMemo(() => {
    if (!allParadigms || !config) return [];
    return config.paradigm_ids
      .map((id) => allParadigms.find((p) => p.id === id))
      .filter(Boolean) as ParadigmMeta[];
  }, [allParadigms, config]);

  function proceed() {
    if (!configStr || !config) return;
    if (config.practice_enabled) {
      router.push(`/practice?config=${configStr}`);
    } else {
      router.push(`/session?config=${configStr}`);
    }
  }

  if (!configStr || !config) {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-4">
        <h1 className="text-3xl font-bold tracking-tight">Session Overview</h1>
        <p className="text-sm text-muted-foreground">
          No session configured. Set up a protocol first.
        </p>
        <Button variant="outline" onClick={() => router.push("/protocol")}>
          Go to Protocol
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-2">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Session Overview</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {paradigms.length > 0
            ? `This session includes ${paradigms.length} task${paradigms.length !== 1 ? "s" : ""}. Read through each before you begin.`
            : "Loading task information..."}
        </p>
      </div>

      <div className="space-y-3">
        {paradigms.map((p, i) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground w-6 shrink-0 tabular-nums">
                      {i + 1}.
                    </span>
                    <CardTitle className="text-sm leading-normal">
                      {p.label}
                    </CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] capitalize shrink-0">
                    {p.category}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pl-12 space-y-3">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {PARADIGM_BRIEFINGS[p.id] ?? p.description}
                </p>
                <div className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">How to respond: </span>
                  {INPUT_MODE_EXAMPLES[p.input_mode] ??
                    INPUT_MODE_LABELS[p.input_mode] ??
                    p.input_mode}
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    ~{p.base_time_sec}s per trial
                  </span>
                  <span className="flex items-center gap-1">
                    <Keyboard className="h-3 w-3" />
                    {INPUT_MODE_LABELS[p.input_mode] ?? p.input_mode}
                  </span>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <Separator />

      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          {config.practice_enabled
            ? "A short practice round follows. Trials are untimed with immediate feedback for each task."
            : `The timed session will begin immediately. Duration: ${config.duration_min} minutes.`}
        </p>
        <Button
          onClick={proceed}
          className="shrink-0"
          disabled={paradigms.length === 0}
        >
          {config.practice_enabled ? "Begin Practice" : "Begin Session"}
          <ChevronRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export default function BriefingPage() {
  return (
    <Suspense
      fallback={
        <div className="py-24 text-center text-muted-foreground">
          Loading...
        </div>
      }
    >
      <BriefingContent />
    </Suspense>
  );
}
