"""Turn paper-doll portrait art into the parts the portrait editor stacks: cropped WebPs, and a manifest
(weiss/static/weiss/portraits/parts.json) saying what each part is, which of the player's choices pick its images,
where each sits and what's drawn over what.

Two artists' kits, each its own art style with a feminine and a masculine body (parts can't cross styles: they're drawn
to their own proportions):

- Sutemo's visual novel sprites, one PSD each (https://sutemo.itch.io/female-character,
  https://sutemo.itch.io/male-character-sprite-for-visual-novel): personal or commercial use, not to be resold alone.
- Tainara-P's character sprite creators, folders of PNGs (https://tainara-p.itch.io/female-character-sprite-creator,
  https://tainara-p.itch.io/male-character-sprite-creator): created characters for commercial or personal use; CC0.
  Each comes as the main download and an "Update 2.0" whose files add to and replace it.

Needs psd-tools and numpy (not the site's own requirements: only this script uses them):

    pip install psd-tools
    python scripts/import_portraits.py \\
        --sutemo-female "Female Sprite by Sutemo.psd" --sutemo-male "Male Sprite by Sutemo.psd" \\
        --tainara-female "Female Character Sprite Creator" "Update 2.0 (female)" \\
        --tainara-male "Male Character Sprite Creator" "Update 2.0 (male)"

Each base is imported on its own (into portraits/<base>/, with its part of the manifest in base.json); a run
replaces the bases it's given and keeps the others, then writes parts.json from them all.

Skin: Tainara-P draws every skin part in nine tones (five human, four fantasy); SKIN_TONES adds two deeper ones, made by
recolouring the darkest. Sutemo draws one, so its skin is recoloured to all of them (recolour_skin). Re-running replaces
everything in the portraits folder.
"""
import argparse
import colorsys
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "weiss" / "static" / "weiss" / "portraits"
QUALITY = 88  # WebP with alpha: a tenth of the PNG's size, no visible loss at this scale

# The skin tones, lightest first: (key, name, base colour, shadow colour). 1-9 are Tainara-P's own; "deep" and "dark"
# are made from tone 5. Sutemo's skin is recoloured to each.
SKIN_TONES = [
    ("1", "Porcelain", "#fce4dc", "#e4a094"), ("2", "Fair", "#fcd0b8", "#ec947c"), ("3", "Warm", "#fcbc94", "#c87c60"),
    ("4", "Tan", "#f09c78", "#b86050"), ("5", "Brown", "#d48068", "#ac4c48"), ("deep", "Deep", "#a65c45", "#743430"),
    ("dark", "Dark", "#73402f", "#47221c"),
    ("6", "Jade", "#9cd0a4", "#288c68"), ("7", "Frost", "#9cbcd0", "#2c4098"), ("8", "Rose", "#f48ce4", "#b42868"),
    ("9", "Crimson", "#d05c5c", "#8c2040"),
]
MADE_TONES = {"deep": "5", "dark": "5"}  # made by recolouring this tone's art
SUTEMO_SKIN = ("#fcf8e0", "#fcc0a0")  # Sutemo's skin, light and shadow

def hex_rgb(value):
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def name_of(rgb):
    """A plain name for a colour from the art: by its hue, lighter or darker."""
    h, light, sat = colorsys.rgb_to_hls(*(rgb / 255))
    h *= 360
    if light < 0.14:
        return "Black"
    if sat < 0.18 or (light > 0.9 and sat < 0.5):
        return "Black" if light < 0.18 else "Charcoal" if light < 0.35 else "Grey" if light < 0.65 else "Silver" if light < 0.85 else "White"
    if (h < 45 or h >= 340) and light < 0.42 and (sat < 0.45 or h >= 15):
        hue = "Brown"
    elif 40 <= h < 65 and light > 0.55:
        hue = "Blonde"
    else:
        hue = next(name for limit, name in ((15, "Red"), (40, "Orange"), (65, "Yellow"), (165, "Green"), (195, "Teal"), (250, "Blue"),
                                            (285, "Purple"), (350, "Pink"), (361, "Red")) if h < limit)
    shade = "Dark " if light < 0.3 else "Light " if light > 0.72 else ""
    return shade + (hue.lower() if shade else hue)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")


def num(name):
    found = re.search(r"(\d+)", name)
    return int(found.group(1)) if found else 0


def swatch(image):
    """The colour a part looks, as hex: the average of its lighter mid-tones (lines, shadows and highlights left out)."""
    a = np.asarray(image.convert("RGBA")).reshape(-1, 4)
    a = a[a[:, 3] > 250][:, :3].astype(float)
    if not len(a):
        return "#888888"
    luma = a @ np.array([0.299, 0.587, 0.114])
    low, high = np.percentile(luma, [50, 92])  # the flat base colour: anime shading is mostly darker, in smaller areas
    mid = a[(luma >= low) & (luma <= high)]
    return "#%02x%02x%02x" % tuple(int(v) for v in (mid if len(mid) else a).mean(axis=0))


