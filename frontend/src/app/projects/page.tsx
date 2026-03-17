"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Plus, Trash2, Unlink, FolderOpen, Link2 } from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  listProjects,
  createProject,
  deleteProject,
  attachSessionToProject,
  detachSessionFromProject,
  listSessions,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Project, SessionListItem } from "@/lib/types";

export default function ProjectsPage() {
  const { token, user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [creating, setCreating] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [attachProjectId, setAttachProjectId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([listProjects(token ?? ""), listSessions(token ?? "")]);
      setProjects(p);
      setSessions(s);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      await createProject(token ?? "", name, newDesc.trim());
      toast.success("Project created");
      setNewName("");
      setNewDesc("");
      setDialogOpen(false);
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(projectId: string) {
    if (!confirm("Delete this project? Sessions will not be deleted.")) return;
    try {
      await deleteProject(token ?? "", projectId);
      toast.success("Project deleted");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function handleAttach(projectId: string, sessionFile: string) {
    if (!sessionFile) return;
    try {
      await attachSessionToProject(token ?? "", projectId, sessionFile);
      toast.success("Session attached");
      setAttachProjectId(null);
      setSelectedFile("");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Attach failed");
    }
  }

  async function handleDetach(projectId: string, filename: string) {
    if (!confirm("Remove this session from the project?")) return;
    try {
      await detachSessionFromProject(token ?? "", projectId, filename);
      toast.success("Session removed from project");
      await refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Detach failed");
    }
  }

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Group sessions into projects to track progress across runs.
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger>
            <Button size="sm">
              <Plus className="w-4 h-4 mr-1" />
              New project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New project</DialogTitle>
              <DialogDescription>
                Create a named project to organise related sessions.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="proj-name">Name</Label>
                <Input
                  id="proj-name"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="proj-desc">
                  Description{" "}
                  <span className="text-xs text-muted-foreground font-normal">(optional)</span>
                </Label>
                <Input
                  id="proj-desc"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={creating}>
                  {creating ? "Creating…" : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : projects.length === 0 ? (
        <Card>
          <CardContent className="pt-6 text-center text-sm text-muted-foreground">
            No projects yet. Create one above.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {projects.map((project) => {
            const attachedSet = new Set(project.session_files);
            const unattached = sessions.filter((s) => !attachedSet.has(s.filename));
            return (
              <Card key={project.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{project.name}</CardTitle>
                      {project.description && (
                        <CardDescription className="mt-0.5">{project.description}</CardDescription>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 text-muted-foreground hover:text-destructive"
                      onClick={() => handleDelete(project.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Created {new Date(project.created).toLocaleDateString()}
                  </p>
                </CardHeader>
                <CardContent className="space-y-3">
                  {project.session_files.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No sessions attached.</p>
                  ) : (
                    <ul className="space-y-1">
                      {project.session_files.map((f) => {
                        const meta = sessions.find((s) => s.filename === f);
                        return (
                          <li key={f} className="flex items-center justify-between text-xs gap-2">
                            <span className="font-mono truncate max-w-xs text-muted-foreground">{f}</span>
                            <div className="flex items-center gap-2 shrink-0">
                              {meta && (
                                <Badge variant="secondary" className="text-xs">
                                  {meta.accuracy_pct.toFixed(0)}% accuracy
                                </Badge>
                              )}
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                onClick={() => handleDetach(project.id, f)}
                              >
                                <Unlink className="w-3 h-3" />
                              </Button>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  {unattached.length > 0 && (
                    <div className="flex items-center gap-2 pt-1">
                      {attachProjectId === project.id ? (
                        <>
                          <select
                            className="flex-1 h-8 rounded-md border border-input bg-background px-2 py-1 text-xs"
                            value={selectedFile}
                            onChange={(e) => setSelectedFile(e.target.value)}
                          >
                            <option value="">Select session…</option>
                            {unattached.map((s) => (
                              <option key={s.filename} value={s.filename}>
                                {s.filename}, {new Date(s.session_start).toLocaleDateString()}
                              </option>
                            ))}
                          </select>
                          <Button
                            size="sm"
                            className="h-8 text-xs"
                            disabled={!selectedFile}
                            onClick={() => handleAttach(project.id, selectedFile)}
                          >
                            Attach
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-8 text-xs"
                            onClick={() => { setAttachProjectId(null); setSelectedFile(""); }}
                          >
                            Cancel
                          </Button>
                        </>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-8 text-xs"
                          onClick={() => { setAttachProjectId(project.id); setSelectedFile(""); }}
                        >
                          <Link2 className="w-3 h-3 mr-1" />
                          Attach session
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
