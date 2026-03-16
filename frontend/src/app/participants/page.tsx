"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Search, User, ChevronRight, X, Trash2, Play } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useParticipants, useSessions } from "@/hooks/use-queries";
import { createParticipant, deleteParticipant, getFieldTemplates, saveFieldTemplates } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { Participant } from "@/lib/types";
import { useAuth } from "@/lib/auth";

export default function ParticipantsPage() {
  const { data: participants, isLoading } = useParticipants();
  const { token } = useAuth();
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedParticipant, setSelectedParticipant] =
    useState<Participant | null>(null);
  const queryClient = useQueryClient();

  // Create form state
  const [formId, setFormId] = useState("");
  const [formName, setFormName] = useState("");
  const [formAge, setFormAge] = useState("");
  const [formGender, setFormGender] = useState("");
  const [formHandedness, setFormHandedness] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [customFields, setCustomFields] = useState<{ key: string; value: string }[]>([]);
  const [creating, setCreating] = useState(false);

  // Load the user's saved field templates when the dialog opens
  function openDialog() {
    setDialogOpen(true);
    if (token) {
      getFieldTemplates(token)
        .then(({ templates }) => {
          if (templates.length > 0) {
            setCustomFields(templates.map((key) => ({ key, value: "" })));
          }
        })
        .catch(() => {/* not logged in or request failed */});
    }
  }

  function closeDialog() {
    setDialogOpen(false);
    setFormId("");
    setFormName("");
    setFormAge("");
    setFormGender("");
    setFormHandedness("");
    setFormNotes("");
    setCustomFields([]);
  }

  const filtered = (participants ?? []).filter((p) =>
    p.id.toLowerCase().includes(search.toLowerCase())
  );

  async function handleCreate() {
    if (!formId.trim()) return;
    setCreating(true);
    try {
      const demographics: Record<string, string | number | null> = {};
      if (formName) demographics.name = formName;
      if (formAge) demographics.age = parseInt(formAge, 10);
      if (formGender) demographics.gender = formGender;
      if (formHandedness) demographics.handedness = formHandedness;
      if (formNotes) demographics.notes = formNotes;
      for (const field of customFields) {
        if (field.key.trim() && field.value.trim()) {
          demographics[field.key.trim()] = field.value.trim();
        }
      }

      await createParticipant(formId.trim(), demographics);
      await queryClient.invalidateQueries({ queryKey: ["participants"] });
      toast.success(`Participant ${formId.trim()} created`);
      closeDialog();
    } catch (err) {
      toast.error(
        `Failed to create participant: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Participants</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage participant profiles and demographics
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(o) => { if (o) openDialog(); else closeDialog(); }}>
          <DialogTrigger
            render={<Button><Plus className="mr-2 h-4 w-4" />Add Participant</Button>}
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Participant</DialogTitle>
              <DialogDescription>
                Create a new participant profile for the study.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="pid">Participant ID</Label>
                  <Input
                    id="pid"
                    placeholder="e.g. P001"
                    value={formId}
                    onChange={(e) => setFormId(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    placeholder="Full name"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="age">Age</Label>
                  <Input
                    id="age"
                    type="number"
                    placeholder="25"
                    value={formAge}
                    onChange={(e) => setFormAge(e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="gender">Gender</Label>
                  <Select value={formGender} onValueChange={(v) => setFormGender(v ?? "")}>
                    <SelectTrigger id="gender">
                      <SelectValue placeholder="Select" />
                    </SelectTrigger>
                    <SelectContent alignItemWithTrigger={false} sideOffset={4}>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="non-binary">Non-binary</SelectItem>
                      <SelectItem value="prefer-not-to-say">
                        Prefer not to say
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="handedness">Handedness</Label>
                <Select
                  value={formHandedness}
                  onValueChange={(v) => setFormHandedness(v ?? "")}
                >
                  <SelectTrigger id="handedness">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent alignItemWithTrigger={false} sideOffset={4}>
                    <SelectItem value="right">Right</SelectItem>
                    <SelectItem value="left">Left</SelectItem>
                    <SelectItem value="ambidextrous">Ambidextrous</SelectItem>
                    <SelectItem value="prefer-not-to-say">Prefer not to say</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  placeholder="Optional notes..."
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                />
              </div>

              <Separator />

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-sm">Custom Fields</Label>
                    {token && (
                      <p className="text-[10px] text-muted-foreground/70 mt-0.5">
                        Field names with a star are saved to your account
                      </p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setCustomFields([...customFields, { key: "", value: "" }])}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Add Field
                  </Button>
                </div>
                {customFields.map((field, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      placeholder="Field name"
                      value={field.key}
                      onChange={(e) => {
                        const updated = [...customFields];
                        updated[i] = { ...updated[i], key: e.target.value };
                        setCustomFields(updated);
                      }}
                      className="flex-1"
                    />
                    <Input
                      placeholder="Value"
                      value={field.value}
                      onChange={(e) => {
                        const updated = [...customFields];
                        updated[i] = { ...updated[i], value: e.target.value };
                        setCustomFields(updated);
                      }}
                      className="flex-1"
                    />
                    {token && field.key.trim() && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        title="Save field name to your account"
                        onClick={() => {
                          if (token) {
                            getFieldTemplates(token).then(({ templates }) => {
                              const updated = [...new Set([...templates, field.key.trim()])];
                              return saveFieldTemplates(token, updated);
                            }).then(() => toast.success(`"${field.key.trim()}" saved to your templates`))
                              .catch(() => toast.error("Could not save template"));
                          }
                        }}
                        className="shrink-0 text-muted-foreground hover:text-foreground"
                      >
                        ★
                      </Button>
                    )}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setCustomFields(customFields.filter((_, j) => j !== i))}
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {customFields.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    Add custom demographic fields (e.g., education level, occupation).
                    {token && " Sign in to save field names to your account so they auto-populate next time."}
                  </p>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={closeDialog}
              >
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating || !formId.trim()}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search participants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <Badge variant="secondary">{filtered.length} total</Badge>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground py-12 text-center">
          Loading participants...
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <User className="mx-auto h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-muted-foreground">
              {search
                ? "No participants match your search."
                : "No participants yet. Add one to get started."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Age</TableHead>
                  <TableHead>Gender</TableHead>
                  <TableHead>Handedness</TableHead>
                  <TableHead className="text-right">Sessions</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((p) => (
                  <TableRow
                    key={p.id}
                    className="cursor-pointer"
                    onClick={() => setSelectedParticipant(p)}
                  >
                    <TableCell className="font-medium">{p.id}</TableCell>
                    <TableCell>
                      {(p.demographics?.name as string) ?? "--"}
                    </TableCell>
                    <TableCell>
                      {p.demographics?.age ?? "-"}
                    </TableCell>
                    <TableCell className="capitalize">
                      {(p.demographics?.gender as string) ?? "-"}
                    </TableCell>
                    <TableCell className="capitalize">
                      {(p.demographics?.handedness as string) ?? "-"}
                    </TableCell>
                    <TableCell className="text-right">
                      {p.session_files?.length ?? 0}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(p.created).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <ChevronRight className="h-4 w-4 text-muted-foreground" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </motion.div>
      )}

      <ParticipantDetailSheet
        participant={selectedParticipant}
        onClose={() => setSelectedParticipant(null)}
      />
    </div>
  );
}

function ParticipantDetailSheet({
  participant,
  onClose,
}: {
  participant: Participant | null;
  onClose: () => void;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const { data: sessions } = useSessions(token, participant?.id);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete() {
    if (!participant) return;
    setDeleting(true);
    try {
      await deleteParticipant(participant.id);
      await queryClient.invalidateQueries({ queryKey: ["participants"] });
      toast.success(`Participant ${participant.id} deleted`);
      setConfirmDelete(false);
      onClose();
    } catch (err) {
      toast.error(`Failed to delete: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Sheet open={!!participant} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Participant {participant?.id}</SheetTitle>
          <SheetDescription>
            Created {participant ? new Date(participant.created).toLocaleDateString() : ""}
          </SheetDescription>
        </SheetHeader>
        {participant && (
          <div className="mt-4 space-y-6">
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => { onClose(); router.push(`/protocol?participant=${encodeURIComponent(participant.id)}`); }}
              >
                <Play className="h-3.5 w-3.5 mr-1.5" />
                Start Session
              </Button>
              {confirmDelete ? (
                <div className="flex items-center gap-1.5 ml-auto">
                  <span className="text-xs text-destructive">Delete this participant?</span>
                  <Button size="sm" variant="destructive" onClick={handleDelete} disabled={deleting}>
                    {deleting ? "Deleting..." : "Confirm"}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(false)}>Cancel</Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  variant="ghost"
                  className="ml-auto text-muted-foreground hover:text-destructive"
                  onClick={() => setConfirmDelete(true)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
            <div>
              <h3 className="text-sm font-medium mb-2">Demographics</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Name:</span>{" "}
                  {(participant.demographics?.name as string) ?? "--"}
                </div>
                <div>
                  <span className="text-muted-foreground">Age:</span>{" "}
                  {participant.demographics?.age ?? "--"}
                </div>
                <div>
                  <span className="text-muted-foreground">Gender:</span>{" "}
                  <span className="capitalize">
                    {(participant.demographics?.gender as string) ?? "--"}
                  </span>
                </div>
                <div>
                  <span className="text-muted-foreground">Handedness:</span>{" "}
                  <span className="capitalize">
                    {(participant.demographics?.handedness as string) ?? "--"}
                  </span>
                </div>
                {Object.entries(participant.demographics ?? {})
                  .filter(([k]) => !["name", "age", "gender", "handedness", "notes"].includes(k))
                  .map(([k, v]) => (
                    <div key={k}>
                      <span className="text-muted-foreground capitalize">{k}:</span>{" "}
                      {String(v ?? "--")}
                    </div>
                  ))
                }
              </div>
              {participant.demographics?.notes && (
                <p className="text-sm text-muted-foreground mt-2">
                  {participant.demographics.notes as string}
                </p>
              )}
            </div>

            <div>
              <h3 className="text-sm font-medium mb-2">
                Session History ({sessions?.length ?? 0})
              </h3>
              {(sessions ?? []).length === 0 ? (
                <p className="text-sm text-muted-foreground">No sessions.</p>
              ) : (
                <div className="space-y-2">
                  {sessions!.map((s) => (
                    <div
                      key={s.filename}
                      className="flex items-center justify-between rounded-md border px-3 py-2 text-sm cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => { onClose(); router.push(`/results?session=${encodeURIComponent(s.filename)}`); }}
                    >
                      <div>
                        <div className="font-medium">
                          {new Date(s.session_start).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {s.total_tasks} tasks &middot;{" "}
                          {s.accuracy_pct.toFixed(1)}% accuracy
                        </div>
                      </div>
                      <Badge
                        variant={
                          s.intensity === "high"
                            ? "destructive"
                            : s.intensity === "medium"
                            ? "default"
                            : "secondary"
                        }
                      >
                        {s.intensity}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