def recolour_skin(image, source, target):
    """Skin from one tone to another. Each skin pixel's place between the source's light and shadow colours (and a
    little past either) is kept, on the target's; pixels well off that line (lines, eye whites, blush) are left."""
    a = np.asarray(image.convert("RGBA")).astype(float)
    rgb = a[..., :3]
    light, shadow = hex_rgb(source[0]), hex_rgb(source[1])
    to_light, to_shadow = hex_rgb(target[0]), hex_rgb(target[1])
    d = shadow - light
    t = ((rgb - light) @ d) / float(d @ d)
    off = rgb - (light + t[..., None] * d)
    skin = ((a[..., 3] > 0) & (np.linalg.norm(off, axis=-1) < 30) & (t > -0.4) & (t < 2.2)
            & (rgb[..., 0] - rgb[..., 2] > 12))  # warm: the eyes' whites aren't skin
    new = to_light + t[..., None] * (to_shadow - to_light) + off * 0.6
    a[..., :3] = np.where(skin[..., None], np.clip(new, 0, 255), rgb)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


class Writer:
    """Saves images for one base, scaled and cropped, and remembers where each went."""

    def __init__(self, base, size, scale=1.0, frame=None):
        self.base, self.scale = base, scale
        self.frame = frame or (0, 0, size[0], size[1])  # the part of the canvas kept
        self.size = [round((self.frame[2] - self.frame[0]) * scale), round((self.frame[3] - self.frame[1]) * scale)]
        self.count = 0

    def save(self, image, name):
        """Art for a full-canvas image: {src, x, y, w, h}, or None if nothing's drawn. Only what's drawn is scaled,
        mapped exactly as scaling the whole frame would, so parts still line up (and it's far quicker)."""
        image = image.convert("RGBA")
        drawn = image.getbbox()
        if not drawn:
            return None
        fx, fy, fx1, fy1 = self.frame
        left, top = max(drawn[0], fx) - fx, max(drawn[1], fy) - fy
        right, bottom = min(drawn[2], fx1) - fx, min(drawn[3], fy1) - fy
        if right <= left or bottom <= top:
            return None
        s = self.scale
        x0, y0, x1, y1 = math.floor(left * s), math.floor(top * s), math.ceil(right * s), math.ceil(bottom * s)
        if s == 1:
            image = image.crop((fx + x0, fy + y0, fx + x1, fy + y1))
        else:
            region = (fx + x0 / s, fy + y0 / s, min(fx + x1 / s, image.width), min(fy + y1 / s, image.height))  # rounding up can pass the edge
            image = image.resize((x1 - x0, y1 - y0), Image.LANCZOS, box=region)
        box = image.getbbox()
        if not box:
            return None
        image = image.crop(box)
        box = (x0 + box[0], y0 + box[1])
        src = f"{self.base}/{name}.webp"
        (OUT / src).parent.mkdir(parents=True, exist_ok=True)
        image.save(OUT / src, "WEBP", quality=QUALITY, method=4)
        self.count += 1
        return {"src": src, "x": box[0], "y": box[1], "w": image.width, "h": image.height}


def tone_choice():
    return {"key": "skin", "label": "Skin", "kind": "swatch",
            "options": [{"key": k, "label": n, "swatch": b} for k, n, b, _ in SKIN_TONES]}


# ---------------------------------------------------------------- Sutemo (PSDs)

