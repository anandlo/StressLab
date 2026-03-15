import time
import random
from datetime import datetime
from .models import (
    SessionConfig, SessionState, SessionSummary, Trial, TrialResult,
    Intensity, INTENSITY_PARAMS, EVAL_FEEDBACK,
)
from .paradigms import PARADIGM_REGISTRY
from .paradigms.base import BaseParadigm


class SessionManager:
    def __init__(self, config: SessionConfig):
        self.config = config
        self.state = SessionState.IDLE
        available_ids = [pid for pid in config.paradigm_ids if pid in PARADIGM_REGISTRY]
        if not available_ids:
            available_ids = list(PARADIGM_REGISTRY.keys())
        self.paradigm_ids = available_ids
        self.paradigms: dict[str, BaseParadigm] = {}
        for pid in self.paradigm_ids:
            paradigm = PARADIGM_REGISTRY[pid]
            paradigm.reset()
            self.paradigms[pid] = paradigm
        self.task_count = 0
        self.correct_count = 0
        self.difficulty = max(1, config.starting_difficulty)
        self.consecutive_wrong = 0
        self.current_block = 0
        self.tasks_in_block = 0
        self.trials: list[TrialResult] = []
        self.start_time: float | None = None
        self.current_trial: Trial | None = None
        self._intensity = INTENSITY_PARAMS[config.intensity]
        self._deck: list[str] = []

    def start(self):
        self.state = SessionState.RUNNING
        self.start_time = time.time()

    def elapsed_sec(self) -> float:
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def is_time_up(self) -> bool:
        return self.elapsed_sec() >= self.config.duration_min * 60

    def should_rest(self) -> bool:
        if self.config.blocks <= 1:
            return False
        target_per_block = max(5, int(
            (self.config.duration_min * 60) / (self.config.blocks * 6)))
        return (self.tasks_in_block >= target_per_block and
                self.current_block < self.config.blocks - 1)

    def begin_rest(self):
        self.state = SessionState.REST

    def end_rest(self):
        self.current_block += 1
        self.tasks_in_block = 0
        self.state = SessionState.RUNNING

    def next_trial(self) -> Trial | None:
        if self.is_time_up():
            self.state = SessionState.COMPLETE
            return None
        if self.should_rest():
            return None
        self.difficulty = min(
            self._intensity["diff_cap"],
            self.config.starting_difficulty + self.correct_count // 5)
        # Shuffled-deck rotation: every paradigm appears once per cycle before
        # any paradigm repeats. With one paradigm selected this has no effect.
        if not self._deck:
            self._deck = list(self.paradigm_ids)
            random.shuffle(self._deck)
        pid = self._deck.pop(0)
        paradigm = self.paradigms[pid]
        base_time = paradigm.meta.base_time_sec
        time_limit = max(3.0, base_time * self._intensity["time_mult"]
                         - (self.difficulty - 1) * 1.5)
        trial = paradigm.generate_trial(self.difficulty, time_limit)
        self.current_trial = trial
        self.tasks_in_block += 1
        return trial

    def submit_answer(self, trial_id: str, response: str | None,
                      response_time_ms: float, timed_out: bool = False) -> TrialResult:
        trial = self.current_trial
        if trial is None or trial.trial_id != trial_id:
            raise ValueError(f"Trial {trial_id} not found or already submitted")
        paradigm = self.paradigms[trial.paradigm_id]
        if timed_out or response is None:
            is_correct = trial.correct_answer.upper() in ("NOGO", "DONE") if timed_out else False
        else:
            is_correct = paradigm.check_answer(trial, response)
        self.task_count += 1
        if is_correct:
            self.correct_count += 1
            self.consecutive_wrong = 0
        else:
            self.consecutive_wrong += 1
        result = TrialResult(
            trial_id=trial_id,
            paradigm_id=trial.paradigm_id,
            paradigm_label=trial.paradigm_label,
            difficulty=trial.difficulty,
            time_limit_sec=trial.time_limit_sec,
            correct_answer=trial.correct_answer,
            user_response=response,
            is_correct=is_correct,
            timed_out=timed_out,
            response_time_ms=response_time_ms,
            timestamp=datetime.now().isoformat(),
            elapsed_sec=self.elapsed_sec(),
        )
        self.trials.append(result)
        self.current_trial = None
        return result

    def get_feedback(self) -> str | None:
        # Disabled -- stress messages are only used within MIST paradigm now
        return None

    def get_score(self) -> dict:
        return {
            "correct": self.correct_count,
            "total": self.task_count,
            "difficulty": self.difficulty,
            "block": self.current_block + 1,
            "total_blocks": self.config.blocks,
            "elapsed_sec": round(self.elapsed_sec(), 1),
        }

    def get_summary(self) -> SessionSummary:
        self.state = SessionState.COMPLETE
        per_paradigm: dict[str, dict] = {}
        # Map paradigm_label -> paradigm_id for metric_focus lookup
        label_to_id: dict[str, str] = {}
        for t in self.trials:
            label_to_id.setdefault(t.paradigm_label, t.paradigm_id)
            entry = per_paradigm.setdefault(t.paradigm_label, {
                "total": 0, "correct": 0, "_total_rt_ms": 0.0,
                "_rts": [], "_timeouts": 0})
            entry["total"] += 1
            if t.is_correct:
                entry["correct"] += 1
            if t.timed_out:
                entry["_timeouts"] += 1
            entry["_total_rt_ms"] += t.response_time_ms
            if not t.timed_out:
                entry["_rts"].append(t.response_time_ms)
        for label, v in per_paradigm.items():
            v["accuracy_pct"] = round(100 * v["correct"] / v["total"], 1) if v["total"] else 0
            v["avg_response_time_ms"] = round(v["_total_rt_ms"] / v["total"], 1) if v["total"] else 0
            # Add metric_focus from paradigm registry
            pid = label_to_id.get(label, "")
            paradigm = self.paradigms.get(pid)
            focus = paradigm.meta.metric_focus if paradigm else "mixed"
            v["metric_focus"] = focus
            # Compute focus-specific metrics
            rts = v["_rts"]
            if focus == "speed" and rts:
                v["median_rt_ms"] = round(sorted(rts)[len(rts) // 2], 1)
                v["lapse_rate"] = round(100 * v["_timeouts"] / v["total"], 1)
            elif focus == "inhibition":
                # Commission errors = incorrect responses (pressed when should not)
                v["commission_errors"] = v["total"] - v["correct"] - v["_timeouts"]
                v["timeout_rate"] = round(100 * v["_timeouts"] / v["total"], 1)
            del v["_total_rt_ms"]
            del v["_rts"]
            del v["_timeouts"]
        rts = [t.response_time_ms for t in self.trials if not t.timed_out]
        return SessionSummary(
            participant_id=self.config.participant_id,
            session_start=self.trials[0].timestamp if self.trials else datetime.now().isoformat(),
            session_end=datetime.now().isoformat(),
            duration_target_sec=int(self.config.duration_min * 60),
            intensity=self.config.intensity.value,
            paradigms_used=self.paradigm_ids,
            total_tasks=self.task_count,
            correct_answers=self.correct_count,
            accuracy_pct=round(100 * self.correct_count / self.task_count, 1) if self.task_count else 0,
            max_difficulty=max((t.difficulty for t in self.trials), default=1),
            avg_response_time_ms=round(sum(rts) / len(rts), 1) if rts else 0,
            per_paradigm=per_paradigm,
            trials=self.trials,
        )

    def generate_practice_trials(self) -> list[Trial]:
        practice = []
        for pid in self.paradigm_ids:
            paradigm = self.paradigms[pid]
            for _ in range(self.config.practice_trials_per_paradigm):
                trial = paradigm.generate_trial(difficulty=1, time_limit=999)
                practice.append(trial)
        return practice
