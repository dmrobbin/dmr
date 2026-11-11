"""CPUs as files: the CPU profiles, their decks and their scenes written out as JSON, as examples to write new
ones from, and new ones read back in. Used by the export_cpu_corpus and import_cpu commands.

A CPU's file, as both commands use it:

    {"profile": {"name": "Rapi", "model": "standard", "aggression": 1, "boss": false,
                 "intro_text": "...", "player_win_text": "...", "player_lose_text": "...", "combo_text": "..."},
     "deck": {"name": "Rapi's deck", "series": "NIK", "anchors": ["NIK/S117-E001", "NIK/S117-E020"], "focus": false,
              "cards": [["NIK/S117-E001", 4], ...]},
     "scenes": [{"name": "Rapi: First meeting", "script": "cast rapi as Rapi\\n...", "infinite_event": false}]}

A deck is built by express building from its series and anchors, unless it lists its cards, which are then taken
as they are. An export also writes "context" (the deck's key cards, where its scenes play), which an import ignores.

Cards go by serial number, not by id, so a file from one database means the same in another.
"""
import json
import random
import re
from types import SimpleNamespace

from django.db import transaction

from . import abilities, buffs, cpu, scenes
from .cpu_views import MAX_TEXT, TEXT_FIELDS, deck_problem, scene_uses
from .express import ANCHORS, build_deck, cpu_anchor_choices, series_pool
from .models import Card, CardList, CardListEntry, CpuProfile, Scene
from .views import series_code

PROFILE_FIELDS = ("name", "model", "aggression", "boss", *TEXT_FIELDS)
CARD_FIELDS = ("serial_number", "name", "card_type", "level", "cost", "color", "power", "soul", "traits", "trigger", "description", "flavor_text")


class CorpusError(Exception):
    """Why a CPU's file can't be imported: every problem found, so they can all be fixed at once."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("\n".join(problems))


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unnamed"


# --- Export ---------------------------------------------------------------------------------------------

def card_record(card):
    return {field: getattr(card, field, None) for field in CARD_FIELDS}


def scene_casts():
    """{scene id: [CPU profile ids it casts]}, read from the scripts' cast lines."""
    casts = {}
    for scene in Scene.objects.all():
        compiled, _ = scenes.compile_scene(scene.script)
        casts[scene.pk] = sorted({profile.pk for profile in compiled["cast"].values()})
    return casts


def key_cards(deck, entries):
    """The cards a deck is built around: its anchors and what they name, or if express didn't build it, its cx combo cards."""
    required = set(deck.express.get("required", ()))
    anchors = set(deck.express.get("anchors", ()))
    cards = [e.card for e in entries if e.card.pk in anchors or e.card.name in required]
    return cards or [e.card for e in entries if abilities.has_combo(e.card.description)]


def deck_record(deck):
    entries = list(deck.entries.select_related("card").order_by("card__serial_number"))
    by_pk = {e.card.pk: e.card for e in entries}
    anchors = [by_pk[pk].serial_number for pk in deck.express.get("anchors", ()) if pk in by_pk]
    series = deck.express.get("series") or (series_code(entries[0].card.serial_number) if entries else "")
    return {"name": deck.name, "series": series, "anchors": anchors, "focus": bool(deck.express.get("focus")),
            "cards": [[e.card.serial_number, e.quantity] for e in entries]}, entries


def scene_record(scene):
    return {"name": scene.name, "script": scene.script, "infinite_event": scene.infinite_event}


def export_profile(profile, casts, uses):
    """A CPU's file, with the scenes that cast it."""
    record = {"profile": {field: getattr(profile, field) for field in PROFILE_FIELDS}, "deck": None, "scenes": [],
              "context": {"id": profile.pk, "finalized": profile.finalized, "key_cards": [], "scenes_play": {},
                          "images": {screen: getattr(profile, field).name for screen, field in CpuProfile.SCREENS.items()
                                     if getattr(profile, field) and getattr(profile, field).name}}}
    if profile.deck:
        record["deck"], entries = deck_record(profile.deck)
        record["context"]["key_cards"] = [card_record(card) for card in key_cards(profile.deck, entries)]
    for scene in Scene.objects.filter(pk__in=[pk for pk, cast in casts.items() if profile.pk in cast]).order_by("name"):
        record["scenes"].append(scene_record(scene))
        record["context"]["scenes_play"][scene.name] = uses.get(scene.pk, [])
    return record


