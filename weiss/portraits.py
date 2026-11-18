"""Portraits: the player's anime paper doll, built from layered parts (see docs/world-mode.md).

The art is two artists' kits, cut into parts by scripts/import_portraits.py: static/weiss/portraits/ holds the images
and parts.json says, for each base (an art style's feminine or masculine body), what can be chosen and what each part
draws. A portrait is a recipe, never an image; the browser stacks it (static/weiss/portrait.js):

    {"base": "tainara_female",
     "choices": {"skin": "3", "hair": "5", "eyes": "2", "eye_state": "Normal", "mouth_state": "Smile", "brow_state": "Neutro"},
     "parts": {"hair_front": {"id": "tainara_female_hair_front_fringe_11", "color": ""},
               "outfit": {"id": "tainara_female_outfit_outfit_3", "color": "2"}, ...}}

`choices` are the base's own (skin tone, hair and eye colour, and for some styles the expression); each part may also
come in colours of its own. `clean` checks a recipe against the manifest before it's saved.
"""
import json
from functools import lru_cache
from pathlib import Path

PORTRAITS_DIR = Path(__file__).resolve().parent / "static" / "weiss" / "portraits"
MANIFEST = PORTRAITS_DIR / "parts.json"
DEFAULT_BASE = "sutemo_female"


class ManifestMissing(Exception):
    """The parts haven't been imported: see scripts/import_portraits.py."""


@lru_cache(maxsize=1)
def manifest():
    if not MANIFEST.exists():
        raise ManifestMissing("No portrait parts yet: run scripts/import_portraits.py.")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def is_ready():
    try:
        manifest()
    except ManifestMissing:
        return False
    return True


def parts():
    return {part["id"]: part for part in manifest()["parts"]}


def bases():
    return manifest()["bases"]


def default_recipe(base=None):
    known = bases()
    base = base if base in known else DEFAULT_BASE if DEFAULT_BASE in known else next(iter(known))
    defaults = known[base]["defaults"]
    return {"base": base, "choices": dict(defaults["choices"]), "parts": {k: dict(v) for k, v in defaults["parts"].items()}}


def clean(recipe):
    """(recipe, problem): the recipe as it should be saved, or why it can't be."""
    if not isinstance(recipe, dict) or not isinstance(recipe.get("parts"), dict) or not isinstance(recipe.get("choices"), dict):
        return None, "That isn't a portrait."
    base_key = recipe.get("base")
    base = bases().get(base_key)
    if base is None:
        return None, "Choose a body."
    choices = {}
    for choice in base["choices"]:
        value = recipe["choices"].get(choice["key"])
        if value not in {o["key"] for o in choice["options"]}:
            return None, f"Choose {choice['label'].lower()}."
        choices[choice["key"]] = value
    slots = {s["key"]: s for s in base["slots"]}
    known = parts()
    out = {}
    for key, pick in recipe["parts"].items():
        slot = slots.get(key)
        if slot is None or not isinstance(pick, dict):
            return None, "That isn't a portrait."
        if not pick.get("id"):
            continue  # the slot left empty
        part = known.get(pick["id"])
        if part is None or part["slot"] != key or part["base"] != base_key:
            return None, f"There's no such {slot['label'].lower()} for this body."
        colours = {c["key"] for c in part.get("colors") or []}
        colour = pick.get("color") or ""
        if colours and colour not in colours:
            return None, f"Choose a colour for {part['name']}."
        out[key] = {"id": part["id"], "color": colour if colours else ""}
    for slot in base["slots"]:
        if slot["required"] and slot["key"] not in out:
            return None, f"Choose {'an' if slot['label'][0] in 'AEIOU' else 'a'} {slot['label'].lower()}."
    return {"base": base_key, "choices": choices, "parts": out}, None


def editor_data():
    """What the editor needs besides the manifest the browser loads itself."""
    return {"default_base": default_recipe()["base"]}


def credits():
    """Each artist once: [{author, url}]."""
    seen = {}
    for base in bases().values():
        seen.setdefault(base["credit"]["author"], base["credit"])
    return list(seen.values())
