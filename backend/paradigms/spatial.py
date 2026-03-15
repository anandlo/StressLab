import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType

COMPASS = {0: "NORTH", 1: "EAST", 2: "SOUTH", 3: "WEST"}
ROTATIONS = {"Right 90": 1, "Left 90": -1, "About-face": 2}


class MentalRotation(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="mental_rotation", label="Mental Rotation",
            reference="Shepard, R.N. & Metzler, J. (1971). Mental rotation of three-dimensional objects. Science, 171(3972), 701-703.",
            description="Track cumulative rotations to determine final orientation. Example: start facing NORTH, apply 'Right 90' then 'Left 90', you end facing NORTH.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.TEXT,
            base_time_sec=25, category="Spatial")

    def generate_trial(self, difficulty, time_limit):
        start_idx = random.randint(0, 3)
        cur = start_idx
        steps = 2 + min(difficulty, 4)
        moves = []
        for _ in range(steps):
            label, delta = random.choice(list(ROTATIONS.items()))
            moves.append(label)
            cur = (cur + delta) % 4
        answer = COMPASS[cur]
        arrow = " -> "
        return self._trial(
            difficulty, time_limit,
            stimulus={"start": COMPASS[start_idx], "moves": moves,
                      "display": f"Start: {COMPASS[start_idx]}.  {arrow.join(moves)}",
                      "keyboard_options": [
                          {"key": "n", "label": "NORTH"}, {"key": "e", "label": "EAST"},
                          {"key": "s", "label": "SOUTH"}, {"key": "w", "label": "WEST"}]},
            correct_answer=answer,
            instruction="Which direction are you facing? Press N/E/S/W.",
            explanation=f"Start {COMPASS[start_idx]}, apply {', '.join(moves)} -> {answer}")


class SimonTask(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="simon_task", label="Simon Task",
            reference="Simon, J.R. & Rudell, A.P. (1967). Auditory S-R compatibility: Effect of an irrelevant cue on information processing. Journal of Applied Psychology, 51(3), 300-304.",
            description="Respond based on stimulus color, ignoring its spatial position. Example: a blue circle appears on the RIGHT side - press LEFT (blue = left), ignoring position.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.SHAPE,
            base_time_sec=6, category="Spatial")

    def generate_trial(self, difficulty, time_limit):
        # Higher difficulty -> more incongruent trials, more colors, size variability,
        # and competing text labels on the shapes to create response conflict.
        congruent_prob = max(0.15, 0.45 - difficulty * 0.05)

        # At difficulty >= 4, add a third color mapping (green = UP).
        # At difficulty >= 6, add fourth (purple = DOWN).
        if difficulty >= 6:
            colors = ["blue", "orange", "green", "purple"]
            color_map = {"blue": "LEFT", "orange": "RIGHT", "green": "UP", "purple": "DOWN"}
            hex_map = {"blue": "#3b82f6", "orange": "#f97316", "green": "#22c55e", "purple": "#a855f7"}
            options = [
                {"key": "ArrowLeft", "label": "\u2190 BLUE"},
                {"key": "ArrowRight", "label": "\u2192 ORANGE"},
                {"key": "ArrowUp", "label": "\u2191 GREEN"},
                {"key": "ArrowDown", "label": "\u2193 PURPLE"},
            ]
        elif difficulty >= 4:
            colors = ["blue", "orange", "green"]
            color_map = {"blue": "LEFT", "orange": "RIGHT", "green": "UP"}
            hex_map = {"blue": "#3b82f6", "orange": "#f97316", "green": "#22c55e"}
            options = [
                {"key": "ArrowLeft", "label": "\u2190 BLUE"},
                {"key": "ArrowRight", "label": "\u2192 ORANGE"},
                {"key": "ArrowUp", "label": "\u2191 GREEN"},
            ]
        else:
            colors = ["blue", "orange"]
            color_map = {"blue": "LEFT", "orange": "RIGHT"}
            hex_map = {"blue": "#3b82f6", "orange": "#f97316"}
            options = [
                {"key": "ArrowLeft", "label": "\u2190 LEFT (blue)"},
                {"key": "ArrowRight", "label": "\u2192 RIGHT (orange)"},
            ]

        color = random.choice(colors)
        correct = color_map[color]
        color_hex = hex_map[color]

        # Position: place stimulus at a conflicting spatial location
        positions = ["left", "right"]
        if len(colors) > 2:
            positions += ["top", "bottom"]
        is_congruent = random.random() < congruent_prob
        correct_pos = correct.lower()
        if is_congruent:
            position = correct_pos if correct_pos in positions else random.choice(positions)
        else:
            wrong_positions = [p for p in positions if p != correct_pos]
            position = random.choice(wrong_positions)

        # Shape variability at high difficulty: not always a circle
        shapes = ["circle"]
        if difficulty >= 3:
            shapes += ["square", "diamond"]
        shape = random.choice(shapes)

        # Size variability to distract
        base_size = 80
        if difficulty >= 2:
            base_size = random.choice([60, 80, 100, 120])

        # Competing text label on the shape at difficulty >= 5
        # Show an INCORRECT direction word on the shape itself
        label = ""
        if difficulty >= 5:
            wrong_labels = [v for v in color_map.values() if v != correct]
            label = random.choice(wrong_labels) if random.random() < 0.7 else ""

        instruction_parts = [f"{c.upper()} = {color_map[c]}" for c in colors]
        instruction = " | ".join(instruction_parts) + ". Ignore position and text."

        return self._trial(
            difficulty, time_limit,
            stimulus={"color": color, "color_hex": color_hex,
                      "position": position, "congruent": is_congruent,
                      "shape": shape, "size": base_size, "label": label,
                      "keyboard_options": options},
            correct_answer=correct,
            instruction=instruction,
            explanation=f"Color: {color} ({correct}), Position: {position}, Label: '{label}'. {'Congruent' if is_congruent else 'Incongruent'}.")


