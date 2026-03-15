"use client";

import { motion } from "framer-motion";
import { CircularTimer } from "./circular-timer";

interface RestScreenProps {
  durationSec: number;
  block: number;
  totalBlocks: number;
  onComplete: () => void;
}

export function RestScreen({
  durationSec,
  block,
  totalBlocks,
  onComplete,
}: RestScreenProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-16 gap-6"
    >
      <div className="text-lg font-medium">Rest Period</div>
      <p className="text-sm text-muted-foreground">
        Block {block} of {totalBlocks} complete. Take a moment to relax.
      </p>

      <CircularTimer
        durationSec={durationSec}
        onTimeout={onComplete}
        running={true}
        size={120}
      />

      <p className="text-xs text-muted-foreground animate-pulse">
        Breathe slowly and steadily
      </p>
    </motion.div>
  );
}