def export_scenes(casts, uses):
    """Every scene, with who it casts and where it plays: those that cast no CPU (the infinite challenge's events) too."""
    names = dict(CpuProfile.objects.values_list("pk", "name"))
    return [{**scene_record(scene), "cast": [names[pk] for pk in casts.get(scene.pk, ())], "plays": uses.get(scene.pk, [])}
            for scene in Scene.objects.order_by("name")]


def reference():
    """What a CPU's file can hold, as Markdown, from the code itself so it's never out of date."""
    lines = ["# CPU file reference", "", "Written by export_cpu_corpus from the code: don't edit it by hand.", "",
             "## A CPU's file", "", "```", __doc__.split("A CPU's file, as both commands use it:")[1].split("A deck is built")[0].strip("\n"), "```", "",
             "A deck is built by express building from its series and anchors (2 cx combo cards a CPU can play), unless it "
             "lists its `cards`, which are then taken as they are. Leave `cards` out of a new CPU.", "",
             "## Profile", "",
             f"- `name`: at most 100 characters, and not already a CPU's: scenes cast CPUs by name.",
             f"- `model`: one of {', '.join(f'`{m}`' for m in cpu.MODELS)}.",
             f"- `aggression`: {cpu.MIN_AGGRESSION} to {cpu.MAX_AGGRESSION}; {cpu.MIN_AGGRESSION} is the standard behaviour.",
             "- `boss`: true for a CPU fought only on the infinite challenge's boss floors."]
    lines += [f"- `{field}`: at most {MAX_TEXT} characters. {CpuProfile._meta.get_field(field).help_text}." for field in TEXT_FIELDS]
    lines += ["", "### CPU models", "", "```", (cpu.__doc__ or "").strip(), "```", "",
              "## Scenes", "", "A scene's `name` must be one no other scene has. Its `script`, one thing per line:", ""]
    lines += [f"- `{example}`: {meaning}" for example, meaning, _ in scenes.REFERENCE]
    lines += ["", f"Backgrounds: {', '.join(scenes.BACKGROUNDS)}.", f"Pictures (expressions): {', '.join(scenes.EXPRESSIONS)}.",
              f"Places: {', '.join(scenes.POSITIONS)}. Ways in and out: {', '.join(scenes.ENTRANCES)}.",
              f"Animations: {', '.join(scenes.ACTIONS)}. Screen effects: {', '.join(scenes.SCREEN_EFFECTS)}.", "",
              "### Buffs", "", f"For `give`, `offer` and an option's `(give ...)`; also `{buffs.RANDOM}`, and `{buffs.PACT}` for a random pact.", ""]
    lines += [f"- `{buff.id}`{' (pact)' if buff.pact else ''}{' (special: only for something earned)' if buff.special else ''}: {buff.description}"
              for buff in buffs.BUFFS.values()]
    return "\n".join(lines) + "\n"


def cards_used():
    """{card name: [CPUs whose decks have it]}."""
    used = {}
    for profile in CpuProfile.objects.filter(deck__isnull=False).prefetch_related("deck__entries__card"):
        for entry in profile.deck.entries.all():
            used.setdefault(entry.card.name, []).append(profile.name)
    return used


def anchor_report(code, used=None):
    """The cx combo cards a CPU deck in a series can be built around, each with the CPUs whose decks already have it,
    and the climaxes it combos with: for choosing a new CPU's anchors."""
    choices = cpu_anchor_choices(code)
    if not choices:
        return []
    pool = series_pool(code)
    climaxes = {abilities.plain_name(c.name): c for c in pool if c.card_type.lower() == "climax"}
    used = cards_used() if used is None else used
    return [{**card_record(card), "used_by": sorted(set(used.get(card.name, []))),
             "combos_with": [card_record(climaxes[name]) for name in sorted(card.combos) if name in climaxes]}
            for card in choices]


def export_corpus():
    """{relative path: text}: a file per CPU, every scene, and the reference."""
    casts, uses = scene_casts(), scene_uses()
    files, taken = {}, set()
    for profile in CpuProfile.objects.select_related("deck", *CpuProfile.SCREENS.values()).order_by("name", "pk"):
        name = slug(profile.name)
        if name in taken:
            name = f"{name}-{profile.pk}"
        taken.add(name)
        files[f"cpus/{name}.json"] = json.dumps(export_profile(profile, casts, uses), indent=2, ensure_ascii=False)
    files["scenes.json"] = json.dumps(export_scenes(casts, uses), indent=2, ensure_ascii=False)
    files["reference.md"] = reference()
    used = cards_used()
    for code in sorted({series_code(s) for s in Card.objects.values_list("serial_number", flat=True)}):
        if anchors := anchor_report(code, used):
            files[f"anchors/{code}.json"] = json.dumps(anchors, indent=2, ensure_ascii=False)
    return files


