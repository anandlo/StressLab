"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Search, BookOpen, ExternalLink, Clock, Keyboard, Eye, X, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useParadigms } from "@/hooks/use-queries";
import type { ParadigmMeta } from "@/lib/types";

const CATEGORIES = [
  "all",
  "attention",
  "memory",
  "executive",
  "arithmetic",
  "spatial",
  "adaptive",
  "social",
] as const;

const INPUT_MODE_LABELS: Record<string, string> = {
  text: "Text entry",
  keyboard: "Arrow keys",
  spacebar: "Spacebar",
  click: "Button click",
  none: "Timer only",
};

const STIMULUS_TYPE_LABELS: Record<string, string> = {
  text: "Text",
  stroop: "Color-word",
  arrows: "Arrow array",
  shape: "Visual shape",
  sequence: "Sequence",
  cards: "Card matching",
  grid: "Grid pattern",
  timer_only: "Timer",
  letter_stream: "Letter stream",
  dual: "Dual task",
};

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  attention: "Tasks measuring sustained, selective, and divided attention",
  memory: "Tasks measuring working memory capacity and retrieval",
  executive: "Tasks measuring cognitive flexibility and executive control",
  arithmetic: "Tasks involving mental computation under time pressure",
  spatial: "Tasks measuring visuospatial processing and mental rotation",
  adaptive: "Tasks that adjust difficulty based on performance",
  social: "Social-evaluative and physical stressor protocols",
};

