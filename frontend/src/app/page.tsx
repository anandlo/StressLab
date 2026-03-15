"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Activity,
  Users,
  FlaskConical,
  Clock,
  ArrowRight,
  Play,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useParticipants, useSessions, useParadigms, useProtocols } from "@/hooks/use-queries";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const router = useRouter();
  const { data: participants } = useParticipants();
  const { data: sessions } = useSessions();
  const { data: paradigms } = useParadigms();
  const { data: protocols } = useProtocols();

  const stats = [
    { label: "Total Sessions", value: sessions?.length ?? 0, icon: Activity },
    { label: "Participants", value: participants?.length ?? 0, icon: Users },
    { label: "Paradigms Available", value: paradigms?.length ?? 0, icon: FlaskConical },
    { label: "Protocols", value: protocols?.length ?? 0, icon: Clock },
  ];

  const recentSessions = (sessions ?? []).slice(0, 8);

  return (
    <div className="space-y-8 max-w-7xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Cognitive stress induction research tool
        </p>
      </div>

      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        variants={container}
        initial="hidden"
        animate="show"
      >
        {stats.map((s) => (
          <motion.div key={s.label} variants={item}>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {s.label}
                </CardTitle>
                <s.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold tabular-nums">{s.value}</div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Recent Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            {recentSessions.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No sessions recorded yet. Start a new session to begin.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Participant</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">Tasks</TableHead>
                    <TableHead className="text-right">Accuracy</TableHead>
                    <TableHead>Intensity</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentSessions.map((s) => (
                    <TableRow
                      key={s.filename}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => router.push(`/results?session=${encodeURIComponent(s.filename)}`)}
                    >
                      <TableCell className="font-medium">
                        {s.participant_id}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(s.session_start).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">{s.total_tasks}</TableCell>
                      <TableCell className="text-right">
                        {s.accuracy_pct.toFixed(1)}%
                      </TableCell>
                      <TableCell>
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
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Start</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {(protocols ?? []).slice(0, 4).map((p) => (
              <Link key={p.id} href={`/protocol?preset=${p.id}`}>
                <Button
                  variant="outline"
                  className="w-full justify-between text-left h-auto py-3"
                >
                  <div>
                    <div className="font-medium text-sm">{p.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {p.duration_min} min &middot; {p.intensity}
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0" />
                </Button>
              </Link>
            ))}

            <Link href="/protocol">
              <Button className="w-full mt-2" size="lg">
                <Play className="mr-2 h-4 w-4" />
                New Session
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