SUTEMO_RULES = {  # (layer path pattern, slot, name); "{style}" "{colour}" "{name}" capture; first match wins
    "female": [
        ("Hair behind/{style}/{colour}", "hair_back", None), ("Base Body", "body", "Body"), ("Blush/1", "face", "Blush"),
        ("Blush/2", "face", "Deep blush"), ("Costume/{name}", "outfit", None), ("Hair front/{style}/{colour}", "hair_front", None),
        ("Expression/{name}", "expression", None), ("Accessories/Red Glasses", "glasses", "Red glasses"),
        ("Accessories/Black Glasses", "glasses", "Black glasses"), ("Accessories/Circle Glasses", "glasses", "Round glasses"),
        ("Accessories/Flower", "head", "Flower"), ("Accessories/Choker", "neck", "Choker"),
    ],
    "male": [
        ("Hair behind/{style}/{colour}", "hair_back", None), ("Base Male Body", "body", "Body"), ("Headphones", "neck", "Headphones"),
        ("Outfit/{name}", "outfit", None), ("HairFront/{style}/{colour}", "hair_front", None), ("Expression/sweat", "face", "Sweat drop"),
        ("Expression/{name}", "expression", None), ("Glasses/Black Glasses Copy", "glasses", "Black glasses"),
        ("Glasses/Circle Glasses Copy", "glasses", "Round glasses"),
        ("Hair Front 2 (blocking eyes)/Side/{colour}", "hair_side", "Side bangs"), ("Headphones Up", "head", "Headphones (on)"),
    ],
}
SUTEMO_COLOURS = {"blondie": "blonde", "blond": "blonde", "black": "dark"}
SUTEMO_HAIR = {"blonde": "#e8c46a", "silver": "#c9cdd8", "pink": "#f2a3c2", "brown": "#8b5a3c", "dark": "#2f2a35", "red": "#c2453a"}
SUTEMO_NAMES = {
    "Long Hair / Hime Cut": "Long (hime cut)", "Twin tail / Short Hair": "Twin tail / short", "Sswimsuit": "Swimsuit",
    "seifuku 1": "School uniform 1", "seifuku 2": "School uniform 2", "Hoodie 1": "Hoodie", "PE uniform": "P.E. uniform",
    "P.E Uniform": "P.E. uniform", "normal": "Normal", "winter": "Winter outfit", "Casual 1-1": "Casual 1", "Casual 1-2": "Casual 1 (alt)",
    "Casual 2-1": "Casual 2", "Casual 2-2": "Casual 2 (alt)", "Casual 3-1": "Casual 3", "Casual 3-3": "Casual 3 (alt)",
}
SUTEMO_SLOTS = [("hair_front", "Fringe", True), ("hair_back", "Back hair", False), ("hair_side", "Side bangs", False),
                ("expression", "Expression", True), ("outfit", "Outfit", True), ("glasses", "Glasses", False),
                ("head", "On the head", False), ("neck", "Around the neck", False), ("face", "Face extras", False)]
SKIN_SLOTS = ("body", "expression")  # Sutemo layers with skin in them, recoloured to each tone
SUTEMO_MOODS = {"happy": r"delighted|laugh|smile 2|smile 3", "smile": r"^smile", "sad": r"sad", "surprised": r"shock|surpris",
                "angry": r"angry|annoyed", "smug": r"smug|smirk", "neutral": r"normal"}
SUTEMO_DEFAULTS = {
    "female": {"hair_front": "hime_cut", "hair_back": "long_hime_cut", "expression": "smile", "outfit": "school_uniform_2"},
    "male": {"hair_front": "short_1", "hair_back": "short_1", "expression": "smile_1", "outfit": "school_uniform_1"},
}


def psd_match(pattern, path):
    steps = pattern.split("/")
    if len(steps) != len(path):
        return None
    found = {}
    for step, name in zip(steps, path):
        if step.startswith("{") and step.endswith("}"):
            found[step[1:-1]] = name
        elif step != name:
            return None
    return found


def psd_leaves(group, path=()):
    for layer in group:
        here = path + (layer.name.strip(),)
        if layer.is_group() and not (len(here) == 3 and here[0].lower().startswith("hair")):
            yield from psd_leaves(layer, here)
        else:
            yield here, layer


