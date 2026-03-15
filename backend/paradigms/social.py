import random
from .base import BaseParadigm
from ..models import ParadigmMeta, InputMode, StimulusType


class SpeechPrep(BaseParadigm):
    TOPICS = [
        "Describe why you are the ideal candidate for your dream job.",
        "Defend an unpopular opinion on a controversial topic.",
        "Explain a major personal failure and what you learned from it.",
        "Present your greatest weakness to a panel of evaluators.",
        "Argue why your work is more valuable than your peers'.",
        "Describe a situation where you made a serious mistake under pressure.",
        "Explain to a skeptical audience why your research matters.",
        "Present a 2-minute summary of your qualifications without preparation.",
    ]

    @property
    def meta(self):
        return ParadigmMeta(
            id="speech_prep", label="Speech Preparation (TSST)",
            reference="Kirschbaum, C., Pirke, K.M., & Hellhammer, D.H. (1993). The 'Trier Social Stress Test' - a tool for investigating psychobiological stress responses in a laboratory setting. Neuropsychobiology, 28(1-2), 76-81.",
            description="Prepare a speech on a stressful topic under time pressure.",
            input_mode=InputMode.NONE, stimulus_type=StimulusType.TIMER_ONLY,
            base_time_sec=60, category="Social-Evaluative")

    def generate_trial(self, difficulty, time_limit):
        topic = random.choice(self.TOPICS)
        prep_time = max(30, 90 - difficulty * 10)
        return self._trial(
            difficulty, prep_time,
            stimulus={"topic": topic, "phase": "preparation",
                      "panel_note": "A panel of evaluators will assess your speech.",
                      "is_timer_only": True},
            correct_answer="DONE",
            instruction="Prepare your speech. The timer shows your remaining preparation time.",
            explanation="Social-evaluative stress: anticipatory anxiety from upcoming speech task.")

    def check_answer(self, trial, response):
        return True  # Timer-only task, always "correct" when time expires


class ColdPressorTimer(BaseParadigm):
    @property
    def meta(self):
        return ParadigmMeta(
            id="cold_pressor", label="Cold Pressor Timer",
            reference="Lovallo, W. (1975). The cold pressor test and autonomic function. Psychophysiology, 12(3), 268-282.",
            description="Timer and instructions for the cold pressor physical stressor.",
            input_mode=InputMode.NONE, stimulus_type=StimulusType.TIMER_ONLY,
            base_time_sec=60, category="Physical")

    def generate_trial(self, difficulty, time_limit):
        duration = min(120, 30 + difficulty * 15)
        return self._trial(
            difficulty, duration,
            stimulus={"instructions": [
                          "Submerge your non-dominant hand in the ice water (0-4 C).",
                          "Keep your hand submerged for the full duration if possible.",
                          "Report your pain level when prompted.",
                          "You may withdraw your hand at any time."],
                      "safety_note": "Withdraw immediately if you experience numbness or sharp pain.",
                      "is_timer_only": True,
                      "duration_sec": duration},
            correct_answer="DONE",
            instruction="Follow the cold pressor protocol. Timer shows remaining time.",
            explanation="Cold pressor task: physical stressor activating sympathetic nervous system.")

    def check_answer(self, trial, response):
        return True  # Timer-only task


class MASTProtocol(BaseParadigm):
    """Maastricht Acute Stress Test combining arithmetic with cold pressor stress."""

    @property
    def meta(self):
        return ParadigmMeta(
            id="mast", label="MAST Protocol",
            reference="Smeets, T., Cornelisse, S., Quaedflieg, C.W., Meyer, T., Jelicic, M., & Merckelbach, H. (2012). Introducing the Maastricht Acute Stress Test (MAST). Psychoneuroendocrinology, 37(12), 1998-2008.",
            description="Alternating mental arithmetic and cold pressor immersion blocks.",
            input_mode=InputMode.TEXT, stimulus_type=StimulusType.TEXT,
            base_time_sec=30, category="Social-Evaluative")

    def generate_trial(self, difficulty, time_limit):
        is_arithmetic = random.random() < 0.6
        if is_arithmetic:
            start = random.randint(200, 999)
            step = random.choice([7, 13, 17])
            answer = start - step
            return self._trial(
                difficulty, time_limit,
                stimulus={"question": f"{start} - {step} = ?",
                          "phase": "arithmetic",
                          "prompt": f"Subtract {step} from {start}. Type the answer."},
                correct_answer=str(answer),
                instruction=f"Calculate: {start} - {step}",
                explanation=f"{start} - {step} = {answer}")
        else:
            duration = min(90, 30 + difficulty * 10)
            return self._trial(
                difficulty, duration,
                stimulus={"instructions": [
                              "Submerge your non-dominant hand in ice water (0-4 C).",
                              "Keep submerged for the full duration.",
                              "You may withdraw at any time for safety."],
                          "phase": "cold_pressor",
                          "is_timer_only": True,
                          "duration_sec": duration,
                          "safety_note": "Withdraw if you experience numbness."},
                correct_answer="DONE",
                instruction="Cold pressor block. Follow the protocol.",
                explanation="MAST cold pressor phase: physical stress component.")

    def check_answer(self, trial, response):
        if trial.stimulus.get("phase") == "cold_pressor":
            return True
        return response.strip() == trial.correct_answer.strip()
