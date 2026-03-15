import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType

WCST_SHAPES = ["circle", "triangle", "square", "star"]
WCST_COLORS = ["red", "blue", "green", "yellow"]
WCST_COLOR_HEX = {"red": "#ef4444", "blue": "#3b82f6", "green": "#22c55e", "yellow": "#eab308"}
WCST_RULES = ["color", "shape", "count"]


class WCST(BaseParadigm):
    def __init__(self):
        self._rule_idx = 0
        self._streak = 0
        self._shift_after = random.randint(5, 8)

    @property
    def meta(self):
        return ParadigmMeta(
            id="wcst", label="Wisconsin Card Sorting",
            reference="Berg, E.A. (1948). A simple objective technique for measuring flexibility in thinking. Journal of General Psychology, 39(1), 15-22.",
            description="Match cards by an implicit rule that shifts without warning. Example: if the hidden rule is 'color', match a red triangle to a red circle, not a blue triangle.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.CARDS,
            base_time_sec=15, category="Executive",
            metric_focus="accuracy")

    def reset(self):
        self._rule_idx = 0
        self._streak = 0
        self._shift_after = random.randint(5, 8)

    def generate_trial(self, difficulty, time_limit):
        rule = WCST_RULES[self._rule_idx % len(WCST_RULES)]
        target = {
            "shape": random.choice(WCST_SHAPES),
            "color": random.choice(WCST_COLORS),
            "count": random.randint(1, 4),
        }
        choices = []
        correct_idx = random.randint(0, 3)
        for i in range(4):
            if i == correct_idx:
                card = dict(target)
                for attr in ["shape", "color", "count"]:
                    if attr != rule:
                        if attr == "shape":
                            card[attr] = random.choice([s for s in WCST_SHAPES if s != target[attr]])
                        elif attr == "color":
                            card[attr] = random.choice([c for c in WCST_COLORS if c != target[attr]])
                        else:
                            card[attr] = random.choice([n for n in range(1, 5) if n != target[attr]])
            else:
                card = {
                    "shape": random.choice(WCST_SHAPES),
                    "color": random.choice(WCST_COLORS),
                    "count": random.randint(1, 4),
                }
                while card[rule] == target[rule]:
                    card[rule] = (random.choice(WCST_SHAPES) if rule == "shape"
                                  else random.choice(WCST_COLORS) if rule == "color"
                                  else random.randint(1, 4))
            card["color_hex"] = WCST_COLOR_HEX[card["color"]]
            choices.append(card)
        target["color_hex"] = WCST_COLOR_HEX[target["color"]]
        return self._trial(
            difficulty, time_limit,
            stimulus={"target": target, "choices": choices,
                      "keyboard_options": [{"key": str(i + 1), "label": str(i + 1)} for i in range(4)]},
            correct_answer=str(correct_idx + 1),
            instruction="Match the card to the target. Press 1-4. The rule may change without warning.",
            explanation=f"Current rule: {rule}. Card {correct_idx + 1} matches by {rule}.")

    def check_answer(self, trial, response):
        correct = super().check_answer(trial, response)
        if correct:
            self._streak += 1
            if self._streak >= self._shift_after:
                self._rule_idx += 1
                self._streak = 0
                self._shift_after = random.randint(5, 8)
        else:
            self._streak = 0
        return correct


