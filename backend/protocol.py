from .models import ProtocolPreset, Intensity

PROTOCOL_PRESETS = [
    ProtocolPreset(
        id="tsst_like",
        name="TSST-Like Protocol",
        description=(
            "Modeled after the Trier Social Stress Test. Three escalating stressors: "
            "Speech Prep (open-ended verbal task under simulated evaluation pressure), "
            "Serial Subtraction (counting backwards from 1022 by 13; rule adds restart-on-error from difficulty 3), "
            "and Mental Arithmetic (pure speed-accuracy arithmetic). "
            "No working-memory tasks. Rule changes are announced on-screen when the error-restart rule activates. "
            "High intensity means time limits tighten as difficulty climbs."
        ),
        paradigm_ids=["speech_prep", "serial_subtraction", "mental_arithmetic"],
        duration_min=10,
        intensity=Intensity.HIGH,
        blocks=2,
        rest_duration_sec=30,
    ),
    ProtocolPreset(
        id="cognitive_battery",
        name="Cognitive Battery",
        description=(
            "Ten paradigms across four cognitive domains: arithmetic (Serial Subtraction, Mental Arithmetic, PASAT), "
            "attention (Stroop, Flanker), working memory (N-back, Digit Span), and executive function (Go/No-Go, Task Switching, Pattern Completion). "
            "Two memory tasks are included (N-back and Digit Span). They are separated by non-memory tasks across blocks to prevent carry-over fatigue. "
            "Rule changes to expect: Stroop adds fonts and expands the color set above difficulty 3; "
            "CPT (if added) switches the target letter between rule tiers; "
            "Go/No-Go adds a second GO shape (blue diamond) at difficulty 3 and introduces reversal trials at difficulty 5. "
            "Three blocks with 45 s rest allow partial physiological recovery between segments."
        ),
        paradigm_ids=[
            "serial_subtraction", "mental_arithmetic", "pasat", "stroop",
            "n_back", "flanker", "go_nogo", "task_switching",
            "pattern_completion", "digit_span",
        ],
        duration_min=15,
        intensity=Intensity.MEDIUM,
        blocks=3,
        rest_duration_sec=45,
    ),
    ProtocolPreset(
        id="quick_stress",
        name="Quick Stress (5 min)",
        description=(
            "High-intensity single-block protocol for short recording windows. "
            "Includes MIST (adaptive arithmetic with false negative feedback to induce social-evaluative stress), "
            "Stroop (color-word interference), Flanker (direction interference), "
            "Serial Subtraction, and N-back (2-back). "
            "One working memory task (N-back) is present; it runs independently of the arithmetic tasks. "
            "No rest period. Difficulty ramps rapidly because high intensity caps at 7."
        ),
        paradigm_ids=["mist", "stroop", "flanker", "serial_subtraction", "n_back"],
        duration_min=5,
        intensity=Intensity.HIGH,
        blocks=1,
        rest_duration_sec=0,
    ),
    ProtocolPreset(
        id="attention_focus",
        name="Attention Focus",
        description=(
            "Seven sustained attention and response inhibition paradigms: "
            "Flanker (congruent vs. incongruent arrow arrays), Go/No-Go (shape-based GO/NOGO with progressive rule complexity), "
            "PVT (vigilance probe with adaptive timing window), CPT (letter target in a stream or matrix), "
            "Simon Task (spatial compatibility), Stroop (color-word), and Stop Signal (SSRT measurement). "
            "No working memory tasks. "
            "Rule changes: Go/No-Go announces a new rule when the shape set expands at difficulty 3 and again when reversal trials begin at difficulty 5. "
            "CPT announces a new target letter when the rule tier advances past difficulty 2. "
            "Stop Signal varies its stop-signal delay adaptively without an explicit announcement (by design). "
            "Suitable for ERP, pupillometry, or eye-tracking studies targeting inhibition-related components."
        ),
        paradigm_ids=["flanker", "go_nogo", "pvt", "cpt", "simon_task", "stroop", "stop_signal"],
        duration_min=10,
        intensity=Intensity.MEDIUM,
        blocks=2,
        rest_duration_sec=30,
    ),
    ProtocolPreset(
        id="executive_function",
        name="Executive Function",
        description=(
            "Five paradigms targeting cognitive flexibility, planning, and set-shifting: "
            "WCST (implicit rule shifts among color, shape, count — the rule changes without warning by design, matching the original paradigm), "
            "Trail Making (alternates number and letter sequences; rule switches between number-only and number-letter interleaving at difficulty 3), "
            "Task Switching (explicit auditory/visual rule cues that alternate each trial above difficulty 2), "
            "Tower of London (disk-planning with increasing move constraints), "
            "and N-back (2-back sequential working memory). "
            "N-back is the only working memory task; it is scheduled last within each block to avoid contaminating the planning tasks. "
            "WCST rule shifts are silent by design; all other rule changes are announced on-screen."
        ),
        paradigm_ids=["wcst", "trail_making", "task_switching", "tower_of_london", "n_back"],
        duration_min=12,
        intensity=Intensity.MEDIUM,
        blocks=2,
        rest_duration_sec=30,
    ),
    ProtocolPreset(
        id="mist_protocol",
        name="MIST Protocol",
        description=(
            "Single-paradigm protocol implementing the Montreal Imaging Stress Test. "
            "The adaptive algorithm targets a performance level slightly below the participant's ability, "
            "and the interface displays false comparisons to norms to generate social-evaluative pressure. "
            "Three blocks of arithmetic interspersed with 30 s rest periods. "
            "No rule changes between trials; difficulty adapts continuously within each block. "
            "Produces reliable HPA-axis and autonomic nervous system responses suitable for fMRI or ECG/EDA studies."
        ),
        paradigm_ids=["mist"],
        duration_min=10,
        intensity=Intensity.HIGH,
        blocks=3,
        rest_duration_sec=30,
    ),
    ProtocolPreset(
        id="full_comprehensive",
        name="Full Comprehensive",
        description=(
            "All 27 paradigms across arithmetic, attention, working memory, executive function, spatial, and social domains. "
            "Four working memory tasks are included (N-back, Digit Span, Operation Span, Sternberg). "
            "To prevent interference: memory tasks are distributed across separate blocks and are not placed consecutively; "
            "Stroop and Emotional Stroop (both color-word paradigms) are separated by at least two other tasks. "
            "Rule changes expected across the session: "
            "Go/No-Go rule tier transitions (announcements at difficulties 3 and 5), "
            "CPT target letter switches (announced at rule tier changes), "
            "Stroop color/font set expansions (announced above difficulty 3), "
            "Serial Subtraction error-restart rule (announced at difficulty 3), "
            "Trail Making sequence rule (announced at difficulty 3). "
            "WCST rule shifts remain silent by design. "
            "Five 60 s rest periods allow physiological recovery between blocks."
        ),
        paradigm_ids=[
            "serial_subtraction", "mental_arithmetic", "pasat",
            "stroop", "emotional_stroop",
            "n_back", "digit_span", "operation_span", "sternberg",
            "flanker", "pvt", "cpt", "go_nogo", "stop_signal",
            "wcst", "trail_making", "tower_of_london", "task_switching",
            "mental_rotation", "simon_task", "pattern_completion",
            "mist", "rapid_comparison", "dual_task",
            "speech_prep", "cold_pressor", "mast",
        ],
        duration_min=30,
        intensity=Intensity.MEDIUM,
        blocks=5,
        rest_duration_sec=60,
    ),
    ProtocolPreset(
        id="inhibition_battery",
        name="Inhibition Battery",
        description=(
            "Five response inhibition paradigms targeting different inhibitory mechanisms: "
            "Go/No-Go (shape-rule suppression), Stop Signal (proactive SSRT-based stopping with adaptive SSD), "
            "Flanker (distractor interference suppression), CPT (sustained vigilance with target detection), "
            "Simon Task (spatial compatibility conflict). "
            "No working memory tasks. "
            "Go/No-Go and Stop Signal both require stopping motor responses but via distinct mechanisms "
            "(shape identity vs. acoustic stop signal); placing them in different blocks reduces response-strategy carry-over. "
            "Rule changes: Go/No-Go announces new rules at difficulty tiers 3 and 5; "
            "CPT announces new target letters at tier transitions. "
            "Stop Signal delay adapts silently throughout."
        ),
        paradigm_ids=["go_nogo", "stop_signal", "flanker", "cpt", "simon_task"],
        duration_min=10,
        intensity=Intensity.MEDIUM,
        blocks=2,
        rest_duration_sec=30,
    ),
    ProtocolPreset(
        id="mast_protocol",
        name="MAST Protocol",
        description=(
            "Single-paradigm protocol implementing the Maastricht Acute Stress Test. "
            "The paradigm alternates arithmetic sub-blocks with cold pressor imagery instructions, "
            "producing a combined cognitive-somatic stressor. "
            "Three blocks, each internally alternating between arithmetic trials and imagery phases. "
            "No explicit rule changes; task difficulty adapts continuously. "
            "Strong acute cortisol and autonomic responder; suitable for salivary alpha-amylase or HRV studies."
        ),
        paradigm_ids=["mast"],
        duration_min=15,
        intensity=Intensity.HIGH,
        blocks=3,
        rest_duration_sec=30,
    ),
]

PROTOCOL_REGISTRY = {p.id: p for p in PROTOCOL_PRESETS}
