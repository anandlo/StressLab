"use client";

import { useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Target,
  Clock,
  Activity,
  Timer,
  Download,
  ChevronLeft,
  ChevronRight,
  Info,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import { useSessions, useSession } from "@/hooks/use-queries";
import type { SessionSummary } from "@/lib/types";
import { downloadSessionCSV, patchSessionNotes } from "@/lib/api";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

function ResultsContent() {
  const searchParams = useSearchParams();
  const summaryParam = searchParams.get("summary");
  const sessionParam = searchParams.get("session");

  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const { data: sessionList } = useSessions();
  const { data: loadedSession } = useSession(selectedFile);
  const csvFilename = selectedFile ?? sessionParam;

  const [exportOpen, setExportOpen] = useState(false);
  const [exportTrials, setExportTrials] = useState(true);
  const [exportSummary, setExportSummary] = useState(true);
  const [exportAnalysis, setExportAnalysis] = useState(false);

  // Sort/filter state for session picker
  const [filterParticipant, setFilterParticipant] = useState("");
  const [filterIntensity, setFilterIntensity] = useState<"all" | "low" | "medium" | "high">("all");
  const [sortBy, setSortBy] = useState<"date" | "accuracy" | "trials">("date");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");

  // Either from URL param (just-completed session) or loaded from API
  const summary: SessionSummary | null = useMemo(() => {
    if (summaryParam) {
      try {
        return JSON.parse(decodeURIComponent(summaryParam));
      } catch {
        return null;
      }
    }
    return loadedSession ?? null;
  }, [summaryParam, loadedSession]);

  // Charts data
  const accuracyOverTime = useMemo(() => {
    if (!summary) return [];
    let correct = 0;
    return summary.trials.map((t, i) => {
      if (t.is_correct) correct++;
      return {
        trial: i + 1,
        accuracy: Math.round((correct / (i + 1)) * 100),
        rt: Math.round(t.response_time_ms),
      };
    });
  }, [summary]);

  const perParadigmData = useMemo(() => {
    if (!summary?.per_paradigm) return [];
    return Object.entries(summary.per_paradigm).map(([name, stats]) => ({
      name,
      accuracy: Math.round(stats.accuracy_pct),
      avgRT: Math.round(stats.avg_response_time_ms),
      total: stats.total,
      metric_focus: stats.metric_focus ?? "mixed",
      median_rt_ms: stats.median_rt_ms,
      lapse_rate: stats.lapse_rate,
      commission_errors: stats.commission_errors,
      timeout_rate: stats.timeout_rate,
    }));
  }, [summary]);

  // ── Scientific Analysis ──────────────────────────────────────────
  const rtHistogram = useMemo(() => {
    if (!summary) return [];
    const BIN = 150;
    const MAX = 3000;
    const bins: Record<number, number> = {};
    for (let b = 0; b <= MAX; b += BIN) bins[b] = 0;
    summary.trials.forEach((t) => {
      if (!t.timed_out && t.response_time_ms > 0) {
        const b = Math.min(Math.floor(t.response_time_ms / BIN) * BIN, MAX);
        bins[b] = (bins[b] ?? 0) + 1;
      }
    });
    return Object.entries(bins).map(([ms, n]) => ({
      rt: `${ms}-${Number(ms) + BIN}`,
      count: n,
    }));
  }, [summary]);

  const quartileData = useMemo(() => {
    if (!summary) return [];
    const sz = Math.ceil(summary.trials.length / 4);
    return [0, 1, 2, 3].map((q) => {
      const slice = summary.trials.slice(q * sz, (q + 1) * sz);
      const correct = slice.filter((t) => t.is_correct).length;
      return {
        quarter: `Q${q + 1}`,
        accuracy: slice.length ? Math.round((correct / slice.length) * 100) : 0,
        n: slice.length,
      };
    });
  }, [summary]);

  const seqEffects = useMemo(() => {
    if (!summary || summary.trials.length < 2) return null;
    const postCorrect: number[] = [];
    const postError: number[] = [];
    for (let i = 1; i < summary.trials.length; i++) {
      const curr = summary.trials[i];
      if (curr.timed_out || curr.response_time_ms <= 0) continue;
      if (summary.trials[i - 1].is_correct) postCorrect.push(curr.response_time_ms);
      else postError.push(curr.response_time_ms);
    }
    const mean = (arr: number[]) =>
      arr.length ? Math.round(arr.reduce((a, b) => a + b, 0) / arr.length) : 0;
    return {
      postCorrect: mean(postCorrect),
      postError: mean(postError),
      nCorrect: postCorrect.length,
      nError: postError.length,
    };
  }, [summary]);

  const analysisStats = useMemo(() => {
    if (!summary) return null;
    const rts = summary.trials
      .filter((t) => !t.timed_out && t.response_time_ms > 0)
      .map((t) => t.response_time_ms);
    if (!rts.length) return null;
    const mean = rts.reduce((a, b) => a + b, 0) / rts.length;
    const variance = rts.reduce((a, b) => a + (b - mean) ** 2, 0) / rts.length;
    const sd = Math.sqrt(variance);
    const sorted = [...rts].sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];
    const cv = mean > 0 ? (sd / mean) * 100 : 0;
    const ies = summary.accuracy_pct > 0 ? mean / (summary.accuracy_pct / 100) : 0;
    const lapses = summary.trials.filter((t) => t.timed_out).length;
    const lapseRate = (lapses / summary.trials.length) * 100;
    const half = Math.floor(summary.trials.length / 2);
    const firstAcc =
      summary.trials.slice(0, half).filter((t) => t.is_correct).length /
      (half || 1);
    const lastAcc =
      summary.trials.slice(half).filter((t) => t.is_correct).length /
      (summary.trials.length - half || 1);
    const fatigueIndex = (firstAcc - lastAcc) * 100;
    const skewness =
      sd > 0 && rts.length >= 3
        ? rts.reduce((a: number, b: number) => a + ((b - mean) / sd) ** 3, 0) /
          rts.length
        : 0;
    const p10 = sorted[Math.max(0, Math.floor(sorted.length * 0.1))];
    const p90 = sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.9))];
    return {
      mean: Math.round(mean),
      median: Math.round(median),
      sd: Math.round(sd),
      cv: cv.toFixed(1),
      ies: Math.round(ies),
      lapseRate: lapseRate.toFixed(1),
      fatigueIndex: fatigueIndex.toFixed(1),
      skewness: skewness.toFixed(2),
      p10: Math.round(p10 ?? 0),
      p90: Math.round(p90 ?? 0),
    };
  }, [summary]);

  const actualDurationLabel = useMemo(() => {
    if (!summary) return "";
    const start = new Date(summary.session_start).getTime();
    const end = new Date(summary.session_end).getTime();
    if (isNaN(start) || isNaN(end) || end <= start)
      return `${Math.round(summary.duration_target_sec / 60)} min`;
    const sec = (end - start) / 1000;
    return sec < 90 ? `${Math.round(sec)}s` : `${(sec / 60).toFixed(1)} min`;
  }, [summary]);

  // Show session picker when no summary is loaded
  if (!summary) {
    const filtered = (sessionList ?? [])
      .filter((s) => {
        if (filterParticipant && !s.participant_id.toLowerCase().includes(filterParticipant.toLowerCase())) return false;
        if (filterIntensity !== "all" && s.intensity !== filterIntensity) return false;
        return true;
      })
      .sort((a, b) => {
        let val = 0;
        if (sortBy === "date") val = new Date(a.session_start).getTime() - new Date(b.session_start).getTime();
        else if (sortBy === "accuracy") val = (a.accuracy_pct ?? 0) - (b.accuracy_pct ?? 0);
        else if (sortBy === "trials") val = (a.total_tasks ?? 0) - (b.total_tasks ?? 0);
        return sortOrder === "desc" ? -val : val;
      });

    return (
      <div className="space-y-6 max-w-7xl">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Select a session to view analysis and export data
          </p>
        </div>
        {!(sessionList?.length) ? (
          <div className="py-24 text-center text-muted-foreground">
            No sessions yet. Complete a session to see results.
          </div>
        ) : (
          <>
            {/* Sort and filter bar */}
            <div className="flex flex-wrap gap-3 items-center">
              <Input
                placeholder="Search participant…"
                value={filterParticipant}
                onChange={(e) => setFilterParticipant(e.target.value)}
                className="h-8 w-48 text-xs"
              />
              <select
                value={filterIntensity}
                onChange={(e) => setFilterIntensity(e.target.value as typeof filterIntensity)}
                className="h-8 rounded-md border bg-background px-2 text-xs text-foreground"
              >
                <option value="all">All intensities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className="h-8 rounded-md border bg-background px-2 text-xs text-foreground"
              >
                <option value="date">Sort: Date</option>
                <option value="accuracy">Sort: Accuracy</option>
                <option value="trials">Sort: Trials</option>
              </select>
              <button
                className="h-8 rounded-md border bg-background px-3 text-xs text-foreground hover:bg-muted transition-colors"
                onClick={() => setSortOrder((o) => (o === "desc" ? "asc" : "desc"))}
              >
                {sortOrder === "desc" ? "Newest first" : "Oldest first"}
              </button>
              {filtered.length !== sessionList.length && (
                <span className="text-xs text-muted-foreground">{filtered.length} of {sessionList.length}</span>
              )}
            </div>
            <div className="rounded-lg border divide-y overflow-hidden">
              {filtered.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground">No sessions match the current filter.</div>
              ) : filtered.map((s) => (
                <button
                  key={s.filename}
                  className="w-full text-left flex items-center justify-between gap-4 px-5 py-4 hover:bg-muted/40 transition-colors"
                  onClick={() => setSelectedFile(s.filename)}
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium">{s.participant_id}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {new Date(s.session_start).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <Badge variant="secondary" className="tabular-nums">
                      {s.accuracy_pct?.toFixed(0)}% accuracy
                    </Badge>
                    <Badge variant="outline">{s.total_tasks} trials</Badge>
                    <Badge variant="outline" className="capitalize">
                      {s.intensity}
                    </Badge>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        {selectedFile && !summaryParam && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedFile(null)}
            className="-ml-2 mb-2 gap-1 text-muted-foreground"
          >
            <ChevronLeft className="h-4 w-4" />
            Sessions
          </Button>
        )}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Sessions</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Session analysis and data export
            </p>
          </div>
          <div className="flex items-center gap-2">
          {summary && (
            <Button variant="outline" onClick={() => setExportOpen(true)}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          )}
          </div>
        </div>
      </div>

      {summary && (
        <>
          <motion.div
            className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <StatCard
              icon={Target}
              label="Accuracy"
              value={`${summary.accuracy_pct.toFixed(1)}%`}
              explanation="Proportion of trials answered correctly across all paradigms in this session. Timed-out trials count as incorrect."
            />
            <StatCard
              icon={Activity}
              label="Total Tasks"
              value={String(summary.total_tasks)}
              explanation="Total number of trials presented in this session, including timeouts and incorrect responses."
            />
            <StatCard
              icon={Timer}
              label="Avg Response Time"
              value={`${summary.avg_response_time_ms.toFixed(0)} ms`}
              explanation="Mean response latency in milliseconds, computed over all non-timeout trials with a recorded response time."
            />
            <StatCard
              icon={Clock}
              label="Duration"
              value={actualDurationLabel}
              explanation="Actual elapsed time from session start to the last trial, measured from server timestamps."
            />
          </motion.div>

          <Tabs defaultValue="charts">
            <TabsList className="gap-1.5">
              <TabsTrigger value="charts">Charts</TabsTrigger>
              <TabsTrigger value="analysis">Analysis</TabsTrigger>
              <TabsTrigger value="trials">Trial Data</TabsTrigger>
            </TabsList>

            <TabsContent value="charts" className="mt-4">
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Accuracy Over Time</CardTitle>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
                          Running accuracy across the session. Each point shows the percentage of all answers up to that trial that were correct. A falling line suggests fatigue or increasing difficulty.
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={accuracyOverTime}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          dataKey="trial"
                          fontSize={12}
                          tickLine={false}
                        />
                        <YAxis
                          domain={[0, 100]}
                          fontSize={12}
                          tickLine={false}
                        />
                        <ChartTooltip />
                        <Line
                          type="monotone"
                          dataKey="accuracy"
                          stroke="var(--color-primary)"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Response Time (ms)</CardTitle>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
                          How long each trial took from the question appearing to you answering, in milliseconds (1000 ms = 1 second). Spikes indicate individual trials where you took longer than usual.
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={250}>
                      <LineChart data={accuracyOverTime}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          dataKey="trial"
                          fontSize={12}
                          tickLine={false}
                        />
                        <YAxis fontSize={12} tickLine={false} />
                        <ChartTooltip />
                        <Line
                          type="monotone"
                          dataKey="rt"
                          stroke="var(--color-chart-2)"
                          strokeWidth={2}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>

              {/* Accuracy by paradigm */}
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="text-sm">Accuracy by Paradigm</CardTitle>
                </CardHeader>
                <CardContent>
                  {perParadigmData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={Math.max(250, perParadigmData.length * 36)}>
                      <BarChart
                        data={perParadigmData}
                        layout="vertical"
                        margin={{ left: 120 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis
                          type="number"
                          domain={[0, 100]}
                          fontSize={12}
                        />
                        <YAxis
                          type="category"
                          dataKey="name"
                          fontSize={11}
                          width={110}
                          tickLine={false}
                        />
                        <ChartTooltip />
                        <Bar
                          dataKey="accuracy"
                          fill="var(--color-primary)"
                          radius={[0, 4, 4, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-8">
                      No paradigm data available.
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Per-paradigm focus-specific metrics */}
              {perParadigmData.length > 0 && (
                <Card className="mt-6">
                  <CardHeader>
                    <CardTitle className="text-sm">Paradigm-Specific Metrics</CardTitle>
                    <CardDescription className="text-xs">
                      Each paradigm is analyzed according to its primary measurement focus.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {perParadigmData.map((p) => (
                        <div key={p.name} className="flex items-baseline gap-3 text-sm border-b pb-2 last:border-0">
                          <span className="font-medium w-44 shrink-0">{p.name}</span>
                          <span className="text-xs px-1.5 py-0.5 rounded bg-muted font-mono">
                            {p.metric_focus}
                          </span>
                          {p.metric_focus === "speed" && (
                            <span className="text-muted-foreground text-xs">
                              Median RT: {p.median_rt_ms ?? "N/A"} ms | Lapse Rate: {p.lapse_rate ?? 0}%
                            </span>
                          )}
                          {p.metric_focus === "inhibition" && (
                            <span className="text-muted-foreground text-xs">
                              Commission Errors: {p.commission_errors ?? 0} | Timeout Rate: {p.timeout_rate ?? 0}%
                            </span>
                          )}
                          {p.metric_focus === "accuracy" && (
                            <span className="text-muted-foreground text-xs">
                              Accuracy: {p.accuracy}% ({p.total} trials) | Avg RT: {p.avgRT} ms
                            </span>
                          )}
                          {p.metric_focus === "mixed" && (
                            <span className="text-muted-foreground text-xs">
                              Accuracy: {p.accuracy}% | Avg RT: {p.avgRT} ms | {p.total} trials
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="analysis" className="mt-4 space-y-6">
              {/* Statistical summary */}
              {analysisStats && (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <SmallStatCard
                    label="Median Response Time"
                    value={`${analysisStats.median} ms`}
                    description={`The middle value when all response times are sorted. Unlike the mean, it resists distortion from outliers. ${Number(analysisStats.median) > 5000 ? "This is a relatively slow median, which may indicate high cognitive load or unfamiliarity with the tasks." : Number(analysisStats.median) > 2000 ? "This falls in a typical range for moderately demanding cognitive tasks." : "This is a fast median, suggesting the participant found the tasks straightforward."} For researchers: compare across sessions or participants to measure cognitive load changes. A rising median over repeated sessions can signal fatigue or increased task demands.`}
                    formula="Sort all n times and take the middle value (or average the two middle values when n is even)"
                  />
                  <SmallStatCard
                    label="Response Time Variability (CV)"
                    value={`${analysisStats.cv}%`}
                    description={`Coefficient of variation: how much response speed varied relative to the average. ${Number(analysisStats.cv) > 40 ? "Above 40% indicates highly inconsistent pacing, which in research is often linked to lapses of attention, mind-wandering, or variable engagement." : Number(analysisStats.cv) > 30 ? "Between 30-40% is moderate variability. Some fluctuation is normal but may warrant attention." : "Below 30% is fairly consistent pacing, suggesting sustained, even attention."} For researchers: CV is preferred over raw standard deviation because it normalizes for speed differences between participants.`}
                    formula="CV = (standard deviation / mean) x 100"
                  />
                  <SmallStatCard
                    label="Inverse Efficiency Score"
                    value={`${analysisStats.ies} ms`}
                    description={`Combines speed and accuracy into a single number. Lower is better. It penalizes both slow responses and errors, preventing the speed-accuracy trade-off from hiding true performance. ${Number(analysisStats.ies) > 10000 ? "A high IES suggests the participant was either slow, inaccurate, or both." : "This IES falls in a reasonable range."} For researchers: IES is useful when you need a single metric to compare conditions. It was introduced to avoid cases where accuracy looks good only because the participant traded speed for correctness.`}
                    formula="IES = mean response time / proportion correct (e.g. 500 ms / 0.80 accuracy = 625 ms)"
                  />
                  <SmallStatCard
                    label="Lapse Rate"
                    value={`${analysisStats.lapseRate}%`}
                    description={`Percentage of trials where no response was given before time ran out. ${Number(analysisStats.lapseRate) > 10 ? "Above 10% indicates frequent attention lapses. In vigilance research, this strongly correlates with fatigue and reduced arousal." : Number(analysisStats.lapseRate) > 5 ? "Between 5-10% suggests occasional attention drifts. May indicate task disengagement or distraction." : "Below 5% means attention was generally sustained throughout the session."} For researchers: lapse rate is one of the most sensitive measures of sustained attention and is a primary outcome in psychomotor vigilance tasks (PVT).`}
                    formula="Lapse Rate = (number of timeouts / total trials) x 100"
                  />
                  <SmallStatCard
                    label="Response Time Std Dev"
                    value={`${analysisStats.sd} ms`}
                    description={`The absolute spread of response times around the mean, measured in milliseconds. A larger number means more variable performance. For researchers: while CV is better for between-participant comparisons (because it normalizes for speed), raw SD is useful for within-participant change over time, since the same participant's baseline speed stays roughly constant.`}
                    formula="SD = square root of the average squared difference from the mean"
                  />
                  <SmallStatCard
                    label="Fatigue Index"
                    value={`${Number(analysisStats.fatigueIndex) >= 0 ? "+" : ""}${analysisStats.fatigueIndex}%`}
                    description={`The difference in accuracy between the first and second half of the session. ${Number(analysisStats.fatigueIndex) > 5 ? "A positive value means accuracy dropped later in the session. In research, this pattern is interpreted as mental fatigue or resource depletion, common in sustained cognitive work." : Number(analysisStats.fatigueIndex) < -5 ? "A negative value means the participant got more accurate over time. This is a practice effect or warm-up, where the participant improved as they became familiar with the tasks." : "The value is close to zero, meaning performance was stable across the session."} For researchers: compare fatigue index across protocol conditions to measure which task combinations are more draining.`}
                    formula="Fatigue Index = first-half accuracy minus second-half accuracy"
                  />
                  <SmallStatCard
                    label="Response Time Skewness"
                    value={analysisStats.skewness}
                    description={`Measures whether response times are symmetrically distributed or pulled toward one tail. ${Number(analysisStats.skewness) > 1 ? "A positive skew above 1.0 means a cluster of unusually slow trials pulled the distribution right. In research, right-skewed distributions are typical under cognitive stress or during attention lapses." : Number(analysisStats.skewness) < -0.5 ? "Negative skew means most responses were slow but a few were unusually fast, which is uncommon and may indicate anticipatory responses or guessing." : "Near-zero skewness means response times were spread fairly evenly around the center."} For researchers: high positive skewness can indicate a different cognitive process than simple slowing (e.g., intermittent attentional failures rather than global cognitive load).`}
                    formula="Skewness = mean of ((each time - mean) / SD) cubed"
                  />
                  <SmallStatCard
                    label="10th Percentile Response Time"
                    value={`${analysisStats.p10} ms`}
                    description={`The fastest 10% of responses were below this value. This represents the participant's best-case processing speed when everything went well: no hesitation, no confusion, and full attention. For researchers: changes in the 10th percentile across conditions reveal whether the baseline processing speed itself is affected, rather than just occasional slow trials.`}
                    formula="Sort all times and read off the value at the 10th percentile position"
                  />
                  <SmallStatCard
                    label="90th Percentile Response Time"
                    value={`${analysisStats.p90} ms`}
                    description={`90% of responses were faster than this value. ${Number(analysisStats.p90) > Number(analysisStats.median) * 2 ? "This is more than double the median, pointing to occasional very slow responses, which typically reflect moments of confusion, distraction, or cognitive overload." : "This is not far from the median, suggesting few extreme slow-downs."} For researchers: the gap between the 10th and 90th percentile (the interdecile range) is a robust measure of response time variability that is less affected by extreme outliers than standard deviation.`}
                    formula="Sort all times and read off the value at the 90th percentile position"
                  />
                  {seqEffects && (
                    <>
                      <SmallStatCard
                        label="Post-Correct Response Time"
                        value={`${seqEffects.postCorrect} ms`}
                        description={`Average response time on ${seqEffects.nCorrect} trials that immediately followed a correct answer. This serves as the participant's "cruising speed" when things are going well. For researchers: post-correct RT is the baseline against which post-error slowing is measured. If this value is already very high, the participant was slow regardless of recent outcomes.`}
                        formula="Average of all response times where the previous trial was correct"
                      />
                      <SmallStatCard
                        label="Post-Error Response Time"
                        value={`${seqEffects.postError} ms`}
                        description={`Average response time on ${seqEffects.nError} trials that immediately followed an error. ${seqEffects.postError > seqEffects.postCorrect ? `${seqEffects.postError - seqEffects.postCorrect} ms slower than after a correct answer. This "post-error slowing" is a well-documented phenomenon reflecting cognitive control: the brain detects the mistake and shifts toward more careful processing on the next trial. It is generally considered a healthy, adaptive response.` : `Similar speed to post-correct trials across ${seqEffects.nError} trials, suggesting the participant did not adjust strategy after errors.`} For researchers: absence of post-error slowing can indicate impaired error monitoring, which is observed in some clinical populations and under extreme cognitive load.`}
                        formula="Average of all response times where the previous trial was incorrect"
                      />
                    </>
                  )}
                </div>
              )}
              <div className="grid gap-6 lg:grid-cols-2">
                {/* RT Distribution */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Response Time Distribution</CardTitle>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
                          How your response times are spread across ranges. A tall bar on the left means most answers were fast. Bars on the right mean some answers were very slow.
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={rtHistogram} margin={{ bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="rt" fontSize={10} angle={-40} textAnchor="end" interval={1} />
                        <YAxis fontSize={11} tickLine={false} />
                        <ChartTooltip />
                        <Bar dataKey="count" fill="var(--color-primary)" radius={[3, 3, 0, 0]} name="Trials" />
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                {/* Accuracy by quarter */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Accuracy by Trial Quarter</CardTitle>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
                          The session split into four equal parts. Dropping accuracy in Q3 or Q4 compared to Q1 usually indicates fatigue.
                        </TooltipContent>
                      </Tooltip>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={quartileData}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                        <XAxis dataKey="quarter" fontSize={12} />
                        <YAxis domain={[0, 100]} fontSize={12} tickLine={false} />
                        <ChartTooltip formatter={(v) => [`${v}%`, "Accuracy"]} />
                        <ReferenceLine y={50} stroke="var(--color-muted-foreground)" strokeDasharray="4 4" opacity={0.5} />
                        <Bar dataKey="accuracy" radius={[4, 4, 0, 0]} name="Accuracy (%)">
                          {quartileData.map((entry, i) => (
                            <Cell
                              key={i}
                              fill={entry.accuracy >= 70 ? "var(--color-primary)" : entry.accuracy >= 50 ? "hsl(var(--chart-2))" : "hsl(var(--destructive))"}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
                {/* Speed-accuracy scatter per paradigm */}
                {perParadigmData.length > 1 && (
                  <Card className="lg:col-span-2">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">Speed-Accuracy Trade-off by Paradigm</CardTitle>
                        <Tooltip>
                          <TooltipTrigger>
                            <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent side="top" className="max-w-[260px] text-xs leading-relaxed">
                            Each dot is a task type. Upper-left (fast and accurate) is best. Lower-right (slow and inaccurate) is worst. Fast but inaccurate may mean guessing.
                          </TooltipContent>
                        </Tooltip>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={280}>
                        <ScatterChart margin={{ top: 10, right: 30, bottom: 20, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                          <XAxis dataKey="avgRT" name="Avg Response Time (ms)" type="number" fontSize={11} label={{ value: "Avg Response Time (ms)", position: "insideBottom", offset: -10, fontSize: 11 }} />
                          <YAxis dataKey="accuracy" name="Accuracy (%)" type="number" domain={[0, 100]} fontSize={11} label={{ value: "Accuracy (%)", angle: -90, position: "insideLeft", fontSize: 11 }} />
                          <ChartTooltip
                            cursor={{ strokeDasharray: "3 3" }}
                            content={({ payload }) => {
                              if (!payload?.length) return null;
                              const d = payload[0]?.payload as { name: string; avgRT: number; accuracy: number; total: number };
                              return (
                                <div className="rounded border bg-popover px-3 py-2 text-xs shadow-md">
                                  <div className="font-medium">{d.name}</div>
                                  <div>Avg Response Time: {d.avgRT} ms</div>
                                  <div>Accuracy: {d.accuracy}%</div>
                                  <div>Trials: {d.total}</div>
                                </div>
                              );
                            }}
                          />
                          <Scatter data={perParadigmData} fill="var(--color-primary)" />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>

            <TabsContent value="trials" className="mt-4">
              <Card>
                <CardContent className="pt-6">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>#</TableHead>
                        <TableHead>Paradigm</TableHead>
                        <TableHead>Difficulty</TableHead>
                        <TableHead>Response</TableHead>
                        <TableHead>Correct</TableHead>
                        <TableHead className="text-right">Response Time (ms)</TableHead>
                        <TableHead>Result</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {summary.trials.map((t, i) => (
                        <TableRow key={t.trial_id}>
                          <TableCell className="text-muted-foreground">
                            {i + 1}
                          </TableCell>
                          <TableCell>{t.paradigm_label}</TableCell>
                          <TableCell>{t.difficulty}</TableCell>
                          <TableCell className="font-mono text-xs">
                            {t.user_response ?? "-"}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {t.correct_answer}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {t.response_time_ms.toFixed(0)}
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant={
                                t.timed_out
                                  ? "secondary"
                                  : t.is_correct
                                  ? "default"
                                  : "destructive"
                              }
                              className="text-[10px]"
                            >
                              {t.timed_out
                                ? "Timeout"
                                : t.is_correct
                                ? "Correct"
                                : "Wrong"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
          {csvFilename && (
            <NotesField
              key={csvFilename}
              filename={csvFilename}
              initialNotes={(summary as SessionSummary & { notes?: string }).notes ?? ""}
            />
          )}
        </>
      )}

      {/* Export dialog */}
      <Dialog open={exportOpen} onOpenChange={setExportOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Export Session Data</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Choose what to include in the download.
          </p>
          <div className="space-y-3 py-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={exportSummary}
                onChange={(e) => setExportSummary(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <div>
                <div className="text-sm font-medium">Summary CSV</div>
                <div className="text-xs text-muted-foreground">Overall accuracy, response times, and per-task breakdown</div>
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={exportTrials}
                onChange={(e) => setExportTrials(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <div>
                <div className="text-sm font-medium">Trial-by-trial CSV</div>
                <div className="text-xs text-muted-foreground">Every individual trial: stimulus, response, correct answer, and response time</div>
              </div>
            </label>
            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={exportAnalysis}
                onChange={(e) => setExportAnalysis(e.target.checked)}
                className="h-4 w-4 rounded border-input"
              />
              <div>
                <div className="text-sm font-medium">Analysis metrics JSON</div>
                <div className="text-xs text-muted-foreground">Median response time, variability, inverse efficiency, skewness, fatigue index, and all computed analysis values</div>
              </div>
            </label>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setExportOpen(false)}>Cancel</Button>
            <Button
              disabled={!exportSummary && !exportTrials && !exportAnalysis}
              onClick={() => {
                if (!summary) return;
                const base = `session_${summary.participant_id}_${summary.session_start.slice(0, 10)}`;
                if (exportTrials && csvFilename) {
                  downloadSessionCSV(csvFilename);
                }
                if (exportSummary) {
                  const rows = [
                    ["participant_id", "session_start", "session_end", "duration_target_sec", "intensity", "total_tasks", "correct_answers", "accuracy_pct", "avg_response_time_ms", "max_difficulty", "paradigms_used"],
                    [summary.participant_id, summary.session_start, summary.session_end, summary.duration_target_sec, summary.intensity, summary.total_tasks, summary.correct_answers, summary.accuracy_pct, summary.avg_response_time_ms, summary.max_difficulty, summary.paradigms_used.join("|")],
                  ];
                  const csv = rows.map((r) => r.join(",")).join("\n");
                  const a = document.createElement("a");
                  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
                  a.download = `${base}_summary.csv`;
                  a.click();
                }
                if (exportAnalysis) {
                  const blob = new Blob([JSON.stringify(summary, null, 2)], { type: "application/json" });
                  const a = document.createElement("a");
                  a.href = URL.createObjectURL(blob);
                  a.download = `${base}_full.json`;
                  a.click();
                }
                setExportOpen(false);
              }}
            >
              <Download className="mr-2 h-4 w-4" />
              Download
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function NotesField({ filename, initialNotes }: { filename: string; initialNotes: string }) {
  const [notes, setNotes] = useState(initialNotes);
  const [saving, setSaving] = useState(false);

  async function handleBlur() {
    setSaving(true);
    try {
      await patchSessionNotes(filename, notes);
    } catch {
      // notes are non-critical; silent fail
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Researcher Notes</CardTitle>
      </CardHeader>
      <CardContent>
        <Textarea
          placeholder="Session observations, participant notes, anomalies to flag..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleBlur}
          className="min-h-[80px] resize-none text-sm"
        />
        {saving && <p className="text-xs text-muted-foreground mt-1">Saving...</p>}
      </CardContent>
    </Card>
  );
}

function SmallStatCard({
  label,
  value,
  description,
  formula,
}: {
  label: string;
  value: string;
  description: string;
  formula?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="text-xs text-muted-foreground mb-1 flex items-center justify-between gap-1">
          <span>{label}</span>
          {formula && (
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-3 w-3 cursor-help shrink-0 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[240px] text-xs leading-relaxed">
                <span className="font-medium">Formula: </span>{formula}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
        <div className="text-2xl font-bold tabular-nums">{value}</div>
        <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{description}</p>
      </CardContent>
    </Card>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  explanation,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  explanation?: string;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
          {label}
          {explanation && (
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-3 w-3 cursor-help shrink-0" aria-label="Explain metric" />
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-[220px] text-xs leading-relaxed">
                {explanation}
              </TooltipContent>
            </Tooltip>
          )}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold tabular-nums">{value}</div>
      </CardContent>
    </Card>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-muted-foreground">Loading...</div>}>
      <ResultsContent />
    </Suspense>
  );
}