def import_sutemo(psd_path, sex):
    from psd_tools import PSDImage

    base = f"sutemo_{sex}"
    psd = PSDImage.open(psd_path)
    width, height = psd.size
    out = Writer(base, (width, height))
    parts = {}
    for z, (path, layer) in enumerate(psd_leaves(psd)):
        for pattern, slot, fixed in SUTEMO_RULES[sex]:
            groups = psd_match(pattern, path)
            if groups is not None:
                break
        else:
            continue
        style = groups.get("style")
        name = fixed or SUTEMO_NAMES.get(style or groups.get("name"), style or groups.get("name"))
        colour = SUTEMO_COLOURS.get(groups["colour"].lower(), groups["colour"].lower()) if groups.get("colour") else ""
        shown = layer
        while shown is not None and shown is not psd:  # the groups it's in are often hidden
            shown.visible = True
            shown = shown.parent
        image = layer.composite(viewport=(0, 0, width, height), force=True)
        if image is None or not image.getbbox():
            print(f"  skipped {'/'.join(path)}: nothing drawn")
            continue
        pid = f"{base}_{slot}_{slug(name)}"
        part = parts.setdefault(pid, {"id": pid, "base": base, "slot": slot, "name": name, "layers": []})
        if slot in SKIN_SLOTS:
            art = {}
            for key, _, light, shade in SKIN_TONES:
                saved = out.save(recolour_skin(image, SUTEMO_SKIN, (light, shade)), f"{slot}/{slug(name)}_{key}")
                if saved:
                    art[key] = saved
            part["layers"].append({"z": z, "key": ["skin"], "art": art})
        elif colour:
            if not part["layers"]:
                part["layers"].append({"z": z, "key": ["hair"], "art": {}})
            saved = out.save(image, f"{slot}/{slug(name)}_{colour}")
            if saved:
                part["layers"][0]["art"][colour] = saved
        else:
            saved = out.save(image, f"{slot}/{slug(name)}")
            if saved:
                part["layers"].append({"z": z, "key": [], "art": {"": saved}})
    parts = list(parts.values())
    hair = sorted({c for p in parts for layer in p["layers"] if layer["key"] == ["hair"] for c in layer["art"]},
                  key=lambda c: list(SUTEMO_HAIR).index(c) if c in SUTEMO_HAIR else 99)
    by_name = lambda slot, key: f"{base}_{slot}_{key}"
    expressions = [p for p in parts if p["slot"] == "expression"]
    moods = {}
    for mood, pattern in SUTEMO_MOODS.items():
        found = next((p for p in expressions if re.search(pattern, p["name"], re.I)), None)
        if found:
            moods[mood] = {"parts": {"expression": {"id": found["id"], "color": ""}}}
    defaults = {"choices": {"skin": "1", "hair": "brown" if "brown" in hair else hair[0]},
                "parts": {slot: {"id": by_name(slot, key), "color": ""} for slot, key in SUTEMO_DEFAULTS[sex].items()}}
    info = {
        "label": "Feminine" if sex == "female" else "Masculine", "style": "Sutemo", "size": out.size,
        "credit": {"author": "Sutemo", "url": "https://sutemo.itch.io/female-character" if sex == "female"
                   else "https://sutemo.itch.io/male-character-sprite-for-visual-novel"},
        "choices": [tone_choice(), {"key": "hair", "label": "Hair colour", "kind": "swatch",
                                    "options": [{"key": c, "label": c.title(), "swatch": SUTEMO_HAIR.get(c, "#888")} for c in hair]}],
        "slots": [{"key": k, "label": l, "required": r} for k, l, r in SUTEMO_SLOTS if any(p["slot"] == k for p in parts)],
        "always": [p["id"] for p in parts if p["slot"] == "body"],
        "moods": moods, "defaults": defaults,
    }
    print(f"  {base}: {len(parts)} parts, {out.count} images")
    return info, parts


# ---------------------------------------------------------------- Tainara-P (folders of PNGs)

EYE_STATES = ("Normal", "Sorrow", "Spread", "Surprised")  # drawn per eye type; the rest are whole "extra" eyes
Z = {  # what's drawn over what, bottom first
    "hat_back": 5, "hair_back": 10, "body": 20, "outfit_shadow": 24, "outfit": 30, "neck": 34, "ears": 38, "face": 40,
    "marks": 44, "sclera": 50, "iris": 52, "iris_light": 53, "eye_shadow": 54, "eye_lines": 55, "eye_extra": 56,
    "eyelid": 57, "mouth": 58, "lipstick": 59, "brows": 60, "fringe_shadow": 62, "earrings": 64, "hair_extension": 66,
    "hair_front": 70, "ahoge": 72, "glasses": 75, "mask_shadow": 76, "mask": 77, "hat": 80,
}
TAINARA_SLOTS = [
    ("hair_front", "Fringe", True), ("hair_back", "Back hair", False), ("hair_extension", "Hair extensions", False),
    ("ahoge", "Ahoge", False), ("eyes", "Eye shape", True), ("iris", "Iris style", True), ("brows", "Brow shape", True),
    ("mouth", "Mouth shape", True), ("ears", "Ears", True), ("outfit", "Outfit", True), ("lipstick", "Lipstick", False),
    ("marks", "Face marks", False), ("glasses", "Glasses", False), ("earrings", "Earrings", False), ("neck", "Necklace", False),
    ("mask", "Mask", False), ("hat", "Hat", False),
]
TAINARA_MOODS = {  # moods as expression choices: (eyes, mouth, brows)
    "smile": ("Normal", "Smile", "Neutro"), "happy": ("Smile", "Big Smile", "Curved"), "sad": ("Sorrow", "Sad", "Sad"),
    "surprised": ("Surprised", "Surprised", "Up"), "angry": ("Angry", "Angry", "Angry"), "smug": ("Smug", "Smirk", "Serious"),
    "neutral": ("Normal", "Neutro", "Neutro"),
}
EAR_NAMES = {1: "Round", 2: "Elf", 3: "Pointed"}
TAINARA_ZOOM = 1.2  # drawn this much bigger than its box (from the bottom), so its heads match Sutemo's: its canvas
                    # leaves room above for hats
