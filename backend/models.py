from pydantic import BaseModel
from enum import Enum
from typing import Optional


class InputMode(str, Enum):
    TEXT = "text"
    KEYBOARD = "keyboard"
    SPACEBAR = "spacebar"
    CLICK = "click"
    NONE = "none"


class StimulusType(str, Enum):
    TEXT = "text"
    STROOP = "stroop"
    ARROWS = "arrows"
    SHAPE = "shape"
    SEQUENCE = "sequence"
    CARDS = "cards"
    GRID = "grid"
    TIMER_ONLY = "timer_only"
    LETTER_STREAM = "letter_stream"
    DUAL = "dual"


class Intensity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SessionState(str, Enum):
    IDLE = "idle"
    PRACTICE = "practice"
    RUNNING = "running"
    REST = "rest"
    PAUSED = "paused"
    COMPLETE = "complete"


INTENSITY_PARAMS = {
    Intensity.LOW: {"time_mult": 1.3, "diff_cap": 3, "fb_thresh": 4},
    Intensity.MEDIUM: {"time_mult": 1.0, "diff_cap": 5, "fb_thresh": 2},
    Intensity.HIGH: {"time_mult": 0.75, "diff_cap": 7, "fb_thresh": 1},
}

# Evaluative feedback disabled -- the fake stress messages were distracting
# and confusing for participants outside the MIST paradigm.
EVAL_FEEDBACK: list[str] = []


class ParadigmMeta(BaseModel):
    id: str
    label: str
    reference: str
    description: str
    input_mode: InputMode
    stimulus_type: StimulusType
    base_time_sec: int
    category: str
    # Primary metric focus for analysis: "speed", "accuracy", "inhibition", or "mixed"
    metric_focus: str = "mixed"


class Trial(BaseModel):
    trial_id: str
    paradigm_id: str
    paradigm_label: str
    difficulty: int
    time_limit_sec: float
    stimulus_type: StimulusType
    input_mode: InputMode
    stimulus: dict
    correct_answer: str
    instruction: str
    explanation: str = ""


class TrialResult(BaseModel):
    trial_id: str
    paradigm_id: str
    paradigm_label: str
    difficulty: int
    time_limit_sec: float
    correct_answer: str
    user_response: Optional[str] = None
    is_correct: bool
    timed_out: bool
    response_time_ms: float
    timestamp: str
    elapsed_sec: float = 0.0


class SessionConfig(BaseModel):
    participant_id: str
    duration_min: float = 5.0
    intensity: Intensity = Intensity.MEDIUM
    paradigm_ids: list[str] = []
    blocks: int = 1
    rest_duration_sec: int = 30
    practice_enabled: bool = True
    practice_trials_per_paradigm: int = 1
    starting_difficulty: int = 1


class SessionSummary(BaseModel):
    participant_id: str
    session_start: str
    session_end: str
    duration_target_sec: int
    intensity: str
    paradigms_used: list[str]
    total_tasks: int
    correct_answers: int
    accuracy_pct: float
    max_difficulty: int
    avg_response_time_ms: float
    per_paradigm: dict
    trials: list[TrialResult]


class Participant(BaseModel):
    id: str
    created: str
    demographics: dict = {}
    session_files: list[str] = []


class ProtocolPreset(BaseModel):
    id: str
    name: str
    description: str
    paradigm_ids: list[str]
    duration_min: float
    intensity: Intensity
    blocks: int
    rest_duration_sec: int
