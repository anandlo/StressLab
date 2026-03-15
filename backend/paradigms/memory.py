import random
from collections import deque
from .base import BaseParadigm
from ..models import ParadigmMeta, Trial, InputMode, StimulusType


class NBack(BaseParadigm):
    def __init__(self):
        self._history: deque[int] = deque(maxlen=12)
        self._shown_count: int = 0
        self._last_n: int = 0

    @property
    def meta(self):
        return ParadigmMeta(
            id="n_back", label="N-Back",
            reference="Kirchner, W.K. (1958). Age differences in short-term retention of rapidly changing information. Journal of Experimental Psychology, 55(4), 352-358.",
            description="Determine if the current stimulus matches one from N steps back. Example: in 2-back, if the current number is 7 and the number two steps ago was also 7, press YES.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.TEXT,
            base_time_sec=15, category="Memory",
            metric_focus="accuracy")
    def reset(self):
        self._history.clear()
        self._shown_count = 0
        self._last_n = 0

    def generate_trial(self, difficulty, time_limit):
        # Start hard: n=2 at difficulty 1, scaling to n=5 at high difficulty
        n = min(5, 2 + (difficulty - 1) // 2)
        new_val = random.randint(1, 9)

        rule_change_notice = ""
        if n != self._last_n:
            if self._last_n == 0:
                rule_change_notice = f"Starting {n}-back. Remember each number. After {n} numbers, you will judge whether the current number matches the one from exactly {n} step{'s' if n > 1 else ''} ago."
            else:
                rule_change_notice = f"Rule change: now {n}-back. Match the number from {n} steps ago (previously {self._last_n}-back)."
            self._last_n = n

        # After enough history, sometimes create a match
        if len(self._history) >= n and random.random() < 0.4:
            new_val = self._history[-n]

        self._history.append(new_val)
        self._shown_count += 1

        if self._shown_count <= n:
            # Introductory trial: not enough history for comparison.
            # Participant just memorizes the number and presses any key.
            return self._trial(
                difficulty, time_limit,
                stimulus={"n": n, "current": new_val,
                          "n_back": True, "is_intro": True,
                          "trial_number": self._shown_count,
                          "rule_change_notice": rule_change_notice,
                          "keyboard_options": [
                              {"key": "ArrowRight", "label": "\u2192 Continue"}]},
                correct_answer="RIGHT",
                instruction=f"Remember this number. ({self._shown_count}/{n} intro)",
                explanation=f"Intro trial {self._shown_count}/{n}. Number: {new_val}")

        comparator = self._history[-(n + 1)]
        match = new_val == comparator
        return self._trial(
            difficulty, time_limit,
            stimulus={"n": n, "current": new_val,
                      "comparator": comparator, "is_match": match,
                      "trial_number": self._shown_count,
                      "n_back": True,
                      "rule_change_notice": rule_change_notice,
                      "keyboard_options": [
                          {"key": "y", "label": "YES (match)"},
                          {"key": "n", "label": "NO (different)"}]},
            correct_answer="YES" if match else "NO",
            instruction=f"Does this number match the one from {n} step{'s' if n > 1 else ''} ago? Press Y or N.",
            explanation=f"Current: {new_val}, {n}-back: {comparator}. {'Match' if match else 'No match'}.")

    def check_answer(self, trial: Trial, response: str) -> bool:
        # Intro trials accept any response
        if trial.stimulus.get("is_intro"):
            return True
        return response.strip().upper() == trial.correct_answer.strip().upper()


class DigitSpan(BaseParadigm):
    def __init__(self):
        self._last_backward: bool | None = None

    def reset(self):
        self._last_backward = None

    @property
    def meta(self):
        return ParadigmMeta(
            id="digit_span", label="Digit Span",
            reference="Wechsler, D. (1939). The Measurement of Adult Intelligence. Williams & Wilkins.",
            description="Recall a sequence of digits forwards or backwards. Example: after seeing 4 7 2 9, type '4729' (forward) or '9274' (backward).",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.SEQUENCE,
            base_time_sec=20, category="Memory",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        length = 4 + min(difficulty, 6)
        digits = [random.randint(0, 9) for _ in range(length)]
        backward = difficulty >= 3 and random.random() < 0.5
        display = "  ".join(str(d) for d in digits)
        # Per Wechsler: digits are read aloud at 1 per second, then recalled.
        # We show digits briefly, then hide them. Display time scales with length.
        display_time_ms = 800 + length * 600
        if backward:
            answer = "".join(str(d) for d in reversed(digits))
            direction = "BACKWARDS"
        else:
            answer = "".join(str(d) for d in digits)
            direction = "FORWARDS"
        rule_change_notice = ""
        if self._last_backward is not None and backward and not self._last_backward:
            rule_change_notice = "Rule change: now recalling digits in REVERSE order. Watch the sequence, then type all digits backwards."
        elif self._last_backward is not None and not backward and self._last_backward:
            rule_change_notice = "Rule change: back to recalling digits in FORWARD order. Type the sequence as shown."
        self._last_backward = backward
        return self._trial(
            difficulty, time_limit,
            stimulus={"digits": digits, "display": display,
                      "direction": direction, "length": length,
                      "display_time_ms": display_time_ms,
                      "rule_change_notice": rule_change_notice,
                      "digit_span": True},
            correct_answer=answer,
            instruction=f"Watch the digits. They will disappear. Then type them {'in reverse order' if backward else 'in the same order'} (no spaces).",
            explanation=f"Digits: {display}. {direction}: {answer}")


class OperationSpan(BaseParadigm):
    """Operation span task measuring working memory capacity.

    Each trial presents one math verification + one letter to remember.
    After a set of trials the participant must recall all letters in order.
    Within a single-trial architecture we accumulate letters across trials
    and periodically trigger a recall trial.
    """

    def __init__(self):
        self._letters: list[str] = []
        self._set_size: int = 3
        self._sets_completed: int = 0

    def reset(self):
        self._letters = []
        self._set_size = 3
        self._sets_completed = 0

    @property
    def meta(self):
        return ParadigmMeta(
            id="operation_span", label="Operation Span",
            reference="Turner, M.L. & Engle, R.W. (1989). Is working memory capacity task dependent? Journal of Memory and Language, 28(2), 127-154.",
            description="Verify a math equation, then remember the letter shown. After several pairs, recall all letters in order. Example: verify '(3 + 4) = 7', remember 'F', then type all letters.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.DUAL,
            base_time_sec=20, category="Memory",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        self._set_size = min(2 + difficulty, 7)

        if len(self._letters) >= self._set_size:
            # Recall trial: ask participant to type all accumulated letters.
            answer = "".join(self._letters)
            recall_letters = list(self._letters)
            self._letters = []
            self._sets_completed += 1
            return self._trial(
                difficulty, time_limit,
                stimulus={"phase": "recall",
                          "set_size": len(recall_letters),
                          "ospan": True,
                          "prompt": f"Type all {len(recall_letters)} letters you saw, in order (no spaces)."},
                correct_answer=answer,
                instruction=f"Recall all {len(recall_letters)} letters in the order they appeared.",
                explanation=f"Letters to recall: {answer}")

        # Encoding trial: math verification + letter to remember.
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        op = random.choice(["+", "-"])
        result = a + b if op == "+" else a - b
        is_correct_eq = random.random() < 0.5
        shown_result = result if is_correct_eq else result + random.choice([-1, 1, 2, -2])
        math_str = f"({a} {op} {b}) = {shown_result}"

        available = [c for c in "BCDFGHJKLMNPQRSTVWXYZ" if c not in self._letters]
        letter = random.choice(available) if available else random.choice("BCDFGHJKLMNPQRSTVWXYZ")
        self._letters.append(letter)

        position = len(self._letters)
        return self._trial(
            difficulty, time_limit,
            stimulus={"math": math_str, "math_correct": is_correct_eq,
                      "letter": letter,
                      "position": position,
                      "set_size": self._set_size,
                      "phase": "encode",
                      "ospan": True,
                      "prompt": f"Is {math_str} correct? Type YES or NO."},
            correct_answer="YES" if is_correct_eq else "NO",
            instruction=f"Is the math correct? Type YES or NO. Remember the letter: {letter} (letter {position} of {self._set_size}).",
            explanation=f"Math: {math_str} is {'correct' if is_correct_eq else 'incorrect'}. Letter to remember: {letter}")


class SternbergTask(BaseParadigm):
    """Sternberg memory scanning task -- stress variant.

    Per Sternberg (1966): a memory set is shown for study, then cleared.
    A single probe digit appears and the participant judges whether it was
    in the set. Start with 5 items to be harder from the beginning. At
    high difficulty the digits are shown in a matrix layout instead of a
    row, forcing spatial scanning during memorization.
    """

    @property
    def meta(self):
        return ParadigmMeta(
            id="sternberg", label="Sternberg Task",
            reference="Sternberg, S. (1966). High-speed scanning in human memory. Science, 153(3736), 652-654.",
            description="Study a set of digits (shown in a row or matrix), then determine if a probe digit was in the set.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.TEXT,
            base_time_sec=10, category="Memory",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        # Start with 5, scale up to 9
        set_size = min(5 + difficulty // 2, 9)
        memory_set = random.sample(range(1, 10), min(set_size, 9))
        is_positive = random.random() < 0.5
        if is_positive:
            probe = random.choice(memory_set)
        else:
            remaining = [d for d in range(1, 10) if d not in memory_set]
            probe = random.choice(remaining) if remaining else random.randint(1, 9)
        display = "  ".join(str(d) for d in memory_set)
        # Study time shrinks slightly with difficulty
        study_time_ms = max(800, 1200 + set_size * 300 - difficulty * 100)

        # Matrix layout at difficulty >= 4
        matrix = None
        matrix_cols = 0
        if difficulty >= 4 and set_size >= 6:
            matrix_cols = 3 if set_size <= 6 else 4
            rows = []
            items = list(memory_set)
            while items:
                rows.append(items[:matrix_cols])
                items = items[matrix_cols:]
            matrix = rows

        return self._trial(
            difficulty, time_limit,
            stimulus={"memory_set": memory_set, "probe": probe,
                      "set_display": display,
                      "study_time_ms": study_time_ms,
                      "sternberg": True,
                      "is_positive": is_positive,
                      "matrix": matrix,
                      "matrix_cols": matrix_cols,
                      "keyboard_options": [
                          {"key": "y", "label": "YES (in set)"},
                          {"key": "n", "label": "NO (not in set)"}]},
            correct_answer="YES" if is_positive else "NO",
            instruction="Memorize the digits. A probe will appear. Was it in the set? Y or N.",
            explanation=f"Set: {memory_set}, probe: {probe}. {'In set' if is_positive else 'Not in set'}.")