TAINARA_DEFAULTS = {  # a new portrait's parts, by name (a name that's gone falls back to the first of its slot)
    "female": {"hair_front": "Fringe 22", "hair_back": "Back 12", "outfit": "Outfit 1"},
    "male": {"hair_front": "Fringe 5", "hair_back": "Back 5", "outfit": "Outfit 1"},
}
DEFAULT_HAIR_NAMES = ("Brown", "Dark brown", "Dark orange", "Black")  # the first of these the kit has


class Kit:
    """A Tainara-P kit's files, the update's laid over the main download's: {relative path: file}."""

    def __init__(self, folders):
        self.files = {}
        for folder in folders:
            folder = Path(folder)
            for f in folder.rglob("*.png"):
                rel = f.relative_to(folder).as_posix()
                if rel.count("/") >= 1 and not rel.startswith(("Preview", "1-tile")):
                    self.files[rel] = f

    def under(self, prefix):
        return {rel[len(prefix) + 1:]: f for rel, f in self.files.items() if rel.startswith(prefix + "/")}

    def items(self, category):
        """Each item folder (or loose file) under a category, by number: [(name, {rest of path: file})]."""
        found = {}
        for rel, f in self.under(category).items():
            head, _, rest = rel.partition("/")
            found.setdefault(head, {})[rest or head] = f
        return sorted(found.items(), key=lambda item: (num(item[0]), item[0]))