# --- Import ---------------------------------------------------------------------------------------------

def not_anchors(serials):
    return "isn't a cx combo card" if len(serials) == 1 else "aren't cx combo cards"


def read_profile(data, problems, taken=None):
    """taken: the CPU names already used, lowercase; None to look in the database."""
    data = data or {}
    unknown = sorted(set(data) - set(PROFILE_FIELDS))
    if unknown:
        problems.append(f"profile: no such fields as {', '.join(unknown)}.")
    fields = {"name": str(data.get("name", "")).strip(), "model": data.get("model", "standard"),
              "aggression": data.get("aggression", cpu.MIN_AGGRESSION), "boss": bool(data.get("boss", False))}
    if not fields["name"] or len(fields["name"]) > 100:
        problems.append("profile: a name, at most 100 characters, is needed.")
    elif fields["name"].lower() in taken if taken is not None else CpuProfile.objects.filter(name__iexact=fields["name"]).exists():
        problems.append(f"profile: there's already a CPU called “{fields['name']}”.")
    if fields["model"] not in cpu.MODELS:
        problems.append(f"profile: the model must be one of {', '.join(cpu.MODELS)}.")
    if not isinstance(fields["aggression"], int) or not cpu.MIN_AGGRESSION <= fields["aggression"] <= cpu.MAX_AGGRESSION:
        problems.append(f"profile: aggression goes from {cpu.MIN_AGGRESSION} to {cpu.MAX_AGGRESSION}.")
    for field in TEXT_FIELDS:
        fields[field] = str(data.get(field, "")).strip()
        if len(fields[field]) > MAX_TEXT:
            problems.append(f"profile: {field} is {len(fields[field])} characters, more than {MAX_TEXT}.")
    return fields


def cards_by_serial(serials, problems, what):
    found = {c.serial_number: c for c in Card.objects.filter(serial_number__in=serials)}
    missing = [s for s in serials if s not in found]
    if missing:
        problems.append(f"deck: no cards {', '.join(missing)} {what}.")
    return found


def make_deck(data, user, rng, problems):
    """The deck, saved, or None if it couldn't be made. Returns (deck, notes from express building)."""
    data = data or {}
    deck = CardList(user=user, name=str(data.get("name", "")).strip()[:100] or "CPU deck", reserved_for_cpu=True)
    if data.get("cards"):
        try:
            copies = {str(serial): int(n) for serial, n in data["cards"]}
        except (TypeError, ValueError):
            problems.append("deck: write cards as [[serial number, copies], ...].")
            return None, []
        found = cards_by_serial(list(copies), problems, "in the card database")
        if len(found) < len(copies):
            return None, []
        deck.save()
        CardListEntry.objects.bulk_create(CardListEntry(card_list=deck, card=found[s], quantity=n) for s, n in copies.items() if n > 0)
        return deck, []
    code, serials = str(data.get("series", "")), [str(s) for s in data.get("anchors", ())]
    choices = cpu_anchor_choices(code) if code else []
    if not choices:
        problems.append(f"deck: the series “{code}” has no cx combo cards a CPU can play.")
        return None, []
    usable = {c.serial_number: c for c in choices}
    by_name = {}  # anchors can be given as any printing of the card
    for card in Card.objects.filter(serial_number__in=serials):
        by_name[card.serial_number] = card.name
    anchors, unusable = [], [s for s in serials if not usable.get(s) and not any(c.name == by_name.get(s) for c in choices)]
    for serial in serials:
        anchor = usable.get(serial) or next((c for c in choices if c.name == by_name.get(serial)), None)
        if anchor:
            anchors.append(anchor)
    if unusable:
        problems.append(f"deck: {', '.join(unusable)} {not_anchors(unusable)} a CPU can play in {code}.")
        return None, []
    needed = min(ANCHORS, len(choices))
    if len(anchors) != needed or len({a.pk for a in anchors}) != needed:
        problems.append(f"deck: it needs {needed} different anchors.")
        return None, []
    focus = bool(data.get("focus"))
    builder, required, notes = build_deck(series_pool(code, for_cpu=True), anchors, rng=rng, deck_name=deck.name, focus=focus)
    deck.is_deck = True
    deck.cover_card = max(anchors, key=lambda a: a.level or 0)
    deck.express = {"series": code, "anchors": [a.pk for a in anchors], "required": required, "focus": focus}
    deck.save()
    CardListEntry.objects.bulk_create(CardListEntry(card_list=deck, card_id=pk, quantity=n) for pk, n in builder.copies.items() if n)
    return deck, notes