class PatternCompletion(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="pattern_completion", label="Pattern Completion",
            reference="Cognitive load paradigm",
            description="Identify the pattern and find the missing number. Example: in 2, 4, 6, ?, 10 the answer is 8.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.SEQUENCE,
            base_time_sec=20, category="Spatial",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        generator = random.choice([self._alternating, self._interleave, self._fibonacci])
        return generator(difficulty, time_limit)

    def _alternating(self, difficulty, time_limit):
        start = random.randint(3, 12)
        v1 = random.randint(2, 3 + difficulty)
        v2 = random.randint(1, 2 + difficulty)
        op = random.choice(["add", "mult"])
        seq, c = [start], start
        for i in range(5):
            c = (c + v1 if op == "add" else c * v1) if i % 2 == 0 else c - v2
            seq.append(c)
        answer = str(seq[-1])
        seq[-1] = "?"
        return self._trial(
            difficulty, time_limit,
            stimulus={"sequence": seq, "display": "  ".join(str(x) for x in seq)},
            correct_answer=answer,
            instruction="Find the pattern. What replaces '?'?",
            explanation=f"Pattern: alternating {'add' if op == 'add' else 'multiply'} {v1}, subtract {v2}. Answer: {answer}")

    def _interleave(self, difficulty, time_limit):
        s1, s2 = random.randint(1, 10), random.randint(20, 30)
        d1, d2 = random.randint(2, 3 + difficulty), random.randint(-4, -1)
        seq = []
        for i in range(3):
            seq += [s1 + i * d1, s2 + i * d2]
        answer = str(s1 + 3 * d1)
        seq.append("?")
        return self._trial(
            difficulty, time_limit,
            stimulus={"sequence": seq, "display": "  ".join(str(x) for x in seq)},
            correct_answer=answer,
            instruction="Two sequences are mixed. What comes next?",
            explanation=f"Sequence A: +{d1}, Sequence B: {d2}. Answer: {answer}")

    def _fibonacci(self, difficulty, time_limit):
        a, b = random.randint(1, 5), random.randint(1, 5)
        seq = [a, b]
        for _ in range(4):
            seq.append(seq[-1] + seq[-2])
        answer = str(seq[-1])
        seq[-1] = "?"
        return self._trial(
            difficulty, time_limit,
            stimulus={"sequence": seq, "display": "  ".join(str(x) for x in seq)},
            correct_answer=answer,
            instruction="Each number = sum of previous two. What replaces '?'?",
            explanation=f"Fibonacci-like sequence. Answer: {answer}")
