from .base import BaseParadigm
from .arithmetic import SerialSubtraction, MentalArithmetic, PASAT
from .stroop import ClassicStroop, EmotionalStroop
from .memory import NBack, DigitSpan, OperationSpan, SternbergTask
from .attention import Flanker, PVT, CPT, GoNoGo, StopSignalTask, VisualSearch
from .executive import WCST, TrailMaking, TowerOfLondon, TaskSwitching
from .spatial import MentalRotation, SimonTask, PatternCompletion
from .adaptive import MIST, RapidComparison, DualTask

ALL_PARADIGMS = [
    SerialSubtraction(), MentalArithmetic(), PASAT(),
    ClassicStroop(), EmotionalStroop(),
    NBack(), DigitSpan(), OperationSpan(), SternbergTask(),
    Flanker(), PVT(), CPT(), GoNoGo(), StopSignalTask(), VisualSearch(),
    WCST(), TrailMaking(), TowerOfLondon(), TaskSwitching(),
    MentalRotation(), SimonTask(), PatternCompletion(),
    MIST(), RapidComparison(), DualTask(),
]

PARADIGM_REGISTRY: dict[str, BaseParadigm] = {p.meta.id: p for p in ALL_PARADIGMS}
