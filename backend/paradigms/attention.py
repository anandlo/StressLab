import random
from .base import BaseParadigm
from ..models import ParadigmMeta, Trial, InputMode, StimulusType


class Flanker(BaseParadigm):
    """Eriksen Flanker task -- stress-inducing variant.

    Per Eriksen & Eriksen (1974), flanker interference depends on spatial
    proximity. This variant adds: per-arrow rotation jitter, variable sizing,
    noise characters mixed among arrows, and strong 2D spatial displacement
    to prevent pre-fixation strategies. At high difficulty, visually similar
    non-arrow symbols (chevrons, angle brackets) are interleaved among real
    arrows, making the center arrow much harder to isolate.
    """

    # Arrow symbols -- only real directional arrows, no ambiguous brackets/chevrons
    _ARROWS_LEFT = ["\u2190", "\u21e6", "\u2b05"]          # ←  ⇦  ⬅
    _ARROWS_RIGHT = ["\u2192", "\u21e8", "\u27a1"]         # →  ⇨  ➡
    _NOISE_ARROWS = ["\u2194", "\u2195", "\u21c4", "\u21cb"]  # bidirectional distractors

    @property
    def meta(self):
        return ParadigmMeta(
            id="flanker", label="Eriksen Flanker",
            reference="Eriksen, B.A. & Eriksen, C.W. (1974). Effects of noise letters upon identification of a target letter. Perception & Psychophysics, 16(1), 143-149.",
            description="Identify the direction of the center arrow among flanking distractors. Example: arrows show <<><< and you press RIGHT for the center arrow.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.ARROWS,
            base_time_sec=3, category="Attention")

    def generate_trial(self, difficulty, time_limit):
        target = random.choice(["LEFT", "RIGHT"])
        pool_left = self._ARROWS_LEFT
        pool_right = self._ARROWS_RIGHT

        # Center arrow drawn from the same pool available at this difficulty
        if difficulty >= 3:
            target_arrow = random.choice(pool_left if target == "LEFT" else pool_right)
        else:
            target_arrow = "\u2190" if target == "LEFT" else "\u2192"

        n_flankers = min(3 + difficulty // 2, 7)

        # Build flanker symbol pool -- only real arrows, no brackets/chevrons
        if difficulty >= 5:
            flanker_pool = pool_left + pool_right + self._NOISE_ARROWS
        elif difficulty >= 3:
            flanker_pool = pool_left[:2] + pool_right[:2] + self._NOISE_ARROWS[:2]
        else:
            flanker_pool = ["\u2190", "\u2192"]

        # Every flanker position is chosen completely independently --
        # no mirroring, no shared pool result, no forced congruence pattern.
        def random_flanker():
            return random.choice(flanker_pool)

        left_flankers = [random_flanker() for _ in range(n_flankers)]
        right_flankers = [random_flanker() for _ in range(n_flankers)]

        # Determine congruence from what was actually generated so the
        # explanation is accurate (congruent = all flankers match target direction).
        all_flankers = left_flankers + right_flankers
        congruent_left = self._ARROWS_LEFT
        congruent_right = self._ARROWS_RIGHT
        if target == "LEFT":
            is_congruent = all(ch in congruent_left for ch in all_flankers)
        else:
            is_congruent = all(ch in congruent_right for ch in all_flankers)

        arrows = left_flankers + [target_arrow] + right_flankers

        # Per-character rotation jitter at difficulty >= 3
        char_rotations = []
        for i, ch in enumerate(arrows):
            if i == n_flankers:
                # Center arrow: no rotation
                char_rotations.append(0)
            elif difficulty >= 3:
                char_rotations.append(random.choice([-15, -10, -5, 0, 5, 10, 15]))
            else:
                char_rotations.append(0)

        # Variable sizes per character at difficulty >= 4
        char_sizes = []
        size_classes = ["text-lg", "text-xl", "text-2xl", "text-3xl"]
        for i in range(len(arrows)):
            if i == n_flankers:
                # Center arrow: same size as flankers (no size pop-out)
                char_sizes.append(random.choice(size_classes[1:3]))
            elif difficulty >= 4:
                char_sizes.append(random.choice(size_classes))
            else:
                char_sizes.append("text-2xl")

        display = "".join(arrows)
        # Constrained jitter: keep arrows within center safe zone
        y_offset_vh = random.uniform(-6, 6)
        x_offset_vw = random.uniform(-10, 10)

        return self._trial(
            difficulty, time_limit,
            stimulus={"display": display, "target": target,
                      "congruent": is_congruent,
                      "n_flankers": n_flankers,
                      "tight_spacing": True,
                      "arrows_array": arrows,
                      "char_rotations": char_rotations,
                      "char_sizes": char_sizes,
                      "per_char_render": difficulty >= 3,
                      "arrow_size": "text-2xl",
                      "y_offset_vh": y_offset_vh,
                      "x_offset_vw": x_offset_vw,
                      "keyboard_options": [
                          {"key": "ArrowLeft", "label": "\u2190 LEFT"},
                          {"key": "ArrowRight", "label": "\u2192 RIGHT"}]},
            correct_answer=target,
            instruction="Press the arrow key matching the CENTER arrow. Respond quickly.",
            explanation=f"Center: {target}. Flankers: {'congruent' if is_congruent else 'incongruent'}. {n_flankers} per side.")


class PVT(BaseParadigm):
    """Psychomotor Vigilance Task -- stress-inducing countdown variant.

    Per Dinges & Powell (1985): after a random foreperiod, a
    millisecond counter appears. In our stress variant the counter
    counts DOWN from a deadline. The participant must press spacebar
    before it hits zero. The deadline shrinks with difficulty, making
    later trials nearly impossible. If they miss the deadline the trial
    is a failure (lapse).
    """

    @property
    def meta(self):
        return ParadigmMeta(
            id="pvt", label="Psychomotor Vigilance",
            reference="Dinges, D.F. & Powell, J.W. (1985). Microcomputer analyses of performance on a portable simple visual RT task. Behavior Research Methods, 17(6), 652-655.",
            description="Press spacebar before the countdown hits zero. The window shrinks as difficulty rises.",
            input_mode=InputMode.SPACEBAR, stimulus_type=StimulusType.TEXT,
            base_time_sec=5, category="Attention",
            metric_focus="speed")

    # Countdown deadlines by difficulty (ms)
    _DEADLINES = [700, 500, 400, 300, 200, 150, 100]

    def generate_trial(self, difficulty, time_limit):
        wait_ms = random.randint(1000, max(1500, 4000 - difficulty * 300))
        # Countdown shrinks: 700, 500, 400, 300, 200, 150, 100
        idx = min(difficulty - 1, len(self._DEADLINES) - 1)
        countdown_ms = self._DEADLINES[max(0, idx)]
        # Total trial time must accommodate the full wait + full countdown + buffer
        time_limit = (wait_ms + countdown_ms) / 1000.0 + 0.5
        # Window scale: the visible countdown box shrinks with difficulty
        window_scale = max(0.5, 1.0 - difficulty * 0.07)
        return self._trial(
            difficulty, time_limit,
            stimulus={"wait_ms": wait_ms,
                      "pvt_counter": True,
                      "countdown_ms": countdown_ms,
                      "window_scale": window_scale},
            correct_answer="GO",
            instruction="Press SPACEBAR before the countdown reaches zero. Do NOT press early!",
            explanation=f"RT task. Foreperiod: {wait_ms}ms. Deadline: {countdown_ms}ms.")

    def check_answer(self, trial: Trial, response: str) -> bool:
        r = response.strip().upper()
        # Only "GO" (pressed during countdown) is correct; "EARLY" = premature
        return r == "GO"


class CPT(BaseParadigm):
    """Continuous Performance Test -- matrix-search stress variant.

    Low difficulty: a single large letter appears; press for target X.
    Medium difficulty (>= 3): the letter is embedded in a small matrix of
      random distractor letters. The participant must scan to find the
      target.
    High difficulty (>= 5): the matrix grows larger (up to 5x5), font size
      shrinks, and visually confusing distractors are used.

    Rule changes (target letter switches, matrix introduction) are
    signaled via rule_change_notice so the frontend can pause and
    explain before continuing.

    Per Rosvold et al. (1956) for standard CPT.
    """

    _TARGETS = ["X", "K", "Z"]

    def __init__(self):
        self._target_idx: int = 0
        self._last_rule_tier: int = 0

    def reset(self):
        self._target_idx = 0
        self._last_rule_tier = 0

    @property
    def meta(self):
        return ParadigmMeta(
            id="cpt", label="Continuous Performance",
            reference="Rosvold, H.E., Mirsky, A.F., Sarason, I., Bransome, E.D., & Beck, L.H. (1956). A continuous performance test of brain damage. Journal of Consulting Psychology, 20(5), 343-350.",
            description="Press spacebar when you see the target letter among distractors. The matrix grows as difficulty increases.",
            input_mode=InputMode.SPACEBAR, stimulus_type=StimulusType.LETTER_STREAM,
            base_time_sec=2, category="Attention")

    def generate_trial(self, difficulty, time_limit):
        target = self._TARGETS[self._target_idx % len(self._TARGETS)]
        confusing = list("YKVWMN")
        all_letters = list("ABCDEFGHJKLMNOPQRSTUVWYZ")

        # Determine rule tier
        if difficulty >= 5:
            rule_tier = 3
        elif difficulty >= 3:
            rule_tier = 2
        elif difficulty >= 2:
            rule_tier = 1
        else:
            rule_tier = 0

        # Switch target letter at tier transitions for extra stress
        rule_change_notice = ""
        if rule_tier != self._last_rule_tier:
            if rule_tier >= 2 and self._last_rule_tier < 2:
                self._target_idx += 1
                target = self._TARGETS[self._target_idx % len(self._TARGETS)]
                rule_change_notice = f"New rule: target letter is now '{target}'. Letters will appear in a matrix -- find the target and press SPACE."
            elif rule_tier == 1:
                rule_change_notice = f"Target letter: '{target}'. Confusing look-alike letters will appear more often."
            elif rule_tier == 3:
                self._target_idx += 1
                target = self._TARGETS[self._target_idx % len(self._TARGETS)]
                rule_change_notice = f"New target: '{target}'. Matrix is larger and font is smaller. Stay alert."
            self._last_rule_tier = rule_tier

        # Target probability
        is_target = random.random() < 0.20

        if is_target:
            letter = target
        elif difficulty >= 2:
            letter = random.choice(confusing)
        else:
            letter = random.choice([c for c in all_letters if c != target])

        correct = "GO" if is_target else "NOGO"

        # Matrix mode at difficulty >= 3
        grid = None
        grid_size = 0
        font_size = "6rem"
        if difficulty >= 5:
            grid_size = 5
            font_size = "1.2rem"
        elif difficulty >= 4:
            grid_size = 4
            font_size = "1.6rem"
        elif difficulty >= 3:
            grid_size = 3
            font_size = "2rem"

        if grid_size > 0:
            n_cells = grid_size * grid_size
            pool = confusing + list("BDFHJLNPRSTUW")
            grid_letters = [random.choice(pool) for _ in range(n_cells)]
            pos = random.randint(0, n_cells - 1)
            grid_letters[pos] = letter
            grid = [grid_letters[i * grid_size:(i + 1) * grid_size]
                    for i in range(grid_size)]
        else:
            if difficulty >= 2:
                font_size = "5rem"

        instruction = f"Press SPACEBAR only for '{target}'. Withhold for everything else."

        return self._trial(
            difficulty, time_limit,
            stimulus={"letter": letter, "target": target, "is_target": is_target,
                      "font_size": font_size,
                      "ax_mode": False,
                      "context_hint": "",
                      "grid": grid,
                      "grid_size": grid_size,
                      "rule_change_notice": rule_change_notice},
            correct_answer=correct,
            instruction=instruction,
            explanation=f"Letter: {letter}. Target: {target}. {'Press' if is_target else 'Withhold'}.")

    def check_answer(self, trial: Trial, response: str) -> bool:
        return response.strip().upper() == trial.correct_answer.strip().upper()


class GoNoGo(BaseParadigm):
    """Go/No-Go task -- stress-inducing variant.

    Progressive rule complexity across difficulty levels:
    - Level 1-2: Green circle = GO, red square = NOGO, green square = lure
    - Level 3-4: Add blue diamond as second GO target, triangle lure,
      shapes vary in size, position randomized
    - Level 5+: Rule reversal trials (NOGO for usual GO shapes), extremely
      rapid presentation (0.8s), shape colors that blend (amber, teal)

    Sends a rule_change_notice when the effective rule set changes so
    the frontend can pause and explain the new rules before continuing.
    """

    def __init__(self):
        self._last_rule_tier: int = 0

    def reset(self):
        self._last_rule_tier = 0

    @property
    def meta(self):
        return ParadigmMeta(
            id="go_nogo", label="Go/No-Go",
            reference="Donders, F.C. (1869/1969). On the speed of mental processes. Acta Psychologica, 30, 412-431.",
            description="Press spacebar for GO stimuli and withhold for NO-GO stimuli. Example: press spacebar for a green circle but do NOT press for a red square or green square.",
            input_mode=InputMode.SPACEBAR, stimulus_type=StimulusType.SHAPE,
            base_time_sec=2, category="Attention",
            metric_focus="inhibition")

    def generate_trial(self, difficulty, time_limit):
        # Rapid presentation: cap aggressively
        time_limit = min(time_limit, max(0.8, 1.5 - difficulty * 0.1))

        # Determine rule tier for rule-change notices
        if difficulty >= 5:
            rule_tier = 3
        elif difficulty >= 3:
            rule_tier = 2
        elif difficulty >= 2:
            rule_tier = 1
        else:
            rule_tier = 0

        rule_change_notice = ""
        if rule_tier != self._last_rule_tier:
            if rule_tier == 1:
                rule_change_notice = "New rule: GREEN CIRCLE only = press. GREEN SQUARE (lure) = do NOT press."
            elif rule_tier == 2:
                rule_change_notice = "New rules: GREEN CIRCLE or BLUE DIAMOND = press. Everything else (including green square, blue triangle) = withhold."
            elif rule_tier == 3:
                rule_change_notice = "New rules: REVERSAL TRIALS added. On some trials, the rule flips -- press for what you would normally withhold. Stay alert."
            self._last_rule_tier = rule_tier

        # Rule reversal at difficulty >= 5: on ~20% of trials, go/nogo swap
        is_reversed = difficulty >= 5 and random.random() < 0.20

        if difficulty >= 5:
            # Complex: 2 GO shapes, multiple NOGO + lures, size/position noise
            stimuli = [
                ("circle", "green", "#22c55e", True),
                ("diamond", "blue", "#3b82f6", True),
                ("square", "red", "#ef4444", False),
                ("square", "green", "#22c55e", False),    # green square lure
                ("triangle", "blue", "#3b82f6", False),   # blue triangle lure
                ("circle", "amber", "#f59e0b", False),    # amber circle lure
                ("diamond", "teal", "#14b8a6", False),     # teal diamond lure
                ("square", "purple", "#a855f7", False),
            ]
            weights = [20, 15, 10, 12, 10, 10, 10, 13]  # ~35% go, ~65% nogo
        elif difficulty >= 3:
            stimuli = [
                ("circle", "green", "#22c55e", True),
                ("diamond", "blue", "#3b82f6", True),
                ("square", "red", "#ef4444", False),
                ("square", "green", "#22c55e", False),
                ("triangle", "blue", "#3b82f6", False),
            ]
            weights = [25, 15, 20, 20, 20]  # 40% go, 60% nogo
        elif difficulty >= 2:
            stimuli = [
                ("circle", "green", "#22c55e", True),
                ("square", "red", "#ef4444", False),
                ("square", "green", "#22c55e", False),
            ]
            weights = [50, 25, 25]  # 50% go
        else:
            stimuli = [
                ("circle", "green", "#22c55e", True),
                ("square", "red", "#ef4444", False),
            ]
            weights = [55, 45]

        # Weighted random selection
        total = sum(weights)
        r = random.uniform(0, total)
        cumulative = 0
        shape, color, color_hex, is_go = stimuli[0]
        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                shape, color, color_hex, is_go = stimuli[i]
                break

        # Rule reversal flips go/nogo
        if is_reversed:
            is_go = not is_go

        # Size variability at difficulty >= 3
        if difficulty >= 3:
            size = random.choice([40, 48, 56, 64, 72])
        else:
            size = 56

        # Position randomization at difficulty >= 4
        if difficulty >= 4:
            position = random.choice(["left", "center", "right"])
        else:
            position = "center"

        # Instruction changes with rule complexity
        if is_reversed:
            instruction = "REVERSED RULE! Press for what you'd normally withhold."
        elif difficulty >= 3:
            instruction = "GREEN CIRCLE or BLUE DIAMOND = press. Everything else = withhold."
        elif difficulty >= 2:
            instruction = "GREEN CIRCLE only = press SPACEBAR. Everything else = do NOT press."
        else:
            instruction = "GREEN circle = press SPACEBAR. RED square = do NOT press."

        label = "REVERSE" if is_reversed else ""

        return self._trial(
            difficulty, time_limit,
            stimulus={"shape": shape, "color": color, "color_hex": color_hex,
                      "is_go": is_go, "size": size, "label": label,
                      "position": position if position != "center" else "",
                      "is_reversed": is_reversed,
                      "rule_change_notice": rule_change_notice},
            correct_answer="GO" if is_go else "NOGO",
            instruction=instruction,
            explanation=f"{'GO' if is_go else 'NO-GO'} ({color} {shape}). {'REVERSED. ' if is_reversed else ''}{'Press' if is_go else 'Withhold'}.")

    def check_answer(self, trial: Trial, response: str) -> bool:
        return response.strip().upper() == trial.correct_answer.strip().upper()


class StopSignalTask(BaseParadigm):
    """Stop-signal paradigm measuring response inhibition.

    Per Logan & Cowan (1984): on every trial a directional arrow appears
    and the participant must respond with the matching arrow key. On a
    proportion of trials, after a variable Stop-Signal Delay (SSD), the
    arrow turns red with a STOP label, signaling the participant to withhold.

    Stress mechanisms:
    - Arrow size varies randomly (disorienting)
    - Different arrow symbols used (not just standard arrows)
    - SSD shrinks with difficulty (nearly impossible to stop)
    - No confusing neutral distractor arrows -- focus on the target arrow
    """

    _LEFT_ARROWS = ["\u2190", "\u21e6", "\u276e", "\u2039", "\u25c0"]
    _RIGHT_ARROWS = ["\u2192", "\u21e8", "\u276f", "\u203a", "\u25b6"]
    _SIZES = ["text-3xl", "text-4xl", "text-5xl", "text-6xl", "text-7xl"]

    @property
    def meta(self):
        return ParadigmMeta(
            id="stop_signal", label="Stop-Signal Task",
            reference="Logan, G.D. & Cowan, W.B. (1984). On the ability to inhibit thought and action. Psychological Review, 91(3), 295-327.",
            description="Respond to the arrow direction, but withhold if a stop signal appears. Example: press LEFT for a left arrow, but if it turns red after a short delay, cancel your response.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.ARROWS,
            base_time_sec=3, category="Attention",
            metric_focus="inhibition")

    def generate_trial(self, difficulty, time_limit):
        # Shrink response window with difficulty: 3s base -> ~1.5s at max
        time_limit = max(1.5, time_limit - difficulty * 0.25)

        direction = random.choice(["LEFT", "RIGHT"])

        # Use varied arrow symbols at higher difficulty
        if difficulty >= 4:
            pool = self._LEFT_ARROWS if direction == "LEFT" else self._RIGHT_ARROWS
            arrow = random.choice(pool)
        elif difficulty >= 2:
            pool = (self._LEFT_ARROWS[:3] if direction == "LEFT" else self._RIGHT_ARROWS[:3])
            arrow = random.choice(pool)
        else:
            arrow = "\u2190" if direction == "LEFT" else "\u2192"

        # Random arrow size for disorientation
        if difficulty >= 3:
            arrow_size = random.choice(self._SIZES)
        else:
            arrow_size = "text-5xl"

        # Stop probability: 25% to 45%
        stop_prob = min(0.45, 0.25 + difficulty * 0.03)
        is_stop = random.random() < stop_prob

        # SSD decreases with difficulty: 400ms at easy, 50ms at hard
        ssd_ms = max(50, 400 - difficulty * 50)

        # Just the single arrow -- no confusing neutral distractors
        display = arrow

        return self._trial(
            difficulty, time_limit,
            stimulus={"arrow": display, "direction": direction,
                      "is_stop_trial": is_stop,
                      "stop_signal_delay_ms": ssd_ms if is_stop else 0,
                      "stop_signal_color": "#ef4444",
                      "stop_signal": True,
                      "stop_label": "STOP!" if is_stop else "",
                      "pre_flash": difficulty >= 5 and is_stop,
                      "arrow_size": arrow_size,
                      "y_offset_vh": 0,
                      "x_offset_vw": 0,
                      "keyboard_options": [
                          {"key": "ArrowLeft", "label": "\u2190 LEFT"},
                          {"key": "ArrowRight", "label": "\u2192 RIGHT"}]},
            correct_answer="NOGO" if is_stop else direction,
            instruction="Press the ARROW KEY matching the direction. If it turns RED, DO NOT PRESS.",
            explanation=f"{'STOP (SSD: ' + str(ssd_ms) + 'ms)' if is_stop else 'GO: ' + direction}.")

    def check_answer(self, trial: Trial, response: str) -> bool:
        return response.strip().upper() == trial.correct_answer.strip().upper()


class VisualSearch(BaseParadigm):
    """Visual search paradigm measuring pre-attentive and serial search.

    Reference: Treisman, A.M. & Gelade, G. (1980). A feature-integration theory
    of attention. Cognitive Psychology, 12(1), 97-136.

    At low difficulty the target differs from all distractors in a single feature
    (feature search, pop-out effect). At higher difficulty multiple distractor
    types share features with the target (conjunction search), requiring serial
    scanning. High difficulty adds color noise, size variability, rotations,
    and visually similar decoy symbols.
    """

    # Symbols grouped by visual similarity for conjunction search
    _ROUND = ["\u25cf", "\u25cb", "\u25d0", "\u25d1"]   # filled circle, empty circle, half circles
    _ANGULAR = ["\u25a0", "\u25a1", "\u25b2", "\u25b3", "\u25c6", "\u25c7"]  # squares, triangles, diamonds
    _STAR_LIKE = ["\u2605", "\u2606", "\u271a", "\u2716", "\u2742"]  # stars, crosses, asterisks
    ALL_SYMBOLS = _ROUND + _ANGULAR + _STAR_LIKE

    # Colors for color-noise at high difficulty
    _COLORS = ["#ef4444", "#3b82f6", "#22c55e", "#a855f7", "#f97316", "#6b7280"]
    ROTATIONS = [0, 45, 90, 135, 180, 225, 270, 315]

    @property
    def meta(self):
        return ParadigmMeta(
            id="visual_search", label="Visual Search",
            reference="Treisman, A.M. & Gelade, G. (1980). A feature-integration theory of attention. Cognitive Psychology, 12(1), 97-136.",
            description="Find whether a target symbol is present among distractors in a grid. Example: search a 5x5 grid for a circle among squares and triangles, then press YES or NO.",
            input_mode=InputMode.KEYBOARD, stimulus_type=StimulusType.GRID,
            base_time_sec=10, category="Attention")

    def generate_trial(self, difficulty, time_limit):
        # Grid size scales: 3x3 at easy, up to 7x7 at hardest
        size = min(3 + difficulty // 2, 7)
        n_cells = size * size
        target_present = random.random() < 0.5

        if difficulty <= 2:
            # Feature search: one target type, one distractor type, no noise
            target = random.choice(self._ROUND)
            # Guarantee distractors never contain target
            distractors = [s for s in self._ANGULAR]
            grid = [random.choice(distractors) for _ in range(n_cells)]
            rotations = [0] * n_cells
            colors = [None] * n_cells
            condition = "feature"
        elif difficulty <= 4:
            # Conjunction: target shares shape group with some distractors
            group = random.choice([self._ROUND, self._ANGULAR, self._STAR_LIKE])
            target = random.choice(group)
            similar = [s for s in group if s != target]
            other = [s for s in self.ALL_SYMBOLS if s not in group]
            # Guarantee no target in distractor pool
            distractors = [s for s in (similar + random.sample(other, min(2, len(other)))) if s != target]
            if not distractors:
                distractors = [s for s in self.ALL_SYMBOLS if s != target]
            grid = [random.choice(distractors) for _ in range(n_cells)]
            rotations = [random.choice([0, 90, 180, 270]) for _ in range(n_cells)]
            colors = [None] * n_cells
            condition = "conjunction"
        else:
            # High difficulty: visually similar symbols, rotations, color noise
            group = random.choice([self._ROUND, self._ANGULAR, self._STAR_LIKE])
            target = random.choice(group)
            similar = [s for s in group if s != target]
            all_distractors = [s for s in self.ALL_SYMBOLS if s != target]
            # Weight similar symbols heavily but never include target
            distractors = similar * 3 + all_distractors
            grid = [random.choice(distractors) for _ in range(n_cells)]
            rotations = [random.choice(self.ROTATIONS) for _ in range(n_cells)]
            colors = [random.choice(self._COLORS) for _ in range(n_cells)]
            condition = "conjunction_color_noise"

        if target_present:
            pos = random.randint(0, n_cells - 1)
            grid[pos] = target
            # Keep rotation and color of target cell randomised so it doesn't pop out trivially
            rotations[pos] = random.choice([0, 90, 180, 270]) if difficulty >= 3 else 0
            if colors[pos] is None and difficulty >= 5:
                colors[pos] = random.choice(self._COLORS)

        rows = [grid[i * size:(i + 1) * size] for i in range(size)]
        rot_rows = [rotations[i * size:(i + 1) * size] for i in range(size)]
        color_rows = [colors[i * size:(i + 1) * size] for i in range(size)]

        # Time decreases with difficulty: 7s at diff 1, down to 2.5s at diff 8+
        time_limit_adj = max(2.5, 7.0 - difficulty * 0.65)

        return self._trial(
            difficulty, time_limit_adj,
            stimulus={
                "grid": rows,
                "rotations": rot_rows,
                "colors": color_rows,
                "target": target,
                "size": size,
                "condition": condition,
                "target_present": target_present,
                "keyboard_options": [
                    {"key": "y", "label": "YES"},
                    {"key": "n", "label": "NO"},
                ],
            },
            correct_answer="YES" if target_present else "NO",
            instruction=f"Is '{target}' present in the grid?  Y = YES  N = NO",
            explanation=f"Target '{target}' was {'present' if target_present else 'absent'} ({condition} search, {size}x{size} grid).")
