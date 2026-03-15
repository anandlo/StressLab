"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import type { Trial } from "@/lib/types";
import { InputMode } from "@/lib/types";

interface ResponseInputProps {
  trial: Trial;
  onSubmit: (response: string) => void;
  disabled: boolean;
}

export function ResponseInput({ trial, onSubmit, disabled }: ResponseInputProps) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setText("");
    if (
      trial.input_mode === InputMode.TEXT &&
      inputRef.current
    ) {
      inputRef.current.focus();
    }
  }, [trial.trial_id, trial.input_mode]);

  const kbOptions = trial.stimulus.keyboard_options as
    | { key: string; label: string }[]
    | undefined;

  const handleKeyboard = useCallback(
    (e: KeyboardEvent) => {
      if (disabled) return;

      if (trial.input_mode === InputMode.KEYBOARD) {
        // Arrow keys -- handled first for standard paradigms
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          onSubmit("LEFT");
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          onSubmit("RIGHT");
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          onSubmit("UP");
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          onSubmit("DOWN");
        } else {
          // Letter-key options (e.g. Y/N for visual search, n-back)
          const match = kbOptions?.find(
            (o) => o.key.toLowerCase() === e.key.toLowerCase()
          );
          if (match) {
            e.preventDefault();
            // Submit the first word of the label so "YES (match)" → "YES"
            onSubmit(match.label.split(" ")[0].toUpperCase());
          }
        }
      } else if (trial.input_mode === InputMode.SPACEBAR) {
        if (e.key === " " || e.code === "Space") {
          e.preventDefault();
          onSubmit("GO");
        }
      }
    },
    [trial.input_mode, kbOptions, onSubmit, disabled]
  );

  useEffect(() => {
    if (
      trial.input_mode === InputMode.KEYBOARD ||
      trial.input_mode === InputMode.SPACEBAR
    ) {
      window.addEventListener("keydown", handleKeyboard);
      return () => window.removeEventListener("keydown", handleKeyboard);
    }
  }, [trial.input_mode, handleKeyboard]);

  // Re-focus text input when it becomes enabled (after stimulus display delay)
  useEffect(() => {
    if (!disabled && trial.input_mode === InputMode.TEXT && inputRef.current) {
      inputRef.current.focus();
    }
  }, [disabled, trial.input_mode]);

  if (trial.input_mode === InputMode.NONE) {
    return (
      <Button
        onClick={() => onSubmit("DONE")}
        disabled={disabled}
        className="w-full"
      >
        Continue
      </Button>
    );
  }

  if (trial.input_mode === InputMode.SPACEBAR) {
    return (
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 rounded-lg border border-dashed px-6 py-4">
          <kbd className="rounded border bg-muted px-2 py-1 font-mono text-sm">
            SPACE
          </kbd>
          <span className="text-sm text-muted-foreground">Press to respond</span>
        </div>
      </div>
    );
  }

  if (trial.input_mode === InputMode.KEYBOARD) {
    const keyLabel = (key: string) => {
      const map: Record<string, string> = {
        ArrowLeft: "←", ArrowRight: "→", ArrowUp: "↑", ArrowDown: "↓",
      };
      return map[key] ?? key.toUpperCase();
    };
    if (kbOptions && kbOptions.length > 0) {
      return (
        <div className="text-center space-y-2">
          <div className="inline-flex flex-wrap items-center gap-4 rounded-lg border border-dashed px-6 py-4 justify-center">
            {kbOptions.map((opt) => (
              <div key={opt.key} className="flex items-center gap-1.5">
                <kbd className="rounded border bg-muted px-2 py-1 font-mono text-sm">
                  {keyLabel(opt.key)}
                </kbd>
                <span className="text-sm text-muted-foreground">{opt.label}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return (
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-4 rounded-lg border border-dashed px-6 py-4">
          <div className="flex gap-1">
            <kbd className="rounded border bg-muted px-3 py-1 font-mono text-sm">←</kbd>
            <kbd className="rounded border bg-muted px-3 py-1 font-mono text-sm">→</kbd>
          </div>
          <span className="text-sm text-muted-foreground">Arrow keys to respond</span>
        </div>
      </div>
    );
  }

  if (trial.input_mode === InputMode.CLICK) {
    const options = (trial.stimulus.options as string[]) ?? [];
    return (
      <div className="flex flex-wrap gap-2 justify-center">
        {options.map((opt) => (
          <Button
            key={opt}
            variant="outline"
            onClick={() => onSubmit(opt)}
            disabled={disabled}
          >
            {opt}
          </Button>
        ))}
      </div>
    );
  }

  // TEXT input mode
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim() && !disabled) {
          onSubmit(text.trim());
        }
      }}
      className="flex gap-2"
    >
      <Input
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type your answer..."
        disabled={disabled}
        autoComplete="off"
        className="font-mono"
      />
      <Button type="submit" disabled={disabled || !text.trim()}>
        Submit
      </Button>
    </form>
  );
}
