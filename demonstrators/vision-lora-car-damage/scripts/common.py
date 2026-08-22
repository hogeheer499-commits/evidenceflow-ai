"""Shared label schema and prompt for the car-damage classification demonstrator."""
LABELS = ["F_Normal", "F_Crushed", "F_Breakage", "R_Normal", "R_Crushed", "R_Breakage"]
LETTERS = ["A", "B", "C", "D", "E", "F"]
DESCRIPTIONS = {
    "F_Normal": "front view, undamaged",
    "F_Crushed": "front view, crushed damage",
    "F_Breakage": "front view, visible breakage",
    "R_Normal": "rear view, undamaged",
    "R_Crushed": "rear view, crushed damage",
    "R_Breakage": "rear view, visible breakage",
}
LABEL_TO_LETTER = dict(zip(LABELS, LETTERS))
LETTER_TO_LABEL = dict(zip(LETTERS, LABELS))

PROMPT = (
    "This photo shows the front or the rear of a car. Classify the image into "
    "exactly one category:\n"
    + "\n".join(f"{LABEL_TO_LETTER[l]}) {DESCRIPTIONS[l]}" for l in LABELS)
    + "\nAnswer with the single letter of the correct category."
)

def target_text(label: str) -> str:
    return f"{LABEL_TO_LETTER[label]}) {DESCRIPTIONS[label]}"