def import_tainara(folders, sex, scale):
    base = f"tainara_{sex}"
    kit = Kit(folders)
    if not kit.files:
        raise SystemExit(f"No PNGs in {folders}")
    canvas = Image.open(next(iter(kit.files.values()))).size
    # Keep only the part of the canvas anything's drawn in (it has a lot of empty sky).
    probe = [f for rel, f in kit.files.items() if rel.startswith(("Hair/Back", "Hair/Bangs", "Accessory/Hats", "Body/Body"))]
    boxes = [Image.open(f).getbbox() for f in probe[::3]]
    boxes = [b for b in boxes if b]
    frame = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), canvas[1])
    out = Writer(base, canvas, scale, frame)
    parts = []
    swatches = {"hair": {}, "eyes": {}}
    tones = {k: (light, shade) for k, _, light, shade in SKIN_TONES}

    def load(f):
        return Image.open(f)

    def skin_art(files, name):
        """{tone: art} for files keyed "N" by tone, the made tones recoloured from theirs."""
        art = {}
        for key, f in files.items():
            if (saved := out.save(load(f), f"{name}_{key}")):
                art[key] = saved
        for key, source in MADE_TONES.items():
            if source in files and (saved := out.save(recolour_skin(load(files[source]), tones[source], tones[key]), f"{name}_{key}")):
                art[key] = saved
        return art

    def by_number(files, prefix):
        """{"N": file} for files named "<prefix> N.png"."""
        return {str(num(name)): f for name, f in files.items() if re.fullmatch(rf"{prefix} \d+\.png", name)}

    def own_colours(files, prefix="Color"):
        return {str(num(n)): f for n, f in files.items() if re.fullmatch(rf"{prefix} \d+\.png", n)}

    def add(slot, name, layers, colours=None):
        pid = f"{base}_{slot}_{slug(name)}"
        part = {"id": pid, "base": base, "slot": slot, "name": name, "layers": [l for l in layers if l["art"]]}
        if colours:
            part["colors"] = colours
        if part["layers"]:
            parts.append(part)
        return part

    def coloured_layer(files, z, folder, key=("own",)):
        art, colours = {}, []
        for c, f in sorted(own_colours(files).items(), key=lambda kv: int(kv[0])):
            image = load(f)
            if (saved := out.save(image, f"{folder}_{c}")):
                art[c] = saved
                colours.append({"key": c, "swatch": swatch(image)})
        return {"z": z, "key": list(key), "art": art}, colours

    def label(colours):
        """Each colour named, numbered where names would repeat ("Blue", "Blue 2")."""
        seen, out = {}, []
        for c in colours:
            name = name_of(hex_rgb(c["swatch"]))
            seen[name] = seen.get(name, 0) + 1
            out.append({**c, "label": name if seen[name] == 1 else f"{name} {seen[name]}"})
        return out

    # The body and face: always drawn, in the skin tone.
    parts.append({"id": f"{base}_body", "base": base, "slot": "body", "name": "Body",
                  "layers": [{"z": Z["body"], "key": ["skin"], "art": skin_art(by_number(kit.under("Body/Body"), "Body"), "body/body")},
                             {"z": Z["face"], "key": ["skin"], "art": skin_art(by_number(kit.under("Head/Face"), "Face"), "body/face")}]})

    # Hair: each style in the hair colour; a fringe's shadow on the forehead in the skin tone.
    for slot, category, z in (("hair_back", "Hair/Back", Z["hair_back"]), ("hair_front", "Hair/Bangs", Z["hair_front"]),
                              ("hair_extension", "Hair/Extension", Z["hair_extension"]), ("ahoge", "Hair/Ahoge", Z["ahoge"])):
        for item, files in kit.items(category):
            layer, colours = coloured_layer(files, z, f"{slot}/{slug(item)}", key=("hair",))
            for c in colours:  # a fringe shows a hair colour best (the back's mostly in shadow)
                if slot == "hair_front":
                    swatches["hair"][c["key"]] = c["swatch"]
                else:
                    swatches["hair"].setdefault(c["key"], c["swatch"])
            shadow = {"z": Z["fringe_shadow"], "key": ["skin"], "art": skin_art(by_number(files, "Shadow/Shadow"), f"{slot}/{slug(item)}_shadow")}
            add(slot, f"{'Fringe' if slot == 'hair_front' else category.split('/')[1]} {num(item)}", [layer, shadow])

    # Ears, in the skin tone.
    for item, files in kit.items("Head/Ears"):
        add("ears", EAR_NAMES.get(num(item), item), [{"z": Z["ears"], "key": ["skin"], "art": skin_art(by_number(files, "Ear"), f"ears/{slug(item)}")}])

    # Eyes: each shape drawn per state: lines, whites (in a colour of their own: white, or a fantasy one) and shading
    # (in the skin tone). "Extra" eyes are whole eyes of their own, drawn instead, with an eyelid shadow.
    extras, sclera_colours = {}, {}
    for item, files in kit.items("Head/Eyes"):
        if item == "Iris":
            continue
        if item == "Eye Extra":
            for name, f in files.items():
                if "/" not in name:
                    extras[name[:-4]] = f
            eyelid = skin_art(by_number(files, "Eyelid/Shadow"), "eyes/eyelid")
            continue
        lines = {"z": Z["eye_lines"], "key": ["eye_state"], "art": {}}
        whites = {"z": Z["sclera"], "key": ["eye_state", "sclera"], "art": {}}
        shade = {"z": Z["eye_shadow"], "key": ["eye_state", "skin"], "art": {}}
        for state in EYE_STATES:
            if f"{state}.png" in files and (saved := out.save(load(files[f"{state}.png"]), f"eyes/{slug(item)}_{slug(state)}")):
                lines["art"][state] = saved
            for colour, f in by_number(files, f"Sclera/{state}/Sclera").items():
                image = load(f)
                if (saved := out.save(image, f"eyes/{slug(item)}_{slug(state)}_sclera_{colour}")):
                    whites["art"][f"{state}|{colour}"] = saved
                    sclera_colours.setdefault(colour, swatch(image))
            for tone, art in skin_art(by_number(files, f"Shadow/{state}/Shadow"), f"eyes/{slug(item)}_{slug(state)}_shadow").items():
                shade["art"][f"{state}|{tone}"] = art
        add("eyes", f"Eyes {num(item)}", [whites, shade, lines])
    for name, f in kit.under("Head/Eye Extra").items():  # more extras, loose in their own folder
        extras.setdefault(name[:-4], f)
    extra_art = {state: saved for state, f in sorted(extras.items()) if (saved := out.save(load(f), f"eyes/extra_{slug(state)}"))}
    parts.append({"id": f"{base}_eye_extra", "base": base, "slot": "eye_extra", "name": "Eyes",
                  "layers": [{"z": Z["eye_extra"], "key": ["eye_state"], "art": extra_art},
                             {"z": Z["eyelid"], "key": ["skin"], "when": {"eye_state": sorted(extra_art)}, "art": eyelid}]})
    eye_colours = []
    for item, files in kit.items("Head/Eyes/Iris"):
        layer, colours = coloured_layer({n.replace("Iris", "Color"): f for n, f in files.items()}, Z["iris"], f"iris/{slug(item)}", key=("eyes",))
        if not eye_colours:
            eye_colours = colours
        light = {"z": Z["iris_light"], "key": [], "art": {}}
        if "Light.png" in files and (saved := out.save(load(files["Light.png"]), f"iris/{slug(item)}_light")):
            light["art"][""] = saved
        for l in (layer, light):
            l["when"] = {"eye_state": list(EYE_STATES)}
        add("iris", f"Iris {num(item)}", [layer, light])

    # Brows and mouths: each type drawn per expression (some brows in the hair colour too).
    brow_states, mouth_states = set(), set()
    for item, files in kit.items("Head/Brows"):
        art, key = {}, ["brow_state"]
        for name, f in files.items():
            if "/" in name:
                colour, _, state = name.partition("/")
                key = ["hair", "brow_state"]
                k = f"{num(colour)}|{state[:-4]}"
            else:
                k, state = name[:-4], name
            brow_states.add(state[:-4] if state.endswith(".png") else state)
            if (saved := out.save(load(f), f"brows/{slug(item)}_{slug(k)}")):
                art[k] = saved
        add("brows", f"Brows {num(item)}", [{"z": Z["brows"], "key": key, "art": art}])
    for item, files in kit.items("Head/Mouth"):
        if item == "Lipstick":
            art, colours = {}, {}
            for name, f in files.items():
                state, _, colour = name.partition("/")
                image = load(f)
                if (saved := out.save(image, f"mouth/lipstick_{slug(state)}_{num(colour)}")):
                    art[f"{state}|{num(colour)}"] = saved
                    colours.setdefault(str(num(colour)), swatch(image))
            add("lipstick", "Lipstick", [{"z": Z["lipstick"], "key": ["mouth_state", "own"], "art": art}],
                label([{"key": k, "swatch": v} for k, v in sorted(colours.items(), key=lambda kv: int(kv[0]))]))
            continue
        art = {}
        for name, f in files.items():
            mouth_states.add(name[:-4])
            if (saved := out.save(load(f), f"mouth/{slug(item)}_{slug(name[:-4])}")):
                art[name[:-4]] = saved
        add("mouth", f"Mouth {num(item)}", [{"z": Z["mouth"], "key": ["mouth_state"], "art": art}])

    # Face marks: one look each.
    for item, files in kit.items("Head/Face Marks"):
        f = next(iter(files.values()))
        if (saved := out.save(load(f), f"marks/{slug(item)}")):
            add("marks", f"Mark {num(item)}", [{"z": Z["marks"], "key": [], "art": {"": saved}}])

    # Clothes and accessories: each in colours of its own; some cast a shadow on the skin, hats have a back.
    for slot, category, z, shadow_z in (("outfit", "Body/Clothes", Z["outfit"], Z["outfit_shadow"]), ("neck", "Accessory/Necklace", Z["neck"], None),
                                        ("earrings", "Accessory/Earring", Z["earrings"], None), ("glasses", "Accessory/Glasses", Z["glasses"], None),
                                        ("mask", "Accessory/Mask", Z["mask"], Z["mask_shadow"]), ("hat", "Accessory/Hats", Z["hat"], None)):
        for item, files in kit.items(category):
            prefix = "Front" if any(n.startswith("Front") for n in files) else "Color"
            layer, colours = coloured_layer({n.replace("Front", "Color"): f for n, f in files.items() if n.startswith(prefix)}, z, f"{slot}/{slug(item)}")
            layers = [layer]
            if shadow_z:
                layers.append({"z": shadow_z, "key": ["skin"], "art": skin_art(by_number(files, "Shadow/Shadow"), f"{slot}/{slug(item)}_shadow")})
            if "Back.png" in files and (saved := out.save(load(files["Back.png"]), f"{slot}/{slug(item)}_back")):
                layers.append({"z": Z["hat_back"], "key": [], "art": {"": saved}})
            backs = {str(num(n)): f for n, f in files.items() if re.fullmatch(r"Back \d+\.png", n)}
            if backs:
                art = {c: saved for c, f in backs.items() if (saved := out.save(load(f), f"{slot}/{slug(item)}_back_{c}"))}
                layers.append({"z": Z["hat_back"], "key": ["own"], "art": art})
            nice = {"outfit": "Outfit", "neck": "Necklace", "earrings": "Earrings", "glasses": "Glasses", "mask": "Mask", "hat": "Hat"}[slot]
            add(slot, f"{nice} {num(item)}", layers, label(colours) if len(colours) > 1 else None)

    hair = [{"key": k, "swatch": v} for k, v in sorted(swatches["hair"].items(), key=lambda kv: int(kv[0]))]
    states = lambda found, order=(): [s for s in order if s in found] + sorted(found - set(order))
    eye_states = list(EYE_STATES) + sorted(extra_art)
    parts_by_slot = lambda slot: [p for p in parts if p["slot"] == slot]
    def first(slot):
        wanted = TAINARA_DEFAULTS[sex].get(slot)
        part = next((p for p in parts_by_slot(slot) if p["name"] == wanted), parts_by_slot(slot)[0])
        return {"id": part["id"], "color": (part.get("colors") or [{"key": ""}])[0]["key"]}

    named_hair = {o["label"]: o["key"] for o in label(hair)}
    default_hair = next((named_hair[n] for n in DEFAULT_HAIR_NAMES if n in named_hair), hair[0]["key"])
    defaults = {"choices": {"skin": "2", "hair": default_hair, "eyes": eye_colours[0]["key"], "sclera": "1",
                            "eye_state": "Normal", "mouth_state": "Smile" if "Smile" in mouth_states else sorted(mouth_states)[0],
                            "brow_state": "Neutro" if "Neutro" in brow_states else sorted(brow_states)[0]},
                "parts": {slot: first(slot) for slot in ("hair_front", "hair_back", "eyes", "iris", "brows", "mouth", "ears", "outfit")
                          if parts_by_slot(slot)}}
    moods = {m: {"choices": {"eye_state": e, "mouth_state": mo, "brow_state": b}} for m, (e, mo, b) in TAINARA_MOODS.items()
             if e in eye_states and mo in mouth_states and b in brow_states}
    info = {
        "label": "Feminine" if sex == "female" else "Masculine", "style": "Tainara-P", "size": out.size,
        "zoom": TAINARA_ZOOM,
        "credit": {"author": "Tainara-P", "url": f"https://tainara-p.itch.io/{sex}-character-sprite-creator"},
        "choices": [tone_choice(),
                    {"key": "hair", "label": "Hair colour", "kind": "swatch", "options": label(hair)},
                    {"key": "eyes", "label": "Eye colour", "kind": "swatch", "options": label(eye_colours)},
                    {"key": "sclera", "label": "Eye whites", "kind": "swatch",
                     "options": label([{"key": k, "swatch": v} for k, v in sorted(sclera_colours.items(), key=lambda kv: int(kv[0]))])},
                    {"key": "eye_state", "label": "Eye expression", "kind": "list", "options": [{"key": s, "label": s} for s in eye_states]},
                    {"key": "brow_state", "label": "Brow expression", "kind": "list", "options": [{"key": s, "label": "Neutral" if s == "Neutro" else s}
                                                                                      for s in states(brow_states, ("Neutro",))]},
                    {"key": "mouth_state", "label": "Mouth expression", "kind": "list", "options": [{"key": s, "label": "Neutral" if s == "Neutro" else s}
                                                                                       for s in states(mouth_states, ("Smile", "Neutro"))]}],
        "slots": [{"key": k, "label": l, "required": r} for k, l, r in TAINARA_SLOTS if parts_by_slot(k)],
        "always": [p["id"] for p in parts if p["slot"] in ("body", "eye_extra")],
        "moods": moods, "defaults": defaults,
    }
    print(f"  {base}: {len(parts)} parts, {out.count} images")
    return info, parts


