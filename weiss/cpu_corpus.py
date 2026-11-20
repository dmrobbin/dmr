"""CPUs as files: the CPU profiles, their decks and their scenes written out as JSON, as examples to write new
ones from, and new ones read back in. Used by the export_cpu_corpus and import_cpu commands.

A CPU's file, as both commands use it:

    {"profile": {"name": "Rapi", "model": "standard", "aggression": 1, "boss": false,
                 "intro_text": "...", "player_win_text": "...", "player_lose_text": "...", "combo_text": "..."},
     "deck": {"name": "Rapi's deck", "series": "NIK", "anchors": ["NIK/S117-E001", "NIK/S117-E020"], "focus": false,
              "cards": [["NIK/S117-E001", 4], ...]},
     "scenes": [{"name": "Rapi: First meeting", "script": "cast rapi as Rapi\\n...", "infinite_event": false}],
     "world": {"temperament": "friendly",
               "schedule": [{"place": "cafe", "days": [0, 1, 2, 3, 4], "times": [1, 2], "weight": 60,
                             "once_per_day": false, "min_rank": 0, "stake": 0}],
               "gift_tastes": {"loves": ["sweet"], "likes": ["drink", "cards"], "dislikes": ["spicy"]},
               "chatter": [{"context": "greet", "min_rank": 0, "weight": 1, "script": "them: Oh, hi, {player}."},
                           {"context": "rank_up", "min_rank": 3, "scene": "Rapi: First meeting"}],
               "quests": [{"key": "rapi-orders", "title": "Orders", "gates": 2, "about": "...",
                           "stages": [{"text": "...", "objectives": [{"do": "defeat", "cpus": ["Anis"]}]}],
                           "endings": [{"key": "done", "title": "Report back"}]}]}}

A deck is built by express building from its series and anchors, unless it lists its cards, which are then taken
as they are. An export also writes "context" (the deck's key cards, where its scenes play), which an import ignores.

Cards go by serial number, not by id, so a file from one database means the same in another.
"""
import json
import random
import re
from types import SimpleNamespace

from django.db import transaction

from . import abilities, buffs, chatter, cpu, quests, scenes
from .cpu_views import MAX_TEXT, TEXT_FIELDS, deck_problem, scene_uses
from .express import ANCHORS, build_deck, cpu_anchor_choices, series_pool
from .models import Card, CardList, CardListEntry, Chatter, CpuProfile, CpuSchedule, GiftItem, Quest, Scene, WorldPlace, WorldSettings, TutorialLine
from .views import series_code

PROFILE_FIELDS = ("name", "model", "aggression", "boss", *TEXT_FIELDS)
RULE_FIELDS = ("place", "days", "times", "weight", "once_per_day", "min_rank", "stake")
TEMPERAMENTS = [key for key, _ in CpuProfile._meta.get_field("temperament").choices]
CHATTER_FIELDS = ("context", "min_rank", "weight", "script", "scene")
TASTES = ("loves", "likes", "dislikes")
MAX_STAKE = 1_000_000
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


def world_record(profile):
    """A CPU's part in world mode: where it's found, what gifts it likes, and what it says."""
    return {
        "temperament": profile.temperament,
        "schedule": [{"place": rule.place.key, "days": rule.days, "times": rule.times, "weight": rule.weight,
                      "once_per_day": rule.once_per_day, "min_rank": rule.min_rank, "stake": rule.stake}
                     for rule in profile.schedule.select_related("place").order_by("-weight", "pk")],
        "gift_tastes": {kind: list((profile.gift_tastes or {}).get(kind, [])) for kind in TASTES} if profile.gift_tastes else {},
        "chatter": [{"context": line.context, "min_rank": line.min_rank, "weight": line.weight, "script": line.script,
                     **({"scene": line.scene.name} if line.scene else {})}
                    for line in profile.chatter.select_related("scene").order_by("context", "min_rank", "pk")],
        "quests": [{k: v for k, v in quests.as_file(quest).items() if k != "giver"}
                   for quest in profile.quests.select_related("giver").order_by("order", "pk")],
    }