def read_scenes(data, problems, taken=None):
    """[(name, script, infinite event)], checked for everything but the script, which needs the CPU to exist first.
    taken: the scene names already used, lowercase; None to look in the database."""
    found, names = [], set()
    for number, scene in enumerate(data or [], 1):
        name = str(scene.get("name", "")).strip()
        if not name or len(name) > 100:
            problems.append(f"scene {number}: a name, at most 100 characters, is needed.")
        elif name.lower() in names or (name.lower() in taken if taken is not None else Scene.objects.filter(name__iexact=name).exists()):
            problems.append(f"scene {number}: there's already a scene called “{name}”.")
        names.add(name.lower())
        found.append((name, str(scene.get("script", "")), bool(scene.get("infinite_event", False))))
    return found


class DryRun(Exception):
    pass


def import_cpu(data, user, rng=random, dry_run=False):
    """Make a CPU from its file: (profile, notes). Nothing is saved if anything's wrong (CorpusError, listing
    it all) or for a dry run. The CPU is never finalized: staff look it over and give it pictures first."""
    try:
        with transaction.atomic():
            problems = []
            fields = read_profile(data.get("profile"), problems)
            wanted_scenes = read_scenes(data.get("scenes"), problems)
            deck, notes = make_deck(data.get("deck"), user, rng, problems)
            if deck and (problem := deck_problem(deck)):
                problems.append(f"deck: {problem}")
            if problems:
                raise CorpusError(problems)
            profile = CpuProfile.objects.create(created_by=user, deck=deck, finalized=False, **fields)
            for name, script, infinite_event in wanted_scenes:
                _, errors = scenes.compile_scene(script)
                problems += [f"scene “{name}”, line {line}: {error}" for line, error in errors]
                Scene.objects.create(name=name, script=script, infinite_event=infinite_event, created_by=user)
            if problems:
                raise CorpusError(problems)
            if dry_run:
                raise DryRun
    except DryRun:
        pass
    return profile, notes


# --- Checking a new CPU against an export, without the database it came from ------------------------------

def load_corpus(folder):
    """(CPU names, scene names, {series: anchors}) from an export: lowercase names, to check new ones against."""
    cpus = {json.loads(path.read_text(encoding="utf-8"))["profile"]["name"] for path in (folder / "cpus").glob("*.json")}
    scene_names = {scene["name"].lower() for scene in json.loads((folder / "scenes.json").read_text(encoding="utf-8"))}
    anchors = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in (folder / "anchors").glob("*.json")}
    return cpus, scene_names, anchors


def check_offline(data, cpus, scene_names, anchors):
    """Every problem import_cpu would find with a CPU's file, as far as an export can tell: all but the deck itself,
    which express building makes on import. cpus, scene_names, anchors: from load_corpus."""
    problems = []
    fields = read_profile(data.get("profile"), problems, taken={name.lower() for name in cpus})
    wanted_scenes = read_scenes(data.get("scenes"), problems, taken=scene_names)
    deck = data.get("deck") or {}
    code, serials = str(deck.get("series", "")), [str(s) for s in deck.get("anchors", ())]
    if deck.get("cards"):
        problems.append("deck: leave out the cards: express building makes the deck from the series and anchors.")
    elif code not in anchors:
        problems.append(f"deck: the series “{code}” has no cx combo cards a CPU can play.")
    else:
        usable = {a["serial_number"]: a["name"] for a in anchors[code]}
        unusable = [s for s in serials if s not in usable]
        needed = min(ANCHORS, len(usable))
        if unusable:
            problems.append(f"deck: {', '.join(unusable)} {not_anchors(unusable)} a CPU can play in {code} "
                            f"(see anchors/{code}.json).")
        elif len({usable[s] for s in serials}) != needed or len(serials) != needed:
            problems.append(f"deck: it needs {needed} different anchors.")
    known = {name.lower(): name for name in [*cpus, fields["name"]] if name}

    def find(who):
        who = who.strip().strip('"“”').strip()
        return (SimpleNamespace(name=known[who.lower()]), None) if who.lower() in known else (None, f"There's no CPU called “{who}” in the export.")

    for name, script, _ in wanted_scenes:
        problems += [f"scene “{name}”, line {line}: {error}" for line, error in scenes.compile_scene(script, find=find)[1]]
    return problems