def face_of(info, parts, slots):
    """Where a base's face is, as fractions of its canvas: [centre x, centre y, width], from its eyes and mouth."""
    boxes = [art for p in parts if p["slot"] in slots for layer in p["layers"] for art in layer["art"].values()]
    left, top = min(a["x"] for a in boxes), min(a["y"] for a in boxes)
    right, bottom = max(a["x"] + a["w"] for a in boxes), max(a["y"] + a["h"] for a in boxes)
    width, height = info["size"]
    return [round((left + right) / 2 / width, 4), round((top + bottom) / 2 / height, 4), round((right - left) / width, 4)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sutemo-female", type=Path)
    parser.add_argument("--sutemo-male", type=Path)
    parser.add_argument("--tainara-female", type=Path, nargs="+")
    parser.add_argument("--tainara-male", type=Path, nargs="+")
    parser.add_argument("--tainara-scale", type=float, default=0.75, help="Tainara-P's canvas is large: scaled by this")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for key, path, run in (("sutemo_female", args.sutemo_female, lambda p: import_sutemo(p, "female")),
                           ("sutemo_male", args.sutemo_male, lambda p: import_sutemo(p, "male")),
                           ("tainara_female", args.tainara_female, lambda p: import_tainara(p, "female", args.tainara_scale)),
                           ("tainara_male", args.tainara_male, lambda p: import_tainara(p, "male", args.tainara_scale))):
        if path:
            print(key)
            if (OUT / key).exists():
                shutil.rmtree(OUT / key)
            info, found = run(path)
            info["face"] = face_of(info, found, ("expression",) if key.startswith("sutemo") else ("eyes", "mouth"))
            (OUT / key / "base.json").write_text(json.dumps({"info": info, "parts": found}), encoding="utf-8")
    bases, parts = {}, []
    for key in ("sutemo_female", "sutemo_male", "tainara_female", "tainara_male"):  # the editor's order
        saved = OUT / key / "base.json"
        if saved.exists():
            data = json.loads(saved.read_text(encoding="utf-8"))
            bases[key] = data["info"]
            parts += data["parts"]
    (OUT / "parts.json").write_text(json.dumps({"version": 2, "bases": bases, "parts": parts}, separators=(",", ":")), encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.rglob("*.webp"))
    print(f"{len(bases)} bases, {len(parts)} parts, {sum(1 for _ in OUT.rglob('*.webp'))} images ({size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
