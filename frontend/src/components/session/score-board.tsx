"use client";

import { Activity, Target, Layers, Clock } from "lucide-react";
import type { SessionScore } from "@/lib/types";

export function ScoreBoard({ score }: { score: SessionScore }) {
  const accuracy =
    score.total > 0 ? ((score.correct / score.total) * 100).toFixed(0) : "-";

  return (
    <div className="grid grid-cols-4 gap-4 text-center rounded-lg border bg-card p-4">
      <div className="space-y-1">
        <Target className="h-5 w-5 mx-auto text-muted-foreground" />
        <div className="text-xl font-bold tabular-nums">{accuracy}%</div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">
          Accuracy
        </div>
      </div>
      <div className="space-y-1">
        <Activity className="h-5 w-5 mx-auto text-muted-foreground" />
        <div className="text-xl font-bold tabular-nums">
          {score.correct}/{score.total}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">
          Score
        </div>
      </div>
      <div className="space-y-1">
        <Layers className="h-5 w-5 mx-auto text-muted-foreground" />
        <div className="text-xl font-bold tabular-nums">
          {score.block}/{score.total_blocks}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">
          Block
        </div>
      </div>
      <div className="space-y-1">
        <Clock className="h-5 w-5 mx-auto text-muted-foreground" />
        <div className="text-xl font-bold tabular-nums">
          {Math.floor(score.elapsed_sec / 60)}:
          {String(Math.floor(score.elapsed_sec % 60)).padStart(2, "0")}
        </div>
        <div className="text-xs text-muted-foreground uppercase tracking-wider">
          Elapsed
        </div>
      </div>
    </div>
  );
}
