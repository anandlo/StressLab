import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType


class SerialSubtraction(BaseParadigm):
    # Combines original serial subtraction and backwards counting into one
    # paradigm. Variants from Kirschbaum et al. (1993) TSST:
    # 1022 - 13, 2083 - 17 (hard), 100 - 3 (easy), 1000 - 7 (medium).
    _VARIANTS = [(100, 3), (1022, 13), (1000, 7), (2083, 17)]

    def __init__(self):
        self._current: int = 1022
        self._step: int = 13

    def reset(self):
        self._current, self._step = random.choice(self._VARIANTS)

    @property
    def meta(self):
        return ParadigmMeta(
            id="serial_subtraction", label="Serial Subtraction (TSST)",
            reference="Kirschbaum, C., Pirke, K.M., & Hellhammer, D.H. (1993). The 'Trier Social Stress Test' -- a tool for investigating psychobiological stress responses in a laboratory setting. Neuropsychobiology, 28(1-2), 76-81.",
            description="Subtract a fixed value one step at a time in a continuous chain, as in the TSST arithmetic protocol. Example: starting from 1022, subtract 13 each trial: 1009, 996, 983...",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.TEXT,
            base_time_sec=20, category="Arithmetic")

    def generate_trial(self, difficulty, time_limit):
        start = self._current
        answer = start - self._step
        self._current = answer  # advance the chain regardless of correctness
        return self._trial(
            difficulty, time_limit,
            stimulus={"question": f"{start} \u2212 {self._step} = ?"},
            correct_answer=str(answer),
            instruction=f"Subtract {self._step} and enter the result. Continue the chain from the previous answer.",
            explanation=f"{start} \u2212 {self._step} = {answer}")


class MentalArithmetic(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="mental_arithmetic", label="Mental Arithmetic",
            reference="Standard cognitive load paradigm",
            description="Solve multi-step arithmetic expressions mentally. Example: given '(15 + 8) x 3', calculate 69.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.TEXT,
            base_time_sec=25, category="Arithmetic")

    def generate_trial(self, difficulty, time_limit):
        if difficulty <= 2:
            a, b, c = random.randint(10, 50), random.randint(5, 20), random.randint(2, 10)
            variants = [
                (f"{a} + {b} x {c}", a + b * c),
                (f"{a} x {b} - {c}", a * b - c),
                (f"({a} + {b}) x {c}", (a + b) * c),
            ]
        else:
            a, b = random.randint(10, 25), random.randint(5, 15)
            c, d = random.randint(2, 8), random.randint(2, 6)
            variants = [
                (f"{a} x {b} + {c} x {d}", a * b + c * d),
                (f"({a} + {b}) x ({c} + {d})", (a + b) * (c + d)),
            ]
        expr, ans = random.choice(variants)
        return self._trial(
            difficulty, time_limit,
            stimulus={"question": expr},
            correct_answer=str(ans),
            instruction="Calculate the result.",
            explanation=f"{expr} = {ans}")


class PASAT(BaseParadigm):
    def __init__(self):
        self._prev: int | None = None

    @property
    def meta(self):
        return ParadigmMeta(
            id="pasat", label="PASAT",
            reference="Gronwall, D.M.A. (1977). Paced auditory serial-addition task: A measure of recovery from concussion. Perceptual and Motor Skills, 44(2), 367-373.",
            description="Add the current number to the previous one in a continuous stream. Example: if the last number was 5 and the current is 8, answer 13.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.TEXT,
            base_time_sec=20, category="Arithmetic")

    def reset(self):
        self._prev = None

    def generate_trial(self, difficulty, time_limit):
        current = random.randint(1, 9)
        if self._prev is None:
            # First trial: just show the number; no addition is possible yet.
            self._prev = current
            return self._trial(
                difficulty, time_limit,
                stimulus={"current": current, "pasat": True, "is_first": True},
                correct_answer=str(current),
                instruction="Remember this number. Type it to confirm, then the next trial will ask you to add.",
                explanation=f"First number in the series: {current}")
        answer = self._prev + current
        prev_for_explanation = self._prev
        # Include the previous number in the stimulus so participants don't
        # have to remember it across interleaved paradigms.
        trial = self._trial(
            difficulty, time_limit,
            stimulus={"current": current, "previous": prev_for_explanation, "pasat": True, "is_first": False},
            correct_answer=str(answer),
            instruction="Add these two numbers. Type the sum.",
            explanation=f"{prev_for_explanation} + {current} = {answer}")
        self._prev = current
        return trial