class TrailMaking(BaseParadigm):
    def __init__(self):
        self._last_variant: str | None = None
        self._last_scrambled: bool = False

    def reset(self):
        self._last_variant = None
        self._last_scrambled = False

    @property
    def meta(self):
        return ParadigmMeta(
            id="trail_making", label="Trail Making",
            reference="Reitan, R.M. (1958). Validity of the Trail Making Test as an indicator of organic brain damage. Perceptual and Motor Skills, 8, 271-276.",
            description="Identify the next item in an alternating number-letter sequence. Example: in 1-A-2-B-?-C, the missing item is 3.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.SEQUENCE,
            base_time_sec=12, category="Executive")

    def generate_trial(self, difficulty, time_limit):
        length = 5 + min(difficulty, 5)     # 6 to 10 items visible
        is_b = difficulty >= 2

        # Build a longer underlying sequence and take a random window from it
        full_len = length + 4
        if is_b:
            # TMT-B: alternate number-letter starting from a random offset
            start_offset = random.randint(0, 6)
            full_seq = []
            for i in range(full_len):
                idx = start_offset + i
                if idx % 2 == 0:
                    full_seq.append(str(idx // 2 + 1))
                else:
                    full_seq.append(chr(ord("A") + idx // 2))
            variant = "B"
        else:
            # TMT-A: consecutive numbers starting from a random offset
            start = random.randint(1, 10)
            full_seq = [str(start + i) for i in range(full_len)]
            variant = "A"

        # Take a windowed slice of `length` items
        win_start = random.randint(0, len(full_seq) - length)
        seq = full_seq[win_start:win_start + length]

        # At difficulty >= 4, scramble the DISPLAY order so user must search
        if difficulty >= 4:
            gap_idx = random.randint(1, length - 2)
            answer = seq[gap_idx]
            # Scramble the items that will be shown (not the answer)
            shown = seq[:gap_idx] + seq[gap_idx + 1:]
            random.shuffle(shown)
            # Re-insert gap marker at a random position to a fixed visible slot
            display_seq = shown[:gap_idx] + ["?"] + shown[gap_idx:]
            instruction = f"TMT-{variant} (scrambled): What item is missing? It follows {seq[gap_idx - 1]} in the sequence."
        else:
            gap_idx = random.randint(1, length - 2)
            answer = seq[gap_idx]
            display_seq = seq[:gap_idx] + ["?"] + seq[gap_idx + 1:]
            instruction = f"TMT-{variant}: What replaces '?'?"

        # Emit a rule-change notice when the variant or scramble mode changes
        scrambled = difficulty >= 4
        rule_change_notice = ""
        if self._last_variant is not None:
            if variant == "B" and self._last_variant == "A":
                rule_change_notice = "Rule change: now TMT-B. Alternate between numbers AND letters (1-A-2-B-3-C...)."
            elif variant == "A" and self._last_variant == "B":
                rule_change_notice = "Rule change: back to TMT-A. Numbers only in ascending sequence."
            elif scrambled and not self._last_scrambled:
                rule_change_notice = "Rule change: items are now scrambled. Search for the missing item in the correct sequence position."
        self._last_variant = variant
        self._last_scrambled = scrambled

        # Add decoy adjacent items at high difficulty
        extra_info = ""
        if difficulty >= 5:
            if is_b:
                extra_info = " (Alternate numbers and letters: 1-A-2-B-3-C...)"
            else:
                extra_info = " (Consecutive numbers)"

        return self._trial(
            difficulty, time_limit,
            stimulus={"sequence": display_seq, "variant": variant,
                      "display": "  ".join(display_seq),
                      "rule_change_notice": rule_change_notice},
            correct_answer=answer,
            instruction=instruction + extra_info,
            explanation=f"Full sequence: {' '.join(seq)}. Missing: {answer}")


class TowerOfLondon(BaseParadigm):
    """Tower of London planning task.

    Configs are generated procedurally via BFS to ensure solvability.
    No hints are given -- the participant must plan the full sequence.
    """

    _BALLS = ["R", "G", "B"]
    _PEG_CAPS = [3, 2, 1]  # max balls per peg (classic ToL constraints)

    @staticmethod
    def _state_key(pegs):
        return tuple(tuple(p) for p in pegs)

    @classmethod
    def _bfs_moves(cls, initial, goal):
        """Return minimum moves from initial to goal using BFS."""
        from collections import deque
        start = cls._state_key(initial)
        target = cls._state_key(goal)
        if start == target:
            return 0
        visited = {start}
        queue = deque([(start, 0)])
        while queue:
            state, depth = queue.popleft()
            pegs = [list(p) for p in state]
            for src in range(3):
                if not pegs[src]:
                    continue
                ball = pegs[src][-1]
                for dst in range(3):
                    if dst == src:
                        continue
                    if len(pegs[dst]) >= cls._PEG_CAPS[dst]:
                        continue
                    new_pegs = [list(p) for p in pegs]
                    new_pegs[src] = new_pegs[src][:-1]
                    new_pegs[dst] = new_pegs[dst] + [ball]
                    key = cls._state_key(new_pegs)
                    if key == target:
                        return depth + 1
                    if key not in visited:
                        visited.add(key)
                        queue.append((key, depth + 1))
        return -1  # unsolvable

    @classmethod
    def _generate_config(cls, target_moves):
        """Generate a random (initial, goal) pair requiring exactly target_moves."""
        import itertools
        balls = list(cls._BALLS)
        # Generate all valid placements
        def all_placements():
            results = []
            for perm in itertools.permutations(balls):
                perm = list(perm)
                # Distribute 3 balls across 3 pegs respecting caps [3,2,1]
                for split1 in range(4):
                    for split2 in range(4 - split1):
                        split3 = 3 - split1 - split2
                        if split1 > cls._PEG_CAPS[0] or split2 > cls._PEG_CAPS[1] or split3 > cls._PEG_CAPS[2]:
                            continue
                        pegs = [perm[:split1], perm[split1:split1+split2], perm[split1+split2:]]
                        results.append(pegs)
            return results

        placements = all_placements()
        random.shuffle(placements)
        for initial in placements[:30]:
            random.shuffle(placements)
            for goal in placements[:30]:
                if cls._state_key(initial) == cls._state_key(goal):
                    continue
                moves = cls._bfs_moves(initial, goal)
                if moves == target_moves:
                    return {"initial": initial, "goal": goal, "moves": moves}
        # Fallback: return any config found
        for initial in placements[:50]:
            for goal in placements[:50]:
                if cls._state_key(initial) == cls._state_key(goal):
                    continue
                moves = cls._bfs_moves(initial, goal)
                if moves >= max(2, target_moves - 1):
                    return {"initial": initial, "goal": goal, "moves": moves}
        return {"initial": [[], balls, []], "goal": [balls, [], []], "moves": 3}

    @property
    def meta(self):
        return ParadigmMeta(
            id="tower_of_london", label="Tower of London",
            reference="Shallice, T. (1982). Specific impairments of planning. Philosophical Transactions of the Royal Society B, 298(1089), 199-209.",
            description="Determine the minimum number of moves to reach the goal configuration. Example: count the fewest ball moves to rearrange colored balls across three pegs from start to target.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.GRID,
            base_time_sec=30, category="Executive",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        # Add randomness so steps are not predictable per difficulty
        base_moves = min(2 + difficulty, 7)
        jitter = random.choice([-1, 0, 0, 1])  # slight variation
        target_moves = max(2, min(7, base_moves + jitter))
        config = self._generate_config(target_moves)
        return self._trial(
            difficulty, time_limit,
            stimulus={"initial": config["initial"], "goal": config["goal"],
                      "peg_labels": ["A", "B", "C"]},
            correct_answer=str(config["moves"]),
            instruction="How many MOVES minimum to go from INITIAL to GOAL? (Each move = one ball, one peg)",
            explanation=f"Minimum moves: {config['moves']}.")


class TaskSwitching(BaseParadigm):
    def __init__(self):
        self._prev_rule: str | None = None
        self._last_rule_count: int = 2

    def reset(self):
        self._prev_rule = None
        self._last_rule_count = 2

    @property
    def meta(self):
        return ParadigmMeta(
            id="task_switching", label="Task Switching",
            reference="Monsell, S. (2003). Task switching. Trends in Cognitive Sciences, 7(3), 134-140.",
            description="Alternate between classification rules on the same stimuli. Example: for the number 7, if the rule is 'parity' answer ODD; if 'magnitude' answer HIGH.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.TEXT,
            base_time_sec=10, category="Executive")

    def generate_trial(self, difficulty, time_limit):
        # Number range scales with difficulty
        max_num = min(9 + difficulty * 3, 30)
        number = random.randint(1, max_num)

        # Available rules scale with difficulty
        rules = ["parity", "magnitude"]
        if difficulty >= 3:
            rules.append("divisible_by_3")
        if difficulty >= 5:
            rules.append("prime")

        # Force a rule switch on ~70% of trials to create switch cost
        if self._prev_rule and random.random() < 0.70:
            candidates = [r for r in rules if r != self._prev_rule]
            rule = random.choice(candidates) if candidates else random.choice(rules)
        else:
            rule = random.choice(rules)

        is_switch = self._prev_rule is not None and rule != self._prev_rule
        self._prev_rule = rule

        # Emit rule_change_notice when a new rule type is unlocked
        rule_change_notice = ""
        if len(rules) > self._last_rule_count:
            new_rule = rules[-1]
            if new_rule == "divisible_by_3":
                rule_change_notice = "New rule added: DIVISIBLE BY 3? Some trials will now ask if the number is divisible by 3. Press Y (yes) or N (no)."
            elif new_rule == "prime":
                rule_change_notice = "New rule added: PRIME NUMBER? Some trials will now ask if the number is a prime. Press Y (yes) or N (no)."
            self._last_rule_count = len(rules)

        if rule == "parity":
            answer = "EVEN" if number % 2 == 0 else "ODD"
            cue = "ODD / EVEN ?"
            options = [{"key": "e", "label": "EVEN"}, {"key": "o", "label": "ODD"}]
        elif rule == "magnitude":
            threshold = 5 if max_num <= 12 else max_num // 2
            answer = "HIGH" if number > threshold else "LOW"
            cue = f"HIGH (>{threshold}) / LOW (<={threshold}) ?"
            options = [{"key": "h", "label": "HIGH"}, {"key": "l", "label": "LOW"}]
        elif rule == "divisible_by_3":
            answer = "YES" if number % 3 == 0 else "NO"
            cue = "DIVISIBLE BY 3 ?"
            options = [{"key": "y", "label": "YES"}, {"key": "n", "label": "NO"}]
        else:  # prime
            primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29}
            answer = "YES" if number in primes else "NO"
            cue = "PRIME NUMBER ?"
            options = [{"key": "y", "label": "YES"}, {"key": "n", "label": "NO"}]

        return self._trial(
            difficulty, time_limit,
            stimulus={"display": str(number), "number": number,
                      "rule": rule, "cue": cue,
                      "is_switch": is_switch,
                      "task_switching": True,
                      "rule_change_notice": rule_change_notice,
                      "keyboard_options": options},
            correct_answer=answer,
            instruction=f"Rule: {cue} Press the matching key.",
            explanation=f"Number: {number}, Rule: {rule}, Switch: {is_switch}. Answer: {answer}")
