import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType


class MIST(BaseParadigm):
    """Montreal Imaging Stress Test: adaptive math with deceptive performance comparison."""
    def __init__(self):
        self._limit = 5.0
        self._fake_score = 0
        self._user_correct = 0
        self._user_total = 0

    _STRESS_MESSAGES = [
        "You are falling behind the average participant.",
        "Most participants solve these faster.",
        "Your accuracy is below the group average.",
        "Performance declining. Try harder.",
        "Warning: below expected performance level.",
    ]

    @property
    def meta(self):
        return ParadigmMeta(
            id="mist", label="MIST Adaptive",
            reference="Dedovic, K., Renwick, R., Mahani, N.K., Engert, V., Lupien, S.J., & Bherer, L. (2005). The Montreal Imaging Stress Task. Journal of Psychiatry and Neuroscience, 30(5), 319-325.",
            description="Adaptive arithmetic with false social-evaluative performance comparison. Example: solve '23 x 4' under time pressure while a progress bar shows you trailing behind peers.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.DUAL,
            base_time_sec=8, category="Adaptive")

    def reset(self):
        self._limit = 5.0
        self._fake_score = 0
        self._user_correct = 0
        self._user_total = 0

    def generate_trial(self, difficulty, time_limit):
        # Multi-step and multiplication at higher difficulty to differentiate from
        # plain arithmetic paradigms (serial subtraction, mental arithmetic)
        if difficulty >= 5:
            # Multi-step: (a + b) x c or a x b - c
            a = random.randint(5, 15 + difficulty * 2)
            b = random.randint(2, 8 + difficulty)
            c = random.randint(2, 6 + difficulty)
            variant = random.choice(["add_mult", "mult_sub"])
            if variant == "add_mult":
                question = f"({a} + {b}) x {c}"
                result = (a + b) * c
            else:
                question = f"{a} x {b} - {c}"
                result = a * b - c
        elif difficulty >= 3:
            # Introduce multiplication
            a = random.randint(6, 20 + difficulty * 5)
            b = random.randint(2, 9 + difficulty)
            op = random.choice(["+", "-", "x"])
            if op == "x":
                a = random.randint(3, 12 + difficulty)
                result = a * b
            elif op == "+":
                result = a + b
            else:
                result = a - b
            question = f"{a} {op} {b}"
        else:
            a = random.randint(11, 40 + difficulty * 10)
            b = random.randint(2, 9 + difficulty)
            op = random.choice(["+", "-"])
            result = a + b if op == "+" else a - b
            question = f"{a} {op} {b}"

        # Fake performance always stays ahead of user with stress messaging
        self._user_total += 1
        target_fake = max(self._user_correct + 2, int(self._user_total * 0.85))
        self._fake_score = target_fake + random.randint(-1, 1)
        fake_pct = min(95, int(self._fake_score / max(1, self._user_total) * 100))
        user_pct = int(self._user_correct / max(1, self._user_total) * 100) if self._user_total > 0 else 0
        actual_limit = max(3.0, self._limit)

        # Stress message when user is behind (which is almost always)
        stress_msg = ""
        if fake_pct > user_pct + 5:
            stress_msg = random.choice(self._STRESS_MESSAGES)

        return self._trial(
            difficulty, actual_limit,
            stimulus={"math_question": question, "time_limit_display": f"{actual_limit:.1f}s",
                      "comparison": {"avg_participant_pct": fake_pct, "user_pct": user_pct,
                                     "stress_message": stress_msg},
                      "mist": True},
            correct_answer=str(result),
            instruction=f"Solve quickly. Time limit: {actual_limit:.1f}s",
            explanation=f"{question} = {result}")

    def check_answer(self, trial, response):
        correct = super().check_answer(trial, response)
        if correct:
            self._user_correct += 1
            self._limit = max(2.5, self._limit * 0.92)
        else:
            self._limit = min(12.0, self._limit * 1.08)
        return correct


class RapidComparison(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="rapid_comparison", label="Rapid Comparison",
            reference="Cognitive load paradigm",
            description="Determine which set of numbers has the larger total. Example: Set A = 45 + 32 + 18 vs Set B = 27 + 41 + 30 - press A if its total is larger.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.TEXT,
            base_time_sec=18, category="Adaptive")

    def generate_trial(self, difficulty, time_limit):
        n = 3 + difficulty
        a = [random.randint(10, 99) for _ in range(n)]
        b = [random.randint(10, 99) for _ in range(n)]
        sa, sb = sum(a), sum(b)
        if sa == sb:
            a[-1] += 1
            sa += 1
        correct = "A" if sa > sb else "B"
        return self._trial(
            difficulty, time_limit,
            stimulus={"set_a": a, "set_b": b,
                      "display_a": " + ".join(map(str, a)),
                      "display_b": " + ".join(map(str, b)),
                      "rapid_comparison": True,
                      "keyboard_options": [
                          {"key": "a", "label": "A is larger"},
                          {"key": "b", "label": "B is larger"}]},
            correct_answer=correct,
            instruction="Which set has the LARGER total? Press A or B.",
            explanation=f"A = {sa}, B = {sb}. Answer: {correct}")


class DualTask(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="dual_task", label="Dual-Task",
            reference="Pashler, H. (1994). Dual-task interference in simple tasks: Data and theory. Psychological Bulletin, 116(2), 220-244.",
            description="Simultaneous arithmetic and letter detection under time pressure. Example: solve '25 + 13' and check if 'K' is among the letters, then type '38Y' or '38N'.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.DUAL,
            base_time_sec=15, category="Adaptive")

    def generate_trial(self, difficulty, time_limit):
        a, b = random.randint(10, 30 + difficulty * 5), random.randint(2, 10 + difficulty)
        op = random.choice(["+", "-", "x"])
        if op == "+":
            math_ans = a + b
        elif op == "-":
            math_ans = a - b
        else:
            math_ans = a * b
        target_letter = random.choice("XKZQJM")
        pool = "ABCDEFGHJKLMNOPQRSTUVWYZ".replace(target_letter, "")
        letters = [random.choice(pool) for _ in range(5)]
        has_target = random.random() < 0.4
        if has_target:
            letters[random.randint(0, 4)] = target_letter
        letter_display = "  ".join(letters)
        # Combined answer: math result + Y/N for letter detection
        combined_answer = f"{math_ans}{'Y' if has_target else 'N'}"
        return self._trial(
            difficulty, time_limit,
            stimulus={"math_question": f"{a} {op} {b}",
                      "letter_stream": letters, "letter_display": letter_display,
                      "target_letter": target_letter},
            correct_answer=combined_answer,
            instruction=f"Solve: {a} {op} {b}. Also: is '{target_letter}' in the letters? Type answer + Y/N (e.g., 42Y or 42N).",
            explanation=f"{a} {op} {b} = {math_ans}. '{target_letter}' {'present' if has_target else 'absent'}. Answer: {combined_answer}")
