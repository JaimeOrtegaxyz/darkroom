"""Built-in film stocks (spec 4.4).

A "filter" is just a named prompt — the transform seam (transform.py)
executes it without knowing anything about this list. The four defaults are
the ImageGenCam starters. Edit freely; ids must stay unique and stable
(they key the dedupe index in store.py).
"""

from __future__ import annotations

PROMPTS: list[dict] = [
    {
        "id": "pathetic-scribble",
        "name": "Pathetic Scribble",
        "prompt": (
            "Redraw this exact photo as a hasty, pathetic ballpoint-pen scribble "
            "on cheap notebook paper. Keep the original composition, subjects and "
            "poses recognizable, but render everything with wobbly lazy pen strokes, "
            "bad proportions and minimal effort, like a bored doodle in the margin "
            "of a school notebook."
        ),
    },
    {
        "id": "turn-to-cheese",
        "name": "Turn to Cheese",
        "prompt": (
            "Recreate this exact photo, same composition and lighting, but every "
            "person, animal and object is sculpted entirely out of cheese. Mix "
            "cheeses — swiss with holes, melted cheddar, crumbly parmesan, stringy "
            "mozzarella — while keeping each subject clearly recognizable. Glossy, "
            "slightly melty, shot like an editorial food photograph."
        ),
    },
    {
        "id": "goblin-mode",
        "name": "Goblin Mode",
        "prompt": (
            "Recreate this exact photo but every person is a mischievous green "
            "goblin — pointed ears, crooked noses, sharp little teeth, gleeful "
            "expressions — wearing tattered medieval rags. Keep the original "
            "composition, poses and setting; gritty fantasy-illustration lighting."
        ),
    },
    {
        "id": "anime-portrait",
        "name": "Anime Portrait",
        "prompt": (
            "Redraw this exact photo as a high-quality anime illustration — clean "
            "line art, cel shading, expressive eyes, soft painted background. Keep "
            "the composition, poses, outfits and setting faithful to the original; "
            "1990s theatrical anime film style."
        ),
    },
]


def get(filter_id: str) -> dict | None:
    return next((p for p in PROMPTS if p["id"] == filter_id), None)


def index_of(filter_id: str) -> int:
    return next((i for i, p in enumerate(PROMPTS) if p["id"] == filter_id), -1)


def names() -> list[str]:
    return [p["name"] for p in PROMPTS]
