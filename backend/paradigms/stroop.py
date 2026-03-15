import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType

# All colors -- used for words, distractors, borders, backgrounds
COLORS = {
    "RED": "#ef4444", "BLUE": "#3b82f6", "GREEN": "#22c55e",
    "YELLOW": "#eab308", "PURPLE": "#a855f7", "ORANGE": "#f97316",
    "PINK": "#ec4899", "CYAN": "#06b6d4", "TEAL": "#14b8a6",
    "LIME": "#84cc16", "MAGENTA": "#d946ef", "INDIGO": "#6366f1",
    "MAROON": "#b91c1c", "NAVY": "#1e3a5f", "CORAL": "#f97171",
    "GOLD": "#ca8a04", "CRIMSON": "#dc2626", "AQUA": "#22d3ee",
    "VIOLET": "#8b5cf6", "BROWN": "#92400e", "BLACK": "#111111",
    "GRAY": "#6b7280", "SILVER": "#9ca3af",
}
COLOR_NAMES = list(COLORS.keys())

# Simple, everyday color names used as the correct answer (ink color).
# Restricted to names that are immediately recognisable and easy to type.
ANSWER_COLORS = {
    "RED": "#ef4444", "BLUE": "#3b82f6", "GREEN": "#22c55e",
    "YELLOW": "#eab308", "PURPLE": "#a855f7", "ORANGE": "#f97316",
    "PINK": "#ec4899", "CYAN": "#06b6d4", "MAROON": "#b91c1c",
    "BROWN": "#92400e", "NAVY": "#1e3a5f", "BLACK": "#111111",
    "GOLD": "#ca8a04",
}
ANSWER_COLOR_NAMES = list(ANSWER_COLORS.keys())

STRESS_WORDS = [
    "FAILURE", "DEADLINE", "MISTAKE", "PANIC", "PRESSURE",
    "THREAT", "DANGER", "EXAM", "JUDGE", "PENALTY",
    "REJECTED", "FIRED", "CRITICIZED", "TENSE", "ANXIOUS",
    "OVERWHELM", "DREAD", "HOPELESS", "SHAME", "GUILT",
    "CONFLICT", "ALARM", "CRISIS", "BURDEN", "HUMILIATE",
    "SCREAM", "SUFFER", "PUNISH", "DISTRESS", "BLAME",
]
NEUTRAL_WORDS = [
    "TABLE", "WINDOW", "PENCIL", "CARPET", "BOTTLE",
    "GARDEN", "BASKET", "MIRROR", "PILLOW", "FOLDER",
    "UMBRELLA", "LANTERN", "CABINET", "BLANKET", "STATION",
    "CURTAIN", "SHOVEL", "PICTURE", "BUTTON", "HAMMER",
]

# Font families for visual disruption at high difficulty
_FONTS = [
    "serif", "sans-serif", "monospace", "cursive", "fantasy",
    "Georgia, serif", "Courier New, monospace", "Impact, sans-serif",
    "Trebuchet MS, sans-serif", "Verdana, sans-serif",
    "Palatino Linotype, serif", "Lucida Console, monospace",
    "Comic Sans MS, cursive", "Arial Black, sans-serif",
    "Garamond, serif", "Bookman Old Style, serif",
]

# Fonts that tend to overflow boxes -- cap their size
_OVERFLOW_FONTS = {"cursive", "fantasy", "Comic Sans MS, cursive"}


def _stroop_visual_noise(difficulty, ink_color_name=None):
    """Generate visual noise fields for stress-inducing Stroop.

    ink_color_name is passed so that bg_color and border_color can be
    guaranteed different from the ink to avoid invisible text.
    """
    result = {}
    exclude = {ink_color_name} if ink_color_name else set()

    if difficulty >= 2:
        font = random.choice(_FONTS)
        result["font_family"] = font
        # Cap font size for fonts prone to overflow
        if font in _OVERFLOW_FONTS:
            result["overflow_safe"] = True
    if difficulty >= 3:
        safe = [c for c in COLOR_NAMES if c not in exclude]
        border_color = random.choice(safe) if safe else random.choice(COLOR_NAMES)
        result["border_color"] = COLORS[border_color]
    if difficulty >= 4:
        safe = [c for c in COLOR_NAMES if c not in exclude]
        bg_color = random.choice(safe) if safe else random.choice(COLOR_NAMES)
        result["bg_color"] = COLORS[bg_color]
    if difficulty >= 5:
        result["font_size"] = random.choice(["2.5rem", "3rem", "3.5rem", "4rem", "4.5rem"])
        result["letter_spacing"] = random.choice(["0.05em", "0.1em", "0.15em", "0.2em", "-0.02em"])
    return result


class ClassicStroop(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="stroop", label="Stroop Color-Word",
            reference="Stroop, J.R. (1935). Studies of interference in serial verbal reactions. Journal of Experimental Psychology, 18(6), 643-662.",
            description="Name the ink color of a word that spells a different color. Example: the word 'RED' displayed in blue ink - type 'BLUE'.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.STROOP,
            base_time_sec=8, category="Attention",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        # At higher difficulty, present double-incongruent stimuli:
        # the word is one color name, displayed in a DIFFERENT ink color,
        # and a third color name is shown as a small distractor label.
        word = random.choice(COLOR_NAMES)
        ink = random.choice([c for c in ANSWER_COLOR_NAMES if c != word])
        distractor = None
        if difficulty >= 3:
            others = [c for c in COLOR_NAMES if c != word and c != ink]
            if others:
                distractor = random.choice(others)
        noise = _stroop_visual_noise(difficulty, ink_color_name=ink)
        return self._trial(
            difficulty, time_limit,
            stimulus={"word": word, "ink_color": ANSWER_COLORS[ink], "ink_name": ink,
                      "distractor": distractor, **noise},
            correct_answer=ink,
            instruction="Type the INK COLOR of the large word. Ignore the word itself, borders, backgrounds, and any small text.",
            explanation=f'The word "{word}" is displayed in {ink} ink. Correct answer: {ink}')


class EmotionalStroop(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="emotional_stroop", label="Emotional Stroop",
            reference="Williams, J.M.G., Mathews, A., & MacLeod, C. (1996). The emotional Stroop task and psychopathology. Psychological Bulletin, 120(1), 3-24.",
            description="Name the ink color of stress-relevant or neutral words. Example: the word 'FAILURE' in green ink - type 'GREEN', ignoring the word meaning.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.STROOP,
            base_time_sec=8, category="Attention",
            metric_focus="accuracy")

    def generate_trial(self, difficulty, time_limit):
        is_stress = random.random() < (0.5 + difficulty * 0.05)  # more stress words at higher difficulty
        word = random.choice(STRESS_WORDS if is_stress else NEUTRAL_WORDS)
        ink = random.choice(ANSWER_COLOR_NAMES)
        distractor = None
        if difficulty >= 3:
            others = [c for c in COLOR_NAMES if c != ink]
            if others:
                distractor = random.choice(others)
        noise = _stroop_visual_noise(difficulty, ink_color_name=ink)
        return self._trial(
            difficulty, time_limit,
            stimulus={"word": word, "ink_color": ANSWER_COLORS[ink], "ink_name": ink,
                      "is_stress_word": is_stress, "distractor": distractor, **noise},
            correct_answer=ink,
            instruction="Type the INK COLOR of the large word. Ignore the word itself, borders, backgrounds, and any small text.",
            explanation=f'The word "{word}" is displayed in {ink} ink. Correct answer: {ink}')