def world_info():
    """What a CPU file's world part can name, for checking one without the database: places, gifts and their tags,
    the moments chatter is said at, and the friendship ranks."""
    from . import world
    tags = set(world.TASTE_TAGS)
    gifts = []
    for item in GiftItem.objects.all():
        tags.update(item.tags or [])
        gifts.append({"key": item.key, "name": item.name, "tags": item.tags})
    return {"places": [{"key": place.key, "name": place.name, "shop": place.shop, "secluded": place.secluded}
                       for place in WorldPlace.objects.all()],
            "temperaments": dict(CpuProfile._meta.get_field("temperament").choices), "max_per_place": world.MAX_PER_PLACE,
            "max_on_stage": world.MAX_ON_STAGE,
            "gifts": gifts, "tags": sorted(tags), "contexts": dict(Chatter.CONTEXTS), "ranks": world.rank_names(),
            "cpu_moods": list(chatter.CPU_MOODS),
            "quests": sorted(Quest.objects.values_list("key", flat=True)),
            "objectives": {do: {"fields": sorted(fields), "about": about} for do, (fields, about) in quests.OBJECTIVES.items()}}


def export_profile(profile, casts, uses):
    """A CPU's file, with the scenes that cast it."""
    record = {"profile": {field: getattr(profile, field) for field in PROFILE_FIELDS}, "deck": None, "scenes": [],
              "context": {"id": profile.pk, "finalized": profile.finalized, "key_cards": [], "scenes_play": {},
                          "images": {screen: getattr(profile, field).name for screen, field in CpuProfile.SCREENS.items()
                                     if getattr(profile, field) and getattr(profile, field).name}}}
    record["world"] = world_record(profile)
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
    lines += world_reference()
    return "\n".join(lines) + "\n"


def world_reference():
    """The reference's world mode part."""
    info = world_info()
    lines = ["", "## World mode (`world`)", "",
             "All optional. A CPU with no schedule gets a starting one when it's finalized, and one with no gift tastes "
             "gets starter tastes; one with no chatter says the built-in lines (chatter.json) and any written for every CPU.", "",
             "### `temperament`", "",
             "How fast it comes to like the player: " + ", ".join(f"`{key}` ({label})" for key, label in info["temperaments"].items()) + ".", "",
             "### `schedule`: its haunts", "",
             f"Each save draws who's out fresh every day: at most {info['max_per_place']} CPUs at a place and {info['max_on_stage']} in "
             "town at once. A haunt says where the CPU can turn up, and when; the heavier, the likelier.",
             f"- `place`: one of {', '.join(f'`{place['key']}`' for place in info['places'])} (world.json has their names; "
             "the secluded ones are where villains keep to). The card shop is for shopping: better not to put a CPU there.",
             "- `days`: 0 (Monday) to 6 (Sunday). `times`: 0 morning, 1 noon, 2 evening, 3 night.",
             "- `weight`: 1 to 100. `once_per_day`: there at most once a day.",
             "- `min_rank`: the friendship rank the player needs for this haunt (0: always). A villain's daytime haunts wait for a friend.",
             f"- `stake`: a high-stakes entry fee when it's there by this haunt (0 for none, at most {MAX_STAKE:,}); a win pays it back twice.",
             "", "A CPU should have a home most days, somewhere at weekends, and somewhere it wanders: three or four haunts.", "",
             "### `gift_tastes`", "",
             f"Tags it `loves`, `likes` and `dislikes`, each in only one list. Tags gifts have: {', '.join(info['tags'])}. "
             "A gift with a loved tag is loved (even if it also has a disliked one), then disliked, then liked, else neutral.", "",
             "### `chatter`: what it says in the town", "",
             "Each line: `context` (when it's said), `min_rank` (the friendship rank it needs, 0 the first: "
             f"{', '.join(f'{i} {name}' for i, name in enumerate(info['ranks']))}), `weight` (1 to 100, how often it's picked) and `script`. "
             "Of the lines that fit, those for the highest rank reached win. For `rank_up`, `min_rank` is the rank reached, "
             "and `scene` can name a scene (in this file, or one there already) to play instead of a script.", ""]
    lines += [f"- `{key}`: {label}." for key, label in info["contexts"].items()]
    lines += ["", "A script is the scene language's compact form: the CPU is `them`, and there's no stage.", ""]
    lines += [f"- `{example}`: {meaning}" for example, meaning, _ in chatter.REFERENCE]
    lines += ["", f"Gift keys for `give gift`: {', '.join(gift['key'] for gift in info['gifts'])}."]
    lines += ["", "### `quests`: what it asks of the player", "",
              "Each quest is given by this CPU. `gates` (a rank) holds its friendship below that rank until the quest is done: "
              "the big rank-ups, the ones with scenes (Friend and Best friend), should each wait on one. A gate quest is offered "
              "once the player has that rank's points. Quests are found by `key` (lowercase, - and _), so other quests can "
              "require or lock them, including other CPUs' quests.", "",
              "```", quests.__doc__.split("A quest is a Quest row: its key, title, giver and the friendship rank it gates, and a spec (checked by `check`):")[1]
              .split("How it plays out")[0].strip("\n"), "```", "",
              "Objectives (`do`), each with an optional `text` to say it in your own words; CPUs by name, cards by serial "
              "number (any printing of the card's name counts):", ""]
    lines += [f"- `{do}` ({', '.join(f'`{field}`' for field in sorted(fields))}): {about}" for do, (fields, about) in quests.OBJECTIVES.items()]
    lines += ["", "An ending's `locks` closes other quests for good (by key), and `removes` sends CPUs away for good: the player "
              "is shown exactly what before choosing. Closing a gate quest leaves its giver at the rank below, in that save.",
              f"Rewards: `{{\"coins\": n}}`, `{{\"card\": serial, \"copies\": n}}`, `{{\"pack\": one of {', '.join(quests.PACKS)}}}`, "
              "`{\"gift\": key}`, `{\"flag\": name, \"text\": what it means}`; `\"hidden\": true` keeps them a surprise."]
    return lines


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
    files["world.json"] = json.dumps(world_info(), indent=2, ensure_ascii=False)
    lines = []
    for context, min_rank, script in chatter.DEFAULTS:
        lines.append({"context": context, "min_rank": min_rank, "script": script})
    for line in Chatter.objects.filter(cpu=None).order_by("context", "min_rank", "pk"):
        lines.append({"context": line.context, "min_rank": line.min_rank, "weight": line.weight, "script": line.script, "any_cpu": True})
    files["chatter.json"] = json.dumps(lines, indent=2, ensure_ascii=False)
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


