from abc import ABC, abstractmethod
import uuid
from ..models import ParadigmMeta, Trial


class BaseParadigm(ABC):
    """Base class for all cognitive stress paradigms."""

    @property
    @abstractmethod
    def meta(self) -> ParadigmMeta:
        ...

    @abstractmethod
    def generate_trial(self, difficulty: int, time_limit: float) -> Trial:
        ...

    def check_answer(self, trial: Trial, response: str) -> bool:
        return response.strip().upper() == trial.correct_answer.strip().upper()

    def reset(self):
        """Reset internal state between sessions."""
        pass

    def _trial(self, difficulty: int, time_limit: float, stimulus: dict,
               correct_answer: str, instruction: str, explanation: str = "",
               *, input_mode_override=None, stimulus_type_override=None) -> Trial:
        return Trial(
            trial_id=uuid.uuid4().hex[:12],
            paradigm_id=self.meta.id,
            paradigm_label=self.meta.label,
            difficulty=difficulty,
            time_limit_sec=time_limit,
            stimulus_type=stimulus_type_override or self.meta.stimulus_type,
            input_mode=input_mode_override or self.meta.input_mode,
            stimulus=stimulus,
            correct_answer=str(correct_answer),
            instruction=instruction,
            explanation=explanation,
        )
