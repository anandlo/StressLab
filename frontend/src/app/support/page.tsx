"use client";

import { useState } from "react";
import { Mail, Coffee, MessageSquare, AlertTriangle, CheckCircle2, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PARADIGM_LIST = [
  "N-Back", "Digit Span", "Trail Making", "WCST", "Tower of London",
  "Task Switching", "Eriksen Flanker", "PVT", "CPT", "Go/No-Go",
  "Stop-Signal Task", "ANT", "Visual Search", "Stroop Color-Word",
  "Emotional Stroop", "Serial Subtraction", "Mental Arithmetic",
  "Backwards Counting", "PASAT", "MIST Adaptive", "Rapid Comparison",
  "Dual-Task", "Speech Preparation", "Cold Pressor Timer", "MAST Protocol",
  "Mental Rotation", "Simon Task", "Pattern Completion",
  "Other / General",
];

const ISSUE_TYPES = [
  { value: "task_bug", label: "Task not displaying correctly" },
  { value: "scoring_error", label: "Scoring or answer logic error" },
  { value: "timing_issue", label: "Timer or timing problem" },
  { value: "ux_feedback", label: "Usability or design feedback" },
  { value: "feature_request", label: "Feature request" },
  { value: "data_concern", label: "Data quality or validity concern" },
  { value: "other", label: "Other" },
];

type Severity = "low" | "medium" | "high";

export default function SupportPage() {
  const [paradigm, setParadigm] = useState("");
  const [issueType, setIssueType] = useState("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [summary, setSummary] = useState("");
  const [detail, setDetail] = useState("");
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!issueType || !summary.trim()) return;
    setSubmitting(true);
    try {
      // Build a mailto link as a professional fallback.
      // In production this can be wired to a backend endpoint or Formspree.
      const subject = encodeURIComponent(
        `[StressLab] ${ISSUE_TYPES.find((t) => t.value === issueType)?.label ?? issueType}` +
          (paradigm ? `, ${paradigm}` : "")
      );
      const body = encodeURIComponent(
        [
          `Paradigm: ${paradigm || "N/A"}`,
          `Issue type: ${ISSUE_TYPES.find((t) => t.value === issueType)?.label ?? issueType}`,
          `Severity: ${severity || "not specified"}`,
          `Reply-to: ${email || "not provided"}`,
          "",
          "Summary:",
          summary,
          "",
          "Details:",
          detail,
        ].join("\n")
      );
      window.open(
        `mailto:anandlo@dal.ca?subject=${subject}&body=${body}`,
        "_blank"
      );
      setSubmitted(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Support</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Contact the developer or report an issue with a test
        </p>
      </div>

      {/* Contact + BMC */}
      <div className="grid sm:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Mail className="h-4 w-4 text-muted-foreground" />
              Contact
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              For research collaborations, dataset access, or general
              enquiries, reach out directly.
            </p>
            <a
              href="mailto:anandlo@dal.ca"
              className="inline-flex items-center gap-1.5 text-foreground font-medium hover:underline underline-offset-2"
            >
              <Mail className="h-3.5 w-3.5" />
              anandlo@dal.ca
              <ExternalLink className="h-3 w-3 opacity-50" />
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Coffee className="h-4 w-4 text-muted-foreground" />
              Support development
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              StressLab is developed and maintained independently. If it
              saves you time in your research, consider supporting its
              continued development.
            </p>
            <a
              href="https://buymeacoffee.com/anandlo"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-foreground font-medium hover:underline underline-offset-2"
            >
              <Coffee className="h-3.5 w-3.5" />
              Buy me a coffee
              <ExternalLink className="h-3 w-3 opacity-50" />
            </a>
          </CardContent>
        </Card>
      </div>

      {/* Feedback form */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold">Report an issue or concern</h2>
        </div>

        {submitted ? (
          <Card>
            <CardContent className="py-10 flex flex-col items-center gap-3 text-center">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
              <p className="font-medium">Report submitted</p>
              <p className="text-sm text-muted-foreground">
                Your default email client should have opened with the report
                pre-filled. If it did not open, copy the details and send
                them manually.
              </p>
              <Button variant="outline" size="sm" onClick={() => setSubmitted(false)}>
                Submit another report
              </Button>
            </CardContent>
          </Card>
        ) : (
          <form onSubmit={handleSubmit}>
            <Card>
              <CardContent className="py-6 space-y-5">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="paradigm">Affected paradigm</Label>
                    <Select value={paradigm} onValueChange={(v) => setParadigm(v ?? "")}>
                      <SelectTrigger id="paradigm">
                        <SelectValue placeholder="Select a paradigm" />
                      </SelectTrigger>
                      <SelectContent>
                        {PARADIGM_LIST.map((p) => (
                          <SelectItem key={p} value={p}>{p}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="issue-type">Issue type</Label>
                    <Select value={issueType} onValueChange={(v) => setIssueType(v ?? "")}>
                      <SelectTrigger id="issue-type">
                        <SelectValue placeholder="Select issue type" />
                      </SelectTrigger>
                      <SelectContent>
                        {ISSUE_TYPES.map((t) => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label>Severity</Label>
                  <div className="flex gap-2">
                    {(["low", "medium", "high"] as Severity[]).map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => setSeverity(severity === s ? "" : s)}
                        className="focus:outline-none"
                      >
                        <Badge
                          variant={severity === s ? "default" : "outline"}
                          className={`cursor-pointer capitalize ${
                            s === "high" && severity === s
                              ? "bg-destructive text-destructive-foreground hover:bg-destructive"
                              : s === "medium" && severity === s
                              ? "bg-amber-500 text-white hover:bg-amber-500"
                              : ""
                          }`}
                        >
                          {s === "high" && <AlertTriangle className="h-3 w-3 mr-1" />}
                          {s}
                        </Badge>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="summary">
                    Summary <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="summary"
                    placeholder="Brief description of the issue"
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="detail">Details</Label>
                  <Textarea
                    id="detail"
                    placeholder="Steps to reproduce, expected behaviour, actual behaviour, screenshots..."
                    value={detail}
                    onChange={(e) => setDetail(e.target.value)}
                    rows={4}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="reply-email">Your email (optional)</Label>
                  <Input
                    id="reply-email"
                    type="email"
                    placeholder="for follow-up replies"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <Button
                  type="submit"
                  disabled={submitting || !issueType || !summary.trim()}
                >
                  {submitting ? "Opening email client..." : "Submit report"}
                </Button>
                <p className="text-[11px] text-muted-foreground">
                  This will open your email client with the report pre-filled.
                  No data is sent automatically.
                </p>
              </CardContent>
            </Card>
          </form>
        )}
      </div>
    </div>
  );
}