def joined(script):
    """A script as text: a pack can write one as a list of lines, which reads (and diffs) better."""
    return "\n".join(str(line) for line in script) if isinstance(script, list) else str(script or "")


def quest_context(info, scene_names=(), cpus=(), quest_keys=(), offline=False):
    """What a CPU file's quests can name (see quests.check): the places, gifts and ranks in `info`, these CPUs (and the
    database's, unless offline), these scenes and quests (and the database's), and cards (unchecked offline)."""
    names = {} if offline else {name.lower(): name for name in CpuProfile.objects.values_list("name", flat=True)}
    names.update({name.lower(): name for name in cpus})
    scene_set = {name.lower() for name in scene_names}
    return SimpleNamespace(
        cpus=names, places={place["key"] for place in info["places"]}, gifts={gift["key"] for gift in info["gifts"]},
        ranks=info["ranks"], quests={*info.get("quests", []), *quest_keys},
        cards=None if offline else (lambda serial: Card.objects.filter(serial_number=serial).exists()),
        scenes=(lambda name: name.lower() in scene_set) if offline else
        (lambda name: name.lower() in scene_set or Scene.objects.filter(name__iexact=name).exists()))


def read_quests(raw, giver, problems, context):
    """The quests a CPU's world part gives, checked: [quests.check fields]."""
    if raw is None:
        return None
    if not isinstance(raw, list):
        problems.append("world quests: a list of quests.")
        return []
    found, keys = [], set()
    for number, data in enumerate(raw, 1):
        if isinstance(data, dict) and data.get("giver") and str(data["giver"]).lower() != giver.lower():
            problems.append(f"world quest {number}: a CPU's quests are its own to give; leave out the giver.")
        fields, errors = quests.check({**data, "giver": giver} if isinstance(data, dict) else data, context, giver=giver)
        problems += [f"world quest {number}: {error}" for error in errors]
        if fields:
            if fields["key"] in keys:
                problems.append(f"world quest {number}: another of its quests has the key “{fields['key']}”.")
            keys.add(fields["key"])
            found.append(fields)
    return found


