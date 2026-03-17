"use client";

import { useState, useMemo, useEffect, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { toast } from "sonner";
import {
  FlaskConical,
  Play,
  Clock,
  Zap,
  Layers,
  ChevronRight,
  Check,
  Info,
  Volume2,
  Save,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useParadigms, useProtocols, useParticipants } from "@/hooks/use-queries";
import { Intensity, type SoundType, type ParadigmMeta, type SessionConfig } from "@/lib/types";
import { listUserProtocols, saveUserProtocol, deleteUserProtocol, listProjects, type UserProtocolConfig } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger>
        <Info className="inline h-3 w-3 ml-1 shrink-0 text-muted-foreground cursor-help" aria-label="More information" />
      </TooltipTrigger>
      <TooltipContent className="max-w-[220px] text-xs leading-relaxed" side="top">
        {text}
      </TooltipContent>
    </Tooltip>
  );
}

const CATEGORIES = [
  "All",
  "attention",
  "memory",
  "executive",
  "arithmetic",
  "spatial",
  "adaptive",
  "social",
] as const;

function ProtocolContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const presetId = searchParams.get("preset");

  const { data: paradigms } = useParadigms();
  const { data: protocols } = useProtocols();
  const { data: participants } = useParticipants();
  const { token, user } = useAuth();

  const participantParam = searchParams.get("participant");
  const paradigmParam = searchParams.get("paradigm");
  const [mode, setMode] = useState<"preset" | "custom" | "saved">(
    paradigmParam ? "custom" : presetId ? "preset" : "preset"
  );
  const [selectedPreset, setSelectedPreset] = useState<string | null>(
    presetId
  );
  const [selectedParadigms, setSelectedParadigms] = useState<Set<string>>(
    paradigmParam ? new Set([paradigmParam]) : new Set()
  );
  const [participantId, setParticipantId] = useState(participantParam ?? "");
  const [duration, setDuration] = useState("10");
  const [intensity, setIntensity] = useState<Intensity>(Intensity.MEDIUM);
  const [blocks, setBlocks] = useState("2");
  const [restDuration, setRestDuration] = useState("30");
  const [category, setCategory] = useState("All");
  const [practiceEnabled, setPracticeEnabled] = useState(false);
  const [soundClicks, setSoundClicks] = useState(false);
  const [soundCountdown, setSoundCountdown] = useState(false);
  const [soundType, setSoundType] = useState<SoundType>("tick");

  // Session naming + project assignment
  const [sessionName, setSessionName] = useState("");
  const [autoName, setAutoName] = useState(true);
  const [projectId, setProjectId] = useState("");
  const [projects, setProjects] = useState<Array<{ id: string; name: string }>>([]);

  // User-saved protocols
  const [savedProtocols, setSavedProtocols] = useState<UserProtocolConfig[]>([]);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);

  const loadSavedProtocols = useCallback(async () => {
    if (!token) return;
    try {
      const list = await listUserProtocols(token);
      setSavedProtocols(list);
    } catch { /* ignore */ }
  }, [token]);

  useEffect(() => {
    loadSavedProtocols();
  }, [loadSavedProtocols]);

  useEffect(() => {
    if (!token) return;
    listProjects(token).then(setProjects).catch(() => {});
  }, [token]);

  const preset = protocols?.find((p) => p.id === selectedPreset);

  const filteredParadigms = useMemo(() => {
    if (!paradigms) return [];
    if (category === "All") return paradigms;
    return paradigms.filter(
      (p) => p.category.toLowerCase() === category.toLowerCase()
    );
  }, [paradigms, category]);

  function toggleParadigm(id: string) {
    setSelectedParadigms((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSaveProtocol() {
    if (!token || !saveName.trim()) return;
    setSaving(true);
    try {
      await saveUserProtocol(token, {
        name: saveName.trim(),
        mode: mode === "saved" ? "custom" : mode,
        preset_id: mode === "preset" ? selectedPreset : null,
        paradigm_ids: mode !== "preset" ? Array.from(selectedParadigms) : [],
        duration_min: parseFloat(duration),
        intensity,
        blocks: parseInt(blocks, 10),
        rest_duration_sec: parseInt(restDuration, 10),
        practice_enabled: practiceEnabled,
      });
      await loadSavedProtocols();
      setSaveDialogOpen(false);
      setSaveName("");
    } catch { /* ignore */ } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSaved(id: string) {
    if (!token) return;
    if (!confirm("Delete this saved protocol?")) return;
    try {
      await deleteUserProtocol(token, id);
      await loadSavedProtocols();
      toast.success("Protocol deleted");
    } catch { /* ignore */ }
  }

  function loadSavedProtocol(p: UserProtocolConfig) {
    if (p.mode) setMode(p.mode as "preset" | "custom");
    if (p.preset_id) setSelectedPreset(p.preset_id);
    if (p.paradigm_ids) setSelectedParadigms(new Set(p.paradigm_ids));
    if (p.duration_min) setDuration(String(p.duration_min));
    if (p.intensity) setIntensity(p.intensity as Intensity);
    if (p.blocks) setBlocks(String(p.blocks));
    if (p.rest_duration_sec !== undefined) setRestDuration(String(p.rest_duration_sec));
    if (p.practice_enabled !== undefined) setPracticeEnabled(p.practice_enabled);
  }

  function startSession() {
    const config: SessionConfig = {
      participant_id: participantId || "anonymous",
      duration_min: parseFloat(duration),
      intensity,
      sound_clicks_enabled: soundClicks,
      sound_countdown_enabled: soundCountdown,
      sound_type: soundType,
      paradigm_ids:
        mode === "preset" && preset
          ? preset.paradigm_ids
          : Array.from(selectedParadigms),
      blocks: parseInt(blocks, 10),
      rest_duration_sec: parseInt(restDuration, 10),
      practice_enabled: practiceEnabled,
      practice_trials_per_paradigm: 1,
      ...(autoName ? {} : { session_name: sessionName.trim() }),
      ...(projectId ? { project_id: projectId } : {}),
    };

    const encoded = encodeURIComponent(JSON.stringify(config));
    router.push(`/briefing?config=${encoded}`);
  }

  const paradigmCount =
    mode === "preset" && preset
      ? preset.paradigm_ids.length
      : selectedParadigms.size;

  const canStart = paradigmCount > 0;

  return (
    <div className="space-y-6 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Protocol Builder</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Configure a session protocol from presets or build your own
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Tabs
            value={mode}
            onValueChange={(v) => setMode(v as "preset" | "custom")}
          >
            <TabsList className={user ? "grid w-full grid-cols-3" : "grid w-full grid-cols-2"}>
              <TabsTrigger value="preset">Preset Protocols</TabsTrigger>
              <TabsTrigger value="custom">Custom Build</TabsTrigger>
              {user && <TabsTrigger value="saved">My Protocols</TabsTrigger>}
            </TabsList>

            <TabsContent value="preset" className="mt-4">
              <div className="grid gap-4 sm:grid-cols-2">
                {(protocols ?? []).map((p) => (
                  <Card
                    key={p.id}
                    className={`h-full cursor-pointer transition-all hover:shadow-md hover:border-primary/30 ${
                      selectedPreset === p.id
                        ? "border-primary bg-primary/5 ring-1 ring-primary"
                        : ""
                    }`}
                    onClick={() => {
                      setSelectedPreset(p.id);
                      setDuration(String(p.duration_min));
                      setIntensity(p.intensity);
                      setBlocks(String(p.blocks));
                      setRestDuration(String(p.rest_duration_sec));
                    }}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <CardTitle className="text-sm leading-tight">
                          {p.name}
                        </CardTitle>
                        {selectedPreset === p.id && (
                          <Check className="h-3 w-3 text-primary shrink-0" />
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
                        {p.description}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant="secondary" className="text-[10px]">
                          {p.duration_min} min
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          {p.intensity}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          {p.paradigm_ids.length} tasks
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          {p.blocks} {p.blocks === 1 ? "block" : "blocks"}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="custom" className="mt-4 space-y-4">
              <div className="flex gap-2 flex-wrap">
                {CATEGORIES.map((cat) => (
                  <Button
                    key={cat}
                    variant={category === cat ? "default" : "outline"}
                    size="sm"
                    onClick={() => setCategory(cat)}
                    className="capitalize"
                  >
                    {cat}
                  </Button>
                ))}
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                {filteredParadigms.map((p) => (
                  <ParadigmCard
                    key={p.id}
                    paradigm={p}
                    selected={selectedParadigms.has(p.id)}
                    onToggle={() => toggleParadigm(p.id)}
                  />
                ))}
              </div>
            </TabsContent>

            <TabsContent value="saved" className="mt-4">
              {savedProtocols.length === 0 ? (
                <div className="py-16 text-center text-sm text-muted-foreground">
                  No saved protocols yet. Build a custom protocol and click &ldquo;Save to Account&rdquo;.
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {savedProtocols.map((p) => (
                    <Card
                      key={p.id}
                      className="cursor-pointer hover:shadow-md transition-all"
                      onClick={() => { loadSavedProtocol(p); setMode(p.mode as "preset" | "custom"); }}
                    >
                      <CardHeader className="pb-1">
                        <div className="flex items-center justify-between gap-2">
                          <CardTitle className="text-sm truncate">{p.name}</CardTitle>
                          <button
                            className="text-muted-foreground hover:text-destructive shrink-0"
                            onClick={(e) => { e.stopPropagation(); handleDeleteSaved(p.id); }}
                            aria-label="Delete"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </CardHeader>
                      <CardContent className="pt-1">
                        <div className="flex gap-2 flex-wrap">
                          <Badge variant="secondary">{p.duration_min} min</Badge>
                          <Badge variant="secondary">{p.intensity}</Badge>
                          <Badge variant="secondary">{p.paradigm_ids.length} tasks</Badge>
                          <Badge variant="outline" className="capitalize">{p.mode}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1.5">
                          Saved {new Date(p.created).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Session Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="participant">Participant</Label>
                <Select
                  value={participantId}
                  onValueChange={(v) => setParticipantId(v ?? "")}
                >
                  <SelectTrigger id="participant">
                    <SelectValue placeholder="Select participant" />
                  </SelectTrigger>
                  <SelectContent>
                    {(participants ?? []).map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Session naming */}
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm">Session Name</Label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoName}
                      onChange={(e) => setAutoName(e.target.checked)}
                      className="h-3.5 w-3.5 rounded border-input"
                    />
                    <span className="text-xs text-muted-foreground">Auto</span>
                  </label>
                </div>
                {!autoName && (
                  <Input
                    placeholder="e.g. Pilot Session 3"
                    value={sessionName}
                    onChange={(e) => setSessionName(e.target.value)}
                    className="h-8 text-sm"
                  />
                )}
              </div>

              {/* Optionally assign to a project */}
              {token && projects.length > 0 && (
                <div className="grid gap-2">
                  <Label className="flex items-center text-sm">
                    Project
                    <InfoTip text="Optionally assign this session to a project. You can also attach sessions to projects later from the Projects page." />
                  </Label>
                  <Select value={projectId} onValueChange={(v) => setProjectId(v === "none" ? "" : v ?? "")}>
                    <SelectTrigger className="h-8 text-sm">
                      <SelectValue placeholder="None (assign later)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      {projects.map((p) => (
                        <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <Label htmlFor="duration" className="flex items-center">
                    <Clock className="inline h-3 w-3 mr-1" />
                    Duration (min)
                    <InfoTip text="Total session wall-clock time. The session ends automatically when this time elapses. Trials mid-flight at the cutoff are completed before the session terminates." />
                  </Label>
                  <Input
                    id="duration"
                    type="number"
                    min="1"
                    max="60"
                    value={duration}
                    onChange={(e) => setDuration(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="intensity" className="flex items-center">
                    <Zap className="inline h-3 w-3 mr-1" />
                    Intensity
                    <InfoTip text="Controls two things: time pressure and difficulty ceiling. Low = generous time limits (1.3x base), difficulty caps at 3. Medium = standard timing, difficulty caps at 5. High = tight time limits (0.75x base), difficulty caps at 7. Within a session, difficulty starts at 1 and rises by 1 for every 5 correct answers, up to the cap. So 'Low' never exceeds difficulty 3, while 'High' can reach difficulty 7." />
                  </Label>
                  <Select
                    value={intensity}
                    onValueChange={(v) => setIntensity(v as Intensity)}
                  >
                    <SelectTrigger id="intensity">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-2">
                  <Label htmlFor="blocks" className="flex items-center">
                    <Layers className="inline h-3 w-3 mr-1" />
                    Blocks
                    <InfoTip text="Number of task blocks separated by rest periods. After each block, participants take a timed break before the next block begins." />
                  </Label>
                  <Input
                    id="blocks"
                    type="number"
                    min="1"
                    max="10"
                    value={blocks}
                    onChange={(e) => setBlocks(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="rest" className="flex items-center">
                    Rest (sec)
                    <InfoTip text="Duration of the rest period between blocks in seconds. Participants see a countdown during this time." />
                  </Label>
                  <Input
                    id="rest"
                    type="number"
                    min="0"
                    max="120"
                    value={restDuration}
                    onChange={(e) => setRestDuration(e.target.value)}
                  />
                </div>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <Label htmlFor="practice" className="text-sm">
                  Practice round
                </Label>
                <input
                  id="practice"
                  type="checkbox"
                  checked={practiceEnabled}
                  onChange={(e) => setPracticeEnabled(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                />
              </div>

              <Separator />

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-sm font-medium flex items-center gap-1">
                    <Volume2 className="h-3 w-3" />
                    Sounds
                  </Label>
                  <input
                    type="checkbox"
                    checked={soundClicks && soundCountdown}
                    ref={(el) => {
                      if (el) el.indeterminate = (soundClicks || soundCountdown) && !(soundClicks && soundCountdown);
                    }}
                    onChange={(e) => {
                      setSoundClicks(e.target.checked);
                      setSoundCountdown(e.target.checked);
                    }}
                    className="h-4 w-4 rounded border-input"
                    aria-label="Toggle all sounds"
                  />
                </div>
                <div className="flex items-center justify-between pl-4">
                  <Label htmlFor="sound-clicks" className="text-sm font-normal flex items-center gap-1">
                    Per-second click
                    <InfoTip text="Plays a short sound each second while the trial timer is counting down, like a metronome. Helps with timing awareness." />
                  </Label>
                  <input
                    id="sound-clicks"
                    type="checkbox"
                    checked={soundClicks}
                    onChange={(e) => setSoundClicks(e.target.checked)}
                    className="h-4 w-4 rounded border-input"
                  />
                </div>
                <div className="flex items-center justify-between pl-4">
                  <Label htmlFor="sound-countdown" className="text-sm font-normal flex items-center gap-1">
                    Countdown warning
                    <InfoTip text="Plays escalating beeps in the last 5 seconds of each trial so you know time is almost up." />
                  </Label>
                  <input
                    id="sound-countdown"
                    type="checkbox"
                    checked={soundCountdown}
                    onChange={(e) => setSoundCountdown(e.target.checked)}
                    className="h-4 w-4 rounded border-input"
                  />
                </div>
                {soundClicks && (
                  <div className="grid gap-1 pl-4">
                    <Label className="text-xs text-muted-foreground">Click sound type</Label>
                    <Select value={soundType} onValueChange={(v) => setSoundType(v as SoundType)}>
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="tick">Tick (subtle)</SelectItem>
                        <SelectItem value="beep">Beep (moderate)</SelectItem>
                        <SelectItem value="soft">Soft tone (quiet)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              <Separator />

              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex justify-between">
                  <span>Paradigms:</span>
                  <span className="font-medium text-foreground">
                    {paradigmCount}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Duration:</span>
                  <span className="font-medium text-foreground">
                    {duration} min
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Total blocks:</span>
                  <span className="font-medium text-foreground">{blocks}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => {
                    const config = {
                      mode,
                      preset_id: mode === "preset" ? selectedPreset : null,
                      paradigm_ids: mode === "custom" ? Array.from(selectedParadigms) : [],
                      duration_min: parseFloat(duration),
                      intensity,
                      blocks: parseInt(blocks, 10),
                      rest_duration_sec: parseInt(restDuration, 10),
                      practice_enabled: practiceEnabled,
                    };
                    const blob = new Blob([JSON.stringify(config, null, 2)], { type: "application/json" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = "protocol.json";
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Export
                </Button>
                <div className="flex-1 relative">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={() => (document.getElementById("protocol-import") as HTMLInputElement)?.click()}
                  >
                    Import
                  </Button>
                  <input
                    id="protocol-import"
                    type="file"
                    accept=".json"
                    className="sr-only"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      const reader = new FileReader();
                      reader.onload = (ev) => {
                        try {
                          const cfg = JSON.parse(ev.target?.result as string);
                          if (cfg.mode) setMode(cfg.mode);
                          if (cfg.preset_id) setSelectedPreset(cfg.preset_id);
                          if (cfg.paradigm_ids) setSelectedParadigms(new Set(cfg.paradigm_ids));
                          if (cfg.duration_min) setDuration(String(cfg.duration_min));
                          if (cfg.intensity) setIntensity(cfg.intensity);
                          if (cfg.blocks) setBlocks(String(cfg.blocks));
                          if (cfg.rest_duration_sec !== undefined) setRestDuration(String(cfg.rest_duration_sec));
                          if (cfg.practice_enabled !== undefined) setPracticeEnabled(cfg.practice_enabled);
                        } catch { /* ignore malformed JSON */ }
                      };
                      reader.readAsText(file);
                      e.target.value = "";
                    }}
                  />
                </div>
              </div>
              {user && mode === "custom" && selectedParadigms.size > 0 && (
                <>
                  {saveDialogOpen ? (
                    <div className="flex gap-2">
                      <Input
                        placeholder="Protocol name…"
                        value={saveName}
                        onChange={(e) => setSaveName(e.target.value)}
                        className="h-8 text-xs"
                        onKeyDown={(e) => { if (e.key === "Enter") handleSaveProtocol(); if (e.key === "Escape") setSaveDialogOpen(false); }}
                        autoFocus
                      />
                      <Button size="sm" className="h-8 px-3" disabled={saving || !saveName.trim()} onClick={handleSaveProtocol}>
                        {saving ? "Saving…" : "Save"}
                      </Button>
                      <Button size="sm" variant="ghost" className="h-8 px-2" onClick={() => setSaveDialogOpen(false)}>
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full gap-1.5"
                      disabled={!canStart}
                      onClick={() => setSaveDialogOpen(true)}
                    >
                      <Save className="h-3.5 w-3.5" />
                      Save to Account
                    </Button>
                  )}
                </>
              )}
              <Button
                className="w-full"
                size="lg"
                disabled={!canStart}
                onClick={startSession}
              >
                {practiceEnabled ? "Start Practice" : "Start Session"}
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ParadigmCard({
  paradigm,
  selected,
  onToggle,
}: {
  paradigm: ParadigmMeta;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <motion.div
      whileTap={{ scale: 0.98 }}
      onClick={onToggle}
      className={`cursor-pointer rounded-lg border p-3 transition-all hover:shadow-sm ${
        selected ? "border-primary bg-primary/5 ring-1 ring-primary" : ""
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">
              {paradigm.label}
            </span>
            {selected && <Check className="h-3 w-3 text-primary shrink-0" />}
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
            {paradigm.reference}
          </p>
        </div>
        <Badge variant="secondary" className="ml-2 text-[10px] shrink-0 capitalize">
          {paradigm.category}
        </Badge>
      </div>
    </motion.div>
  );
}

export default function ProtocolPage() {
  return (
    <Suspense fallback={<div className="py-24 text-center text-muted-foreground">Loading...</div>}>
      <ProtocolContent />
    </Suspense>
  );
}