export default function LibraryPage() {
  const { data: paradigms, isLoading } = useParadigms();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [selectedParadigm, setSelectedParadigm] = useState<ParadigmMeta | null>(null);

  const filtered = useMemo(() => {
    if (!paradigms) return [];
    return paradigms.filter((p) => {
      const matchesCategory =
        category === "all" ||
        p.category.toLowerCase() === category.toLowerCase();
      const matchesSearch =
        !search ||
        p.label.toLowerCase().includes(search.toLowerCase()) ||
        p.reference.toLowerCase().includes(search.toLowerCase()) ||
        p.description.toLowerCase().includes(search.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [paradigms, search, category]);

  const categoryCounts = useMemo(() => {
    if (!paradigms) return {};
    const counts: Record<string, number> = { all: paradigms.length };
    for (const p of paradigms) {
      const cat = p.category.toLowerCase();
      counts[cat] = (counts[cat] ?? 0) + 1;
    }
    return counts;
  }, [paradigms]);

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Paradigm Library</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Research-backed cognitive stress induction paradigms
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search paradigms..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary" className="text-sm">
          {filtered.length} paradigms
        </Badge>
      </div>

      <Tabs value={category} onValueChange={setCategory}>
        <TabsList className="flex flex-wrap h-auto gap-1">
          {CATEGORIES.map((cat) => (
            <TabsTrigger key={cat} value={cat} className="capitalize">
              {cat}
              {categoryCounts[cat] !== undefined && (
                <span className="ml-1 text-xs text-muted-foreground">
                  ({categoryCounts[cat]})
                </span>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        {CATEGORIES.map((cat) => (
          <TabsContent key={cat} value={cat} className="mt-4">
            {cat !== "all" && CATEGORY_DESCRIPTIONS[cat] && (
              <p className="text-sm text-muted-foreground mb-4">
                {CATEGORY_DESCRIPTIONS[cat]}
              </p>
            )}
            {isLoading ? (
              <div className="py-12 text-center text-muted-foreground">
                Loading paradigms...
              </div>
            ) : filtered.length === 0 ? (
              <div className="py-12 text-center text-muted-foreground">
                <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-50" />
                <p>No paradigms found.</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {filtered.map((p, i) => (
                  <motion.div
                    key={p.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                  >
                    <Card
                      className="h-full cursor-pointer transition-all hover:shadow-md hover:border-primary/30"
                      onClick={() => setSelectedParadigm(p)}
                    >
                      <CardHeader className="pb-2">
                        <div className="flex items-start justify-between gap-2">
                          <CardTitle className="text-sm leading-tight">
                            {p.label}
                          </CardTitle>
                          <Badge
                            variant="outline"
                            className="text-[10px] shrink-0 capitalize"
                          >
                            {p.category}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
                          {p.description}
                        </p>

                        <div className="text-xs text-primary/80 italic line-clamp-1">
                          {p.reference}
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                          <Badge variant="secondary" className="text-[10px]">
                            {INPUT_MODE_LABELS[p.input_mode] ?? p.input_mode}
                          </Badge>
                          <Badge variant="secondary" className="text-[10px]">
                            {STIMULUS_TYPE_LABELS[p.stimulus_type] ??
                              p.stimulus_type}
                          </Badge>
                          <Badge variant="secondary" className="text-[10px]">
                            {p.base_time_sec}s base
                          </Badge>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      <ParadigmDetailDialog
        paradigm={selectedParadigm}
        onClose={() => setSelectedParadigm(null)}
      />
    </div>
  );
}

function ParadigmDetailDialog({
  paradigm,
  onClose,
}: {
  paradigm: ParadigmMeta | null;
  onClose: () => void;
}) {
  const router = useRouter();
  if (!paradigm) return null;

  const paperUrl = PAPER_LINKS[paradigm.id];

  return (
    <Dialog open={!!paradigm} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <DialogTitle className="text-xl">{paradigm.label}</DialogTitle>
              <Badge variant="outline" className="mt-2 capitalize">
                {paradigm.category}
              </Badge>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-5 mt-2">
          <div>
            <h4 className="text-sm font-medium mb-1.5">Description</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {paradigm.description}
            </p>
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-medium mb-1.5">Reference</h4>
            <p className="text-sm text-muted-foreground italic">
              {paradigm.reference}
            </p>
            {paperUrl && (
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => window.open(paperUrl, "_blank", "noopener,noreferrer")}
              >
                <ExternalLink className="mr-2 h-3.5 w-3.5" />
                View Paper
              </Button>
            )}
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-medium mb-3">Task Details</h4>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg border p-3 text-center">
                <Keyboard className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <div className="text-xs font-medium">Input</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {INPUT_MODE_LABELS[paradigm.input_mode] ?? paradigm.input_mode}
                </div>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <Eye className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <div className="text-xs font-medium">Stimulus</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {STIMULUS_TYPE_LABELS[paradigm.stimulus_type] ?? paradigm.stimulus_type}
                </div>
              </div>
              <div className="rounded-lg border p-3 text-center">
                <Clock className="h-4 w-4 mx-auto text-muted-foreground mb-1" />
                <div className="text-xs font-medium">Base Time</div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {paradigm.base_time_sec} seconds
                </div>
              </div>
            </div>
          </div>

          <Separator />

          <div>
            <h4 className="text-sm font-medium mb-1.5">How it works</h4>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {getParadigmExplanation(paradigm)}
            </p>
          </div>
          <Button
            className="w-full"
            onClick={() => { onClose(); router.push(`/protocol?paradigm=${paradigm.id}`); }}
          >
            Use in Session
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

const PAPER_LINKS: Record<string, string> = {
  // Stroop
  stroop: "https://doi.org/10.1037/h0054651",
  // Stroop, J.R. (1935). Studies of interference in serial verbal reactions. Journal of Experimental Psychology, 18(6), 643-662.
  emotional_stroop: "https://doi.org/10.1037/0033-2909.120.1.3",
  // Williams, J.M.G., Mathews, A., & MacLeod, C. (1996). The emotional Stroop task and psychopathology. Psychological Bulletin, 120(1), 3-24.

  // Attention
  flanker: "https://doi.org/10.3758/BF03203267",
  // Eriksen, B.A. & Eriksen, C.W. (1974). Effects of noise letters upon the identification of a target letter. Perception & Psychophysics, 16(1), 143-149.
  pvt: "https://doi.org/10.3758/BF03200977",
  // Dinges, D.F. & Powell, J.W. (1985). Microcomputer analyses of performance on a portable simple visual RT task. Behavior Research Methods, 17(6), 652-655.
  cpt: "https://doi.org/10.1037/h0043220",
  // Rosvold, H.E., Mirsky, A.F., Sarason, I., Bransome, E.D., & Beck, L.H. (1956). A continuous performance test of brain damage. Journal of Consulting Psychology, 20(5), 343-350.
  go_nogo: "https://doi.org/10.1016/0001-6918(69)90065-1",
  // Donders, F.C. (1869/1969). On the speed of mental processes. Acta Psychologica, 30, 412-431.
  stop_signal: "https://doi.org/10.1037/0033-295X.91.3.295",
  // Logan, G.D. & Cowan, W.B. (1984). On the ability to inhibit thought and action. Psychological Review, 91(3), 295-327.
  ant: "https://doi.org/10.1162/089892902317361886",
  // Fan, J., McCandliss, B.D., Sommer, T., Raz, A., & Posner, M.I. (2002). Testing the efficiency and independence of attentional networks. Journal of Cognitive Neuroscience, 14(3), 340-347.

  // Memory
  n_back: "https://doi.org/10.1037/h0043688",
  // Kirchner, W.K. (1958). Age differences in short-term retention of rapidly changing information. Journal of Experimental Psychology, 55(4), 352-358.
  operation_span: "https://doi.org/10.1016/0749-596x(89)90040-5",
  // Turner, M.L. & Engle, R.W. (1989). Is working memory capacity task dependent? Journal of Memory and Language, 28(2), 127-154.
  sternberg: "https://doi.org/10.1126/science.153.3736.652",
  // Sternberg, S. (1966). High-speed scanning in human memory. Science, 153(3736), 652-654.

  // Arithmetic
  serial_subtraction: "https://doi.org/10.1159/000119004",
  // Kirschbaum, C., Pirke, K.M., & Hellhammer, D.H. (1993). The 'Trier Social Stress Test'. Neuropsychobiology, 28, 76-81.
  backwards_counting: "https://doi.org/10.1159/000119004",
  // Kirschbaum, C., Pirke, K.M., & Hellhammer, D.H. (1993). The 'Trier Social Stress Test'. Neuropsychobiology, 28, 76-81.
  pasat: "https://doi.org/10.2466/pms.1977.44.2.367",
  // Gronwall, D.M.A. (1977). Paced auditory serial-addition task. Perceptual and Motor Skills, 44(2), 367-373.

  // Spatial
  mental_rotation: "https://doi.org/10.1126/science.171.3972.701",
  // Shepard, R.N. & Metzler, J. (1971). Mental rotation of three-dimensional objects. Science, 171(3972), 701-703.
  simon_task: "https://doi.org/10.1037/h0020586",
  // Simon, J.R. & Rudell, A.P. (1967). Auditory S-R compatibility: Effect of an irrelevant cue on information processing. Journal of Applied Psychology, 51(3), 300-304.

  // Executive
  wcst: "https://doi.org/10.1080/00221309.1948.9918159",
  // Berg, E.A. (1948). A simple objective technique for measuring flexibility in thinking. Journal of General Psychology, 39(1), 15-22.
  tower_of_london: "https://doi.org/10.1098/rstb.1982.0082",
  // Shallice, T. (1982). Specific impairments of planning. Philosophical Transactions of the Royal Society B, 298(1089), 199-209.
  task_switching: "https://doi.org/10.1016/s1364-6613(03)00028-7",
  // Monsell, S. (2003). Task switching. Trends in Cognitive Sciences, 7(3), 134-140.

  // Adaptive
  mist: "https://doi.org/10.1139/jpn.0541",
  // Dedovic, K. et al. (2005). The Montreal Imaging Stress Task. Journal of Psychiatry and Neuroscience, 30(5), 319-325.
  dual_task: "https://doi.org/10.1037/0033-2909.116.2.220",
  // Pashler, H. (1994). Dual-task interference in simple tasks: Data and theory. Psychological Bulletin, 116(2), 220-244.

  // Social
  speech_prep: "https://doi.org/10.1159/000119004",
  // Kirschbaum, C., Pirke, K.M., & Hellhammer, D.H. (1993). The 'Trier Social Stress Test'. Neuropsychobiology, 28, 76-81.
  cold_pressor: "https://doi.org/10.1111/j.1469-8986.1975.tb01289.x",
  // Lovallo, W. (1975). The cold pressor test and autonomic function. Psychophysiology, 12(3), 268-282.
  mast: "https://doi.org/10.1016/j.psyneuen.2012.04.012",
  // Smeets, T. et al. (2012). Introducing the Maastricht Acute Stress Test (MAST). Psychoneuroendocrinology, 37(12), 1998-2008.
};

function getParadigmExplanation(p: ParadigmMeta): string {
  const explanations: Record<string, string> = {
    stroop: "Participants must name the ink color of color words while ignoring the word meaning. Incongruent trials (e.g., the word 'RED' in blue ink) create interference that reliably increases cognitive load and stress response. Example: you see the word 'GREEN' printed in red ink and must type 'RED'.",
    emotional_stroop: "A variant of the Stroop task using emotionally charged words. Participants name the ink color while suppressing automatic reading of threatening or emotional content, measuring attentional bias to emotional stimuli. Example: you see the word 'FAILURE' in purple ink and must type 'PURPLE'.",
    flanker: "A row of arrows is presented and participants must identify the direction of the central arrow while ignoring flanking distractors. Incongruent flankers create response conflict, taxing selective attention. Example: given <<><< you press RIGHT for the center arrow.",
    simon_task: "Stimuli appear on the left or right side of the screen. Participants respond based on stimulus identity, not position. When stimulus position conflicts with the correct response side, interference occurs. Example: a blue circle appears on the right, but blue means press LEFT.",
    go_nogo: "Participants respond quickly to frequent 'go' stimuli but must withhold responses to rare 'no-go' stimuli. Lure stimuli (green squares that look like go signals) increase inhibition demands. Example: press spacebar for a green circle, but withhold for a red square or green square.",
    cpt: "Letters appear one at a time. Participants must respond to a target letter but withhold responses to all others, measuring sustained attention over extended periods. Example: press spacebar only when 'X' appears; ignore all other letters.",
    stop_signal: "Participants respond to arrow stimuli, but on some trials an auditory or visual stop signal appears after a variable delay, requiring them to cancel the already-initiated response. Example: press LEFT for a left arrow, but if it turns red, stop.",
    ant: "Combines cue-target sequences with flanker arrays to measure three attention networks: alerting (response to cues), orienting (spatial cueing benefit), and executive control (flanker interference). Example: a cue flashes, then <<><< appears above or below center.",
    n_back: "Working memory task where participants monitor a stream of items and indicate when the current item matches the one presented N positions back. Higher N values increase cognitive demand. Example: in 2-back, if you see 3, 7, 5, 7, the second 7 matches 2 steps ago.",
    digit_span: "Sequences of digits are presented and participants must recall them in order (forward) or reverse order (backward), measuring verbal working memory capacity. Example: after seeing 4 7 2 9, type '4729' forward or '9274' backward.",
    corsi_block: "The spatial analog of digit span. Blocks in a grid light up in sequence and participants must reproduce the pattern, measuring visuospatial working memory.",
    sternberg: "A memory set of items is presented, followed by a probe item. Participants must indicate whether the probe was in the memory set, measuring memory scanning speed. Example: study {3, 7, 1, 9}, then when probe '7' appears, press YES.",
    operation_span: "A dual-task combining math verification with letter recall. Participants verify equations while remembering letters, measuring working memory capacity under cognitive load. Example: verify '(3 + 4) = 7', remember letter 'F', then recall all letters in order.",
    mental_arithmetic: "Participants solve arithmetic problems of increasing difficulty under time pressure. A reliable stress inducer used extensively in psychophysiological research. Example: solve '(15 + 8) x 3' and type 69.",
    paced_serial_addition: "The PASAT: numbers are presented serially and participants must add each new number to the one immediately preceding it, creating continuous cognitive demand. Example: if the last number was 5 and the current is 8, type 13.",
    number_comparison: "Pairs of numbers are presented and participants must quickly judge which is larger, measuring numerical processing speed and decision-making efficiency.",
    equation_verification: "Mathematical equations are presented and participants must judge whether they are correct or incorrect, combining arithmetic processing with verification demands.",
    trail_making: "Participants connect a sequence of targets (numbers, letters, or alternating) as quickly as possible, measuring visual search, processing speed, and cognitive flexibility. Example: in TMT-B, the sequence 1-A-2-B-?-C has the missing item 3.",
    wisconsin_card: "Cards must be sorted by rules that change without warning. Participants must discover the current sorting rule through trial and error, measuring set-shifting and cognitive flexibility. Example: if the hidden rule is 'color', match a red triangle to a red circle.",
    wcst: "Cards must be sorted by rules that change without warning. Participants must discover the current sorting rule through trial and error, measuring set-shifting and cognitive flexibility. Example: if the hidden rule is 'color', match a red triangle to a red circle.",
    mental_rotation: "Participants track cumulative rotations to determine final compass direction, measuring spatial reasoning ability. Example: start facing NORTH, apply 'Right 90' then 'Left 90', you end facing NORTH.",
    spatial_span: "A grid-based spatial working memory task where participants must track and recall target positions in a spatial array.",
    cold_pressor: "A physical stressor protocol where participants are instructed to immerse their hand in cold water. This timer-based task measures cold pressor tolerance as a stress induction method.",
    tsst_arithmetic: "The arithmetic component of the Trier Social Stress Test. Participants perform serial subtraction from a large number while being observed, combining cognitive and social-evaluative stress.",
    mast: "The Maastricht Acute Stress Test alternates mental arithmetic blocks with simulated cold pressor immersions, combining cognitive and physical stressors in a standardized protocol.",
    serial_subtraction: "Participants subtract a fixed value one step at a time from a single running total. The step stays constant for the entire session (either -13 from 1022 or -17 from 2083, the two variants from Kirschbaum et al. 1993). Example: 1022, 1009, 996, 983...",
    backwards_counting: "Participants count backwards from a fixed starting number by a constant step, one subtraction per trial. The chain is continuous across the session (e.g., 100 by 3s or 1000 by 7s). Example: 100, 97, 94, 91...",
    pasat: "Numbers are presented one at a time. Participants must add each new number to the immediately preceding number and respond before the next appears. Example: if the last number was 5 and the current is 8, answer 13.",
    speech_prep: "Participants are given a topic and must mentally prepare a short speech under time pressure. The anticipatory stress from upcoming social evaluation mirrors the speech component of the TSST, reliably inducing cortisol and autonomic arousal.",
    mist: "Adaptive arithmetic with false social-evaluative comparison. The system manipulates time limits and displays a fake performance bar that always shows you trailing behind peers, creating social-evaluative threat. Example: solve '(12 + 8) x 3' while a bar shows 'Avg: 85%, You: 60%'.",
    task_switching: "Participants must rapidly switch between different classification rules applied to the same stimuli. Rule switches force cognitive reconfiguration, creating switch costs. Example: for the number 7, if the rule changes to 'parity', answer ODD; if 'magnitude', answer HIGH.",
    rapid_comparison: "Two sets of numbers are shown and participants must quickly determine which set has the larger total sum. Example: Set A = 45 + 32 + 18 vs Set B = 27 + 41 + 30, press A or B.",
    dual_task: "Participants must solve an arithmetic problem while simultaneously detecting a target letter among distractors. Example: solve '25 + 13' and check if 'K' appears among the letters, type '38Y' or '38N'.",
    visual_search: "Participants search a grid of symbols for a target among distractors. At higher difficulty, distractors share features with the target, requiring serial scanning. Example: find a circle among squares and triangles in a 5x5 grid.",
  };

  return explanations[p.id] ??
    `This ${p.category} paradigm uses ${STIMULUS_TYPE_LABELS[p.stimulus_type]?.toLowerCase() ?? p.stimulus_type} stimuli with ${INPUT_MODE_LABELS[p.input_mode]?.toLowerCase() ?? p.input_mode} input. Base time limit is ${p.base_time_sec} seconds, adjusted by intensity and difficulty.`;
}