def quest_keys(entries):
    """Every quest key the world parts of these files or pack entries name, so one quest can lock another's."""
    return {str(q.get("key")) for world_part in entries if isinstance(world_part, dict)
            for q in (world_part.get("quests") or []) if isinstance(q, dict) and q.get("key")}


def read_world(data, problems, info, scene_names=(), giver=None, names=None):
    """(schedule rules, gift tastes, chatter lines, temperament, quests), checked; info: world_info() (or world.json,
    offline); scene_names: the scenes a rank-up can play (lowercase), besides those in the database when checking
    online. giver: the CPU's name, for its quests; names: what they can name (quest_context). Quests are None when
    the part has none to say (so an import leaves the CPU's quests be)."""
    data = data or {}
    if not isinstance(data, dict):
        problems.append("world: write it as {\"schedule\": [...], \"gift_tastes\": {...}, \"chatter\": [...]}.")
        return [], {}, [], None, None
    unknown = sorted(set(data) - {"temperament", "schedule", "gift_tastes", "chatter", "quests"})
    if unknown:
        problems.append(f"world: no such fields as {', '.join(unknown)}.")
    places = {place["key"] for place in info["places"]}
    rules = []
    for number, rule in enumerate(data.get("schedule") or [], 1):
        where = f"world schedule rule {number}"
        if not isinstance(rule, dict):
            problems.append(f"{where}: write it as {{\"place\": ..., \"days\": [...], \"times\": [...]}}.")
            continue
        if extra := sorted(set(rule) - set(RULE_FIELDS)):
            problems.append(f"{where}: no such fields as {', '.join(extra)}.")
        days, times = rule.get("days"), rule.get("times")
        fields = {"place": rule.get("place"), "weight": rule.get("weight", 50), "min_rank": rule.get("min_rank", 0),
                  "stake": rule.get("stake", 0), "once_per_day": bool(rule.get("once_per_day", False))}
        if fields["place"] not in places:
            problems.append(f"{where}: there's no place “{fields['place']}”; places are {', '.join(sorted(places))}.")
        if not isinstance(days, list) or not days or any(not isinstance(d, int) or not 0 <= d <= 6 for d in days):
            problems.append(f"{where}: days are a list of 0 (Monday) to 6 (Sunday).")
        if not isinstance(times, list) or not times or any(not isinstance(t, int) or not 0 <= t <= 3 for t in times):
            problems.append(f"{where}: times are a list of 0 (morning) to 3 (night).")
        if not isinstance(fields["weight"], int) or not 1 <= fields["weight"] <= 100:
            problems.append(f"{where}: the weight goes from 1 to 100.")
        if not isinstance(fields["min_rank"], int) or not 0 <= fields["min_rank"] < len(info["ranks"]):
            problems.append(f"{where}: min_rank goes from 0 to {len(info['ranks']) - 1}.")
        if not isinstance(fields["stake"], int) or not 0 <= fields["stake"] <= MAX_STAKE:
            problems.append(f"{where}: the stake goes from 0 to {MAX_STAKE:,}.")
        rules.append({**fields, "days": sorted(set(days)) if isinstance(days, list) else [],
                      "times": sorted(set(times)) if isinstance(times, list) else []})
    temperament = data.get("temperament")
    if temperament is not None and temperament not in info.get("temperaments", TEMPERAMENTS):
        problems.append(f"world: the temperament must be one of {', '.join(info.get('temperaments', TEMPERAMENTS))}.")
    tastes = {}
    raw = data.get("gift_tastes") or {}
    if not isinstance(raw, dict) or set(raw) - set(TASTES):
        problems.append("world gift_tastes: write it as {\"loves\": [...], \"likes\": [...], \"dislikes\": [...]}.")
    else:
        for kind in TASTES:
            tags = raw.get(kind, [])
            if not isinstance(tags, list) or any(not isinstance(tag, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", tag) for tag in tags):
                problems.append(f"world gift_tastes: {kind} is a list of tags: lowercase letters, numbers and dashes.")
                tags = []
            if raw:
                tastes[kind] = list(dict.fromkeys(tags))
        twice = sorted(tag for i, a in enumerate(TASTES) for b in TASTES[i + 1:] for tag in set(tastes.get(a, [])) & set(tastes.get(b, [])))
        if twice:
            problems.append(f"world gift_tastes: {', '.join(twice)} can only be in one list.")
    lines = []
    gifts = {gift["key"] for gift in info["gifts"]}
    for number, line in enumerate(data.get("chatter") or [], 1):
        if not isinstance(line, dict):
            problems.append(f"world chatter {number}: write it as {{\"context\": ..., \"script\": ...}}.")
            continue
        context = line.get("context")
        where = f"world chatter {number} ({context})"
        if extra := sorted(set(line) - set(CHATTER_FIELDS)):
            problems.append(f"{where}: no such fields as {', '.join(extra)}.")
        if context not in info["contexts"]:
            problems.append(f"world chatter {number}: the context must be one of {', '.join(info['contexts'])}.")
        min_rank, weight = line.get("min_rank", 1 if context == "rank_up" else 0), line.get("weight", 1)
        if not isinstance(min_rank, int) or not 0 <= min_rank < len(info["ranks"]):
            problems.append(f"{where}: min_rank goes from 0 to {len(info['ranks']) - 1}.")
        if not isinstance(weight, int) or not 1 <= weight <= 100:
            problems.append(f"{where}: the weight goes from 1 to 100.")
        script, scene = joined(line.get("script")), line.get("scene")
        if scene and context != "rank_up":
            problems.append(f"{where}: only a rank_up line can play a scene.")
        elif scene and str(scene).lower() not in scene_names and not Scene.objects.filter(name__iexact=str(scene)).exists():
            problems.append(f"{where}: there's no scene called “{scene}”.")
        if not script.strip() and not scene:
            problems.append(f"{where}: it needs a script (or, for a rank_up, a scene).")
        elif script.strip():
            problems += [f"{where}, line {at}: {error}" for at, error in chatter.compile_chatter(script, gifts=gifts)[1]]
        lines.append({"context": context, "min_rank": min_rank, "weight": weight, "script": script, "scene": str(scene) if scene else None})
    found_quests = None
    if data.get("quests") is not None:
        found_quests = read_quests(data["quests"], giver or "", problems,
                                   names or quest_context(info, scene_names, cpus=[giver] if giver else [], quest_keys=quest_keys([data])))
    return rules, tastes, lines, temperament, found_quests


def make_world(profile, rules, tastes, lines, temperament=None, found_quests=None):
    """Saves a CPU's world part, once the CPU (and the batch's scenes) exist. Its quests (if the part had some to say)
    replace the CPU's own; saves that started one keep their place in it, by its key."""
    if temperament:
        profile.temperament = temperament
        profile.save(update_fields=["temperament"])
    places = {place.key: place for place in WorldPlace.objects.all()}
    CpuSchedule.objects.bulk_create(CpuSchedule(cpu=profile, place=places[rule["place"]], **{k: v for k, v in rule.items() if k != "place"})
                                    for rule in rules)
    if tastes:
        profile.gift_tastes = tastes
        profile.save(update_fields=["gift_tastes"])
    for line in lines:
        scene = Scene.objects.filter(name__iexact=line["scene"]).first() if line["scene"] else None
        Chatter.objects.create(cpu=profile, context=line["context"], min_rank=line["min_rank"], weight=line["weight"],
                               script=line["script"], scene=scene)
    if found_quests is not None:
        for order, fields in enumerate(found_quests):
            quests.save_quest({**fields, "giver": profile.name}, order=order)
        profile.quests.exclude(key__in=[fields["key"] for fields in found_quests]).delete()


class DryRun(Exception):
    pass


def import_cpus(files, user, seed=None, dry_run=False, rngs=None):
    """Make CPUs from several files in one go: a result for each file, in order, with .profile (None if it couldn't be
    made), .notes (from express building), .problems and .cards (its deck, [(card, copies)], as built).

    Every file's profile is made before any file's scenes, so a scene can cast a CPU from another file of the batch,
    whatever order they come in. The batch goes in whole or not at all: nothing is saved if any file has a problem,
    or for a dry run. Each deck is built with random.Random(seed) (or rngs, one for each file), as a single import
    of that file would be, so a dry run's decks are the ones the real run builds. No CPU is finalized: staff look
    them over and give them pictures first."""
    from .lists import sorted_entries  # weiss.lists is imported by weiss.cpu_views, which this module needs first

    results = [SimpleNamespace(data=data, profile=None, notes=[], problems=[], cards=[], scenes=[], world=None) for data in files]
    info = world_info()
    rngs = rngs or [random.Random(seed) for _ in files]
    try:
        with transaction.atomic():
            batch_scenes = {}
            for result, rng in zip(results, rngs):
                fields = read_profile(result.data.get("profile"), result.problems)
                result.scenes = read_scenes(result.data.get("scenes"), result.problems)
                for name, _, _ in result.scenes:  # two files of the batch can't both have a scene by one name
                    if batch_scenes.setdefault(name.lower(), result) is not result:
                        result.problems.append(f"scene “{name}”: another file of this batch has a scene called that.")
                deck, result.notes = make_deck(result.data.get("deck"), user, rng, result.problems)
                if deck:
                    result.cards = [(entry.card, entry.quantity) for entry in sorted_entries(deck)]
                    if problem := deck_problem(deck):
                        result.problems.append(f"deck: {problem}")
                if not result.problems:  # made now, so the scenes below (this file's or any other's) can cast it
                    result.profile = CpuProfile.objects.create(created_by=user, deck=deck, finalized=False, **fields)
            for result in results:
                if not result.profile:
                    continue
                for name, script, infinite_event in result.scenes:
                    _, errors = scenes.compile_scene(script)
                    result.problems += [f"scene “{name}”, line {line}: {error}" for line, error in errors]
                    Scene.objects.create(name=name, script=script, infinite_event=infinite_event, created_by=user)
            batch_keys = quest_keys([result.data.get("world") for result in results])
            for result in results:  # once every scene of the batch is made, for rank-ups to play
                if not result.profile:
                    continue
                result.world = read_world(result.data.get("world"), result.problems, info, giver=result.profile.name,
                                          names=quest_context(info, quest_keys=batch_keys))
                if not result.problems:
                    make_world(result.profile, *result.world)
            if dry_run or any(result.problems for result in results):
                raise DryRun
    except DryRun:
        pass
    return results


def import_cpu(data, user, rng=random, dry_run=False):
    """Make a CPU from its file: (profile, notes). Nothing is saved if anything's wrong (CorpusError, listing
    it all) or for a dry run. The CPU is never finalized: staff look it over and give it pictures first."""
    result = import_cpus([data], user, dry_run=dry_run, rngs=[rng])[0]
    if result.problems:
        raise CorpusError(result.problems)
    return result.profile, result.notes


# --- Checking a new CPU against an export, without the database it came from ------------------------------

def load_corpus(folder):
    """(CPU names, scene names, {series: anchors}, world info) from an export: lowercase names, to check new ones
    against; world info is world.json (None in an export from before world mode)."""
    cpus = {json.loads(path.read_text(encoding="utf-8"))["profile"]["name"] for path in (folder / "cpus").glob("*.json")}
    scene_names = {scene["name"].lower() for scene in json.loads((folder / "scenes.json").read_text(encoding="utf-8"))}
    anchors = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in (folder / "anchors").glob("*.json")}
    world_file = folder / "world.json"
    info = json.loads(world_file.read_text(encoding="utf-8")) if world_file.exists() else None
    return cpus, scene_names, anchors, info


def check_offline(data, cpus, scene_names, anchors, info=None):
    """Every problem import_cpu would find with a CPU's file, as far as an export can tell: all but the deck itself,
    which express building makes on import. cpus, scene_names, anchors, info: from load_corpus."""
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
    if data.get("world"):
        if info is None:
            problems.append("world: this export is from before world mode; export again to check it.")
        else:
            known_scenes = {*scene_names, *(name.lower() for name, _, _ in wanted_scenes)}
            read_world(data["world"], problems, info, scene_names=known_scenes, giver=fields["name"],
                       names=quest_context(info, known_scenes, cpus=[*cpus, fields["name"] or ""], quest_keys=quest_keys([data["world"]]), offline=True))
    return problems


# --- World packs: world mode for CPUs that exist already ------------------------------------------------------

def import_world_pack(files, dry_run=False, user=None, known=None):
    """Give existing CPUs their part in world mode from pack files: [{"cpus": [{"name", "world", "scenes"}]}]. A CPU is
    found by name; its haunts and chatter are replaced by the pack's, and its tastes and temperament set. A pack's
    scenes (a rank-up's, say) are made, or their scripts updated if a scene has that name already. A result for each
    file, in order, with .problems (nothing's saved if any file has one, or for a dry run), .missing (CPUs the pack
    names that aren't here: skipped) and .done ([(CPU name, what it got)]). known: CPU names to check against instead
    of the database, with nothing made (an offline check against an export)."""
    results = [SimpleNamespace(problems=[], missing=[], done=[]) for _ in files]
    info = world_info()
    pack_scenes = {}
    for data, result in zip(files, results):
        for number, scene in enumerate(data.get("scenes") or [], 1):
            name = str(scene.get("name", "")).strip()
            if not name or len(name) > 100:
                result.problems.append(f"scene {number}: a name, at most 100 characters, is needed.")
            elif name.lower() in pack_scenes:
                result.problems.append(f"scene “{name}”: the pack has two scenes called that.")
            pack_scenes[name.lower()] = (name, joined(scene.get("script")), result)
        for entry in data.get("cpus") or []:
            for number, scene in enumerate(entry.get("scenes") or [], 1):
                name = str(scene.get("name", "")).strip()
                if not name or len(name) > 100:
                    result.problems.append(f"{entry.get('name')}: scene {number} needs a name, at most 100 characters.")
                elif name.lower() in pack_scenes:
                    result.problems.append(f"scene “{name}”: the pack has two scenes called that.")
                pack_scenes[name.lower()] = (name, joined(scene.get("script")), result)
    names = {name.lower(): name for name in (known if known is not None else CpuProfile.objects.values_list("name", flat=True))}

    def find(who):
        who = who.strip().strip('"“”').strip()
        if who.lower() == quests.MENTOR:  # the story's scenes cast whoever the player chose as their guide
            return SimpleNamespace(name=quests.MENTOR, pk=0), None
        if known is not None:
            return (SimpleNamespace(name=names[who.lower()]), None) if who.lower() in names else (None, f"There's no CPU called “{who}”.")
        return scenes.find_cpu(who)

    for name, script, result in pack_scenes.values():
        result.problems += [f"scene “{name}”, line {line}: {error}" for line, error in scenes.compile_scene(script, find=find)[1]]
    wanted = []
    pack_keys = quest_keys([entry.get("world") for data in files for entry in data.get("cpus") or []])
    pack_keys |= {str(chapter.get("key")) for data in files for chapter in data.get("story") or [] if isinstance(chapter, dict) and chapter.get("key")}
    story = []  # (checked fields, its file's result): a story file's chapters (weiss.quests, story quests)
    for data, result in zip(files, results):
        raw = data.get("story")
        if raw is None:
            continue
        if not isinstance(raw, list):
            result.problems.append("story: a list of chapters (quests with \"story\": true).")
            continue
        context = quest_context(info, set(pack_scenes), cpus=names.values(), quest_keys=pack_keys, offline=known is not None)
        for number, chapter in enumerate(raw, 1):
            if not isinstance(chapter, dict) or not chapter.get("story"):
                result.problems.append(f"story chapter {number}: give it \"story\": true (a story file's quests are its chapters).")
                continue
            fields, errors = quests.check(chapter, context)
            result.problems += [f"story chapter {number}: {error}" for error in errors]
            if fields and not errors:
                story.append((fields, result))
    for data, result in zip(files, results):
        for number, entry in enumerate(data.get("cpus") or [], 1):
            name = str(entry.get("name", "")).strip()
            if name.lower() not in names:
                result.missing.append(name or f"CPU {number}")
                continue
            before = len(result.problems)
            found = read_world(entry.get("world"), result.problems, info, scene_names=set(pack_scenes), giver=names[name.lower()],
                               names=quest_context(info, set(pack_scenes), cpus=names.values(), quest_keys=pack_keys, offline=known is not None))
            result.problems[before:] = [f"{names[name.lower()]}: {problem}" for problem in result.problems[before:]]
            wanted.append((names[name.lower()], found, result))
    tutorial_parts = []  # (guides, [(step, cpu name or None, script)], its file's result): a story file's TUTORIAL
    for data, result in zip(files, results):
        raw = data.get("tutorial")
        if raw is None:
            continue
        found = read_tutorial(raw, result.problems, names)
        if found:
            tutorial_parts.append((*found, result))
    chapters = {}
    for fields, result in story:
        chapters.setdefault(id(result), [result, 0])[1] += 1
    if dry_run or known is not None or any(result.problems for result in results):
        for name, (rules, tastes, lines, _, found_quests), result in wanted:
            result.done.append((name, done_words(rules, lines, found_quests)))
        for result, count in chapters.values():
            result.done.append(("The story", f"{count} chapter{'s' if count != 1 else ''}"))
        for guides, lines, result in tutorial_parts:
            result.done.append(("The tutorial", f"{len(guides)} guides, {len(lines)} scripts"))
        return results
    with transaction.atomic():
        for name, script, _ in pack_scenes.values():
            scene = Scene.objects.filter(name__iexact=name).first()
            if scene:
                scene.script = script
                scene.save(update_fields=["script", "updated"])
            else:
                Scene.objects.create(name=name, script=script, created_by=user)
        for name, (rules, tastes, lines, temperament, found_quests), result in wanted:
            profile = CpuProfile.objects.get(name__iexact=name)
            profile.schedule.all().delete()
            profile.chatter.all().delete()
            make_world(profile, rules, tastes, lines, temperament, found_quests)
            result.done.append((name, done_words(rules, lines, found_quests)))
        for order, (fields, _) in enumerate(story, 1):  # the story's chapters, by key: saves keep their place in them
            quests.save_quest(fields, order=order)
        for guides, lines, _ in tutorial_parts:  # the tutorial: its guides, and every step's lines replaced
            WorldSettings.objects.update_or_create(pk=1, defaults={"tutorial_guides": guides})
            TutorialLine.objects.all().delete()
            for step, cpu_name, script in lines:
                TutorialLine.objects.create(step=step, cpu=CpuProfile.objects.filter(name__iexact=cpu_name).first() if cpu_name else None,
                                            script=script)
        for result, count in chapters.values():
            result.done.append(("The story", f"{count} chapter{'s' if count != 1 else ''}"))
        for guides, lines, result in tutorial_parts:
            result.done.append(("The tutorial", f"{len(guides)} guides, {len(lines)} scripts"))
    return results


def read_tutorial(raw, problems, names):
    """A story file's TUTORIAL, checked: ([guide names], [(step, cpu name or None, script)]), or None. Each script is
    chatter with plain lines only (them, player, narrator): the tutorial (weiss.world_tutorial) does the rest."""
    from . import world_tutorial
    if not isinstance(raw, dict) or not isinstance(raw.get("lines"), dict):
        problems.append('tutorial: write it as {"guides": [...], "lines": {step: {"*" or a guide: [lines]}}}.')
        return None
    guides = []
    for name in raw.get("guides") or []:
        if str(name).lower() not in names:
            problems.append(f"tutorial: there's no CPU called “{name}” to be a guide.")
        else:
            guides.append(names[str(name).lower()])
    if not guides:
        problems.append("tutorial: name at least one guide.")
    lines = []
    for step, by_guide in raw["lines"].items():
        if step not in world_tutorial.STEPS:
            problems.append(f"tutorial: there's no step “{step}” (the steps are {', '.join(world_tutorial.STEPS)}).")
            continue
        for who, script in (by_guide or {}).items():
            if who != "*" and str(who).lower() not in names:
                problems.append(f"tutorial {step}: there's no CPU called “{who}”.")
                continue
            text = joined(script)
            compiled, errors = chatter.compile_chatter(text)
            problems += [f"tutorial {step} ({who}), line {line}: {error}" for line, error in errors]
            if any(s["do"] != "say" for s in compiled["steps"]):
                problems.append(f"tutorial {step} ({who}): only lines (them, player, narrator); no choices, points or gifts.")
            lines.append((step, None if who == "*" else names[str(who).lower()], text))
    return guides, lines


def done_words(rules, lines, found_quests):
    words = f"{len(rules)} haunts, {len(lines)} lines"
    return words + (f", {len(found_quests)} quest{'s' if len(found_quests) != 1 else ''}" if found_quests else "")
