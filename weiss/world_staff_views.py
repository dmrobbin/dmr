"""World mode's staff pages, under the CPU tab's World mode section: the town's places, gift items (and what each CPU
thinks of them), and chatter (what CPUs say in the town, written in the scene editor). The schedules and settings are
in weiss.world_views."""
import json
import re

from django.contrib import messages
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import chatter, quests, scenes, world
from .cpu_views import staff_required
from .models import Chatter, CpuProfile, GiftItem, Quest, Scene, WorldPlace, WorldSave
from .world_views import MAX_COINS

MAX_TAGS = 10
TAG = re.compile(r"[a-z0-9][a-z0-9-]{0,19}")


def read_tags(text, what="Tags"):
    """["sweet", "drink"] from "Sweet, drink": lowercase words, each at most 20 characters. Raises ValueError."""
    tags = []
    for raw in str(text or "").split(","):
        tag = raw.strip().lower().replace(" ", "-")
        if not tag:
            continue
        if not TAG.fullmatch(tag):
            raise ValueError(f"{what}: “{raw.strip()}” isn't a tag: use letters, numbers and dashes, at most 20.")
        if tag not in tags:
            tags.append(tag)
    if len(tags) > MAX_TAGS:
        raise ValueError(f"{what}: at most {MAX_TAGS} tags.")
    return tags


def known_tags():
    """Every tag gifts or tastes use, and the starter ones, for suggestions."""
    tags = set(world.TASTE_TAGS)
    for item_tags in GiftItem.objects.values_list("tags", flat=True):
        tags.update(item_tags or [])
    for tastes in CpuProfile.objects.values_list("gift_tastes", flat=True):
        for kind in ("loves", "likes", "dislikes"):
            tags.update((tastes or {}).get(kind, []))
    return sorted(tags)


# ---------------------------------------------------------------- Places

@staff_required
def world_places(request):
    """The town's places: their names, a backdrop for each time of day, where they are on the map, whether a flag
    opens them, and which has the card shop."""
    if request.method == "POST":
        try:
            said = change_place(request.POST)
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, said)
        return redirect("weiss:world_places")
    places = list(WorldPlace.objects.all())
    for place in places:
        place.times = list(zip(WorldSave.TIMES, [place.backdrop(time) for time in range(4)], range(4)))
        place.rules = place.schedule.count()
    return render(request, "weiss/world_places.html", {"places": places, "backgrounds": scenes.BACKGROUNDS})


def change_place(data):
    """Add, change or delete a place from a posted form. Returns what was done; raises ValueError."""
    if "delete" in data:
        place = WorldPlace.objects.filter(pk=data["delete"] or None).first()
        if not place:
            raise ValueError("That place has gone already.")
        if WorldPlace.objects.count() <= 1:
            raise ValueError("The town needs at least one place.")
        rules = place.schedule.count()
        place.delete()
        return f"{place.name} is gone{f', with its {rules} schedule rule' + ('s' if rules != 1 else '') if rules else ''}."
    name = str(data.get("name", "")).strip()[:100]
    if not name:
        raise ValueError("A place needs a name.")
    if "add" in data:
        key = slugify(data.get("key") or name)[:50]
        if not key:
            raise ValueError("Give the place a key: letters, numbers and dashes.")
        if WorldPlace.objects.filter(key=key).exists():
            raise ValueError(f"There's already a place with the key “{key}”.")
        order = (WorldPlace.objects.aggregate(top=Max("order"))["top"] or 0) + 1
        WorldPlace.objects.create(key=key, name=name, backdrops=["default"] * 4, order=order)
        return f"Added {name}, at the end of the map. Choose its backdrops below."
    place = WorldPlace.objects.filter(pk=data.get("place") or None).first()
    if not place:
        raise ValueError("That place has gone.")
    backdrops = [data.get(f"backdrop_{time}", "") for time in range(4)]
    if any(backdrop not in scenes.BACKGROUNDS for backdrop in backdrops):
        raise ValueError(f"Backdrops are {', '.join(scenes.BACKGROUNDS)}.")
    flag = str(data.get("unlock_flag", "")).strip().lower()
    if flag and not re.fullmatch(scenes.NAME, flag):
        raise ValueError("A flag is one word: letters, numbers, dashes and underscores, starting with a letter.")
    try:
        order = int(data.get("order", place.order))
    except ValueError:
        raise ValueError("The map order is a number.")
    place.name, place.backdrops, place.unlock_flag, place.shop = name, backdrops, flag, data.get("shop") == "on"
    place.order = max(0, min(order, 999))
    place.save()
    return f"Saved {place.name}."


# ---------------------------------------------------------------- Gifts, and what each CPU thinks of them

@staff_required
def world_gifts(request):
    """Gift items (sold at the card shop), and each CPU's tastes: the tags it loves, likes and dislikes."""
    if request.method == "POST":
        try:
            said = change_gifts(request.POST)
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, said)
        anchor = f"#cpu-{request.POST['tastes']}" if "tastes" in request.POST else ""
        return redirect(f"{request.path}{anchor}")
    cpus = list(CpuProfile.objects.order_by("name"))
    items = list(GiftItem.objects.all())
    for item in items:
        reactions = [world.taste(cpu, item) for cpu in cpus]
        item.loved, item.liked, item.disliked = (reactions.count(kind) for kind in ("loved", "liked", "disliked"))
        item.tag_text = ", ".join(item.tags or [])
    for cpu in cpus:
        tastes = cpu.gift_tastes or {}
        cpu.taste_text = {kind: ", ".join(tastes.get(kind, [])) for kind in ("loves", "likes", "dislikes")}
    return render(request, "weiss/world_gifts.html", {
        "items": items, "cpus": cpus, "tags": known_tags(), "untasted": sum(1 for cpu in cpus if not cpu.gift_tastes),
        "points": world.GIFT_POINTS, "per_day": world.GIFTS_PER_DAY,
    })


def change_gifts(data):
    if "fill" in data:
        made = world.give_tastes()
        return f"Gave {made} CPU{'s' if made != 1 else ''} starter tastes: change them as you like."
    if "tastes" in data:
        cpu = CpuProfile.objects.filter(pk=data["tastes"] or None).first()
        if not cpu:
            raise ValueError("That CPU has gone.")
        tastes = {kind: read_tags(data.get(kind), f"{cpu.name}: {kind}") for kind in ("loves", "likes", "dislikes")}
        twice = sorted((set(tastes["loves"]) & set(tastes["dislikes"])) | (set(tastes["likes"]) & set(tastes["dislikes"]))
                       | (set(tastes["loves"]) & set(tastes["likes"])))
        if twice:
            raise ValueError(f"{cpu.name} can't feel two ways about {', '.join(twice)}.")
        cpu.gift_tastes = tastes
        cpu.save(update_fields=["gift_tastes"])
        return f"Saved {cpu.name}'s tastes."
    if "delete" in data:
        item = GiftItem.objects.filter(pk=data["delete"] or None).first()
        if not item:
            raise ValueError("That gift has gone already.")
        item.delete()
        return f"{item.name} is gone. Saves holding one keep it out of sight; chatter giving it shows a mistake."
    name = str(data.get("name", "")).strip()[:60]
    if not name:
        raise ValueError("A gift needs a name.")
    try:
        price = int(data.get("price", ""))
        order = int(data.get("order") or 0)
    except ValueError:
        raise ValueError("The price and order are numbers.")
    if not 1 <= price <= MAX_COINS:
        raise ValueError(f"A price goes from 1 to {MAX_COINS:,}.")
    fields = {"name": name, "icon": str(data.get("icon", "")).strip()[:8], "about": str(data.get("about", "")).strip()[:200],
              "price": price, "tags": read_tags(data.get("tags")), "order": max(0, min(order, 999))}
    if "add" in data:
        key = slugify(data.get("key") or name)[:40]
        if not key:
            raise ValueError("Give the gift a key: letters, numbers and dashes.")
        if GiftItem.objects.filter(key=key).exists():
            raise ValueError(f"There's already a gift with the key “{key}”.")
        GiftItem.objects.create(key=key, **fields)
        return f"Added {name}. Chatter gives it with “give gift {key}”."
    item = GiftItem.objects.filter(pk=data.get("gift") or None).first()
    if not item:
        raise ValueError("That gift has gone.")
    for field, value in fields.items():
        setattr(item, field, value)
    item.save()
    return f"Saved {item.name}."


# ---------------------------------------------------------------- Chatter

STARTERS = {  # a new line's script, by context
    "greet": "them: Oh, hi, {player}.\nplayer: Hey.",
    "again": "them: Back again?",
    "gift_loved": "them (pleased): For me? I love it!",
    "gift_liked": "them (pleased): Oh, thanks.",
    "gift_neutral": "them: Huh. Thanks.",
    "gift_disliked": "them (dismayed): …Thanks, I guess.",
    "before_duel": "them: Let's see what you've got.",
    "after_win": "them (dismayed): Not bad.",
    "after_loss": "them (pleased): Good game.",
    "rank_up": "them (pleased): I'm glad we met, {player}.",
    "estranged": "them (dismayed): …Oh. It's you.",
    "hello": "them: Oh, hello.",
    "goodbye": "them: See you around.",
}


def first_said(script):
    """The first spoken line of a script, for a list."""
    compiled, _ = chatter.compile_chatter(script)
    return next((step["text"] for step in compiled["steps"] if step["do"] == "say"), "")


@staff_required
def world_chatter(request):
    """Every line CPUs say in the town, by CPU and moment, with how many each moment has and any with mistakes."""
    rows = Chatter.objects.select_related("cpu", "scene")
    who, context = request.GET.get("cpu", ""), request.GET.get("context", "")
    if who == "any":
        rows = rows.filter(cpu=None)
    elif who.isdigit():
        rows = rows.filter(cpu_id=int(who))
    if context in chatter.CONTEXTS:
        rows = rows.filter(context=context)
    names = world.rank_names()
    lines = list(rows)
    for line in lines:
        _, errors = chatter.compile_chatter(line.script) if line.script.strip() or not line.scene_id else (None, [])
        line.mistakes = len(errors)
        line.first = first_said(line.script) if line.script.strip() else (f"Plays the scene {line.scene.name}" if line.scene else "")
        line.rank_name = names[line.min_rank] if line.min_rank < len(names) else f"rank {line.min_rank}"
    counts = {key: {"any": 0, "own": 0} for key in chatter.CONTEXTS}
    for cpu_id, key in Chatter.objects.values_list("cpu_id", "context"):
        if key in counts:
            counts[key]["own" if cpu_id else "any"] += 1
    return render(request, "weiss/world_chatter.html", {
        "lines": lines, "cpus": CpuProfile.objects.order_by("name"), "contexts": Chatter.CONTEXTS, "who": who, "context": context,
        "coverage": [(key, label, counts[key]) for key, label in Chatter.CONTEXTS],
        "defaults": len(chatter.DEFAULTS),
    })


@staff_required
@require_POST
def world_chatter_new(request):
    context = request.POST.get("context", "")
    if context not in chatter.CONTEXTS:
        messages.error(request, "Choose when it's said.")
        return redirect("weiss:world_chatter")
    cpu = CpuProfile.objects.filter(pk=request.POST.get("cpu") or None).first()
    line = Chatter.objects.create(cpu=cpu, context=context, script=STARTERS.get(context, "them: …"),
                                  min_rank=1 if context == "rank_up" else 0)
    return redirect("weiss:world_chatter_edit", pk=line.pk)


@staff_required
def world_chatter_edit(request, pk):
    """A line, in the scene editor: who says it and when, and its script, checked as it's typed. Saving keeps a script
    with mistakes, so work isn't lost; the town leaves it out until they're fixed."""
    line = get_object_or_404(Chatter.objects.select_related("cpu", "scene"), pk=pk)
    names = world.rank_names()
    if request.method == "POST":
        try:
            read_line(request.POST, line, len(names))
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("weiss:world_chatter_edit", pk=line.pk)
        line.save()
        errors = chatter.compile_chatter(line.script)[1] if line.script.strip() or not line.scene_id else []
        if errors:
            messages.warning(request, f"Saved, with {len(errors)} mistake{'s' if len(errors) != 1 else ''}: the town leaves it out until they're fixed.")
        else:
            messages.success(request, "Saved.")
        return redirect("weiss:world_chatter_edit", pk=line.pk)
    compiled, errors = chatter.compile_chatter(line.script) if line.script.strip() or not line.scene_id else ({"labels": {}}, [])
    return render(request, "weiss/world_chatter_edit.html", {
        "line": line, "errors": errors, "labels": sorted(compiled["labels"]), "reference": chatter.REFERENCE,
        "max_script": scenes.MAX_SCRIPT, "cpus": CpuProfile.objects.order_by("name"), "contexts": Chatter.CONTEXTS,
        "ranks": list(enumerate(names)), "scenes": Scene.objects.order_by("name"), "gifts": GiftItem.objects.all(),
        "cpu_moods": chatter.CPU_MOODS,
    })


def read_line(data, line, ranks):
    context = data.get("context", "")
    if context not in chatter.CONTEXTS:
        raise ValueError("Choose when it's said.")
    try:
        min_rank, weight = int(data.get("min_rank", 0)), int(data.get("weight", 1))
    except ValueError:
        raise ValueError("The rank and weight are numbers.")
    if not 0 <= min_rank < ranks:
        raise ValueError(f"Ranks go from 0 to {ranks - 1}.")
    if not 1 <= weight <= 100:
        raise ValueError("The weight goes from 1 to 100.")
    cpu = CpuProfile.objects.filter(pk=data.get("cpu") or None).first()
    scene = Scene.objects.filter(pk=data.get("scene") or None).first() if context == "rank_up" else None
    script = str(data.get("script", "")).replace("\r\n", "\n")[:scenes.MAX_SCRIPT]
    if not script.strip() and not scene:
        raise ValueError("Write what's said (or, for a rank-up, choose a scene to play).")
    line.cpu, line.context, line.min_rank, line.weight, line.scene, line.script = cpu, context, min_rank, weight, scene, script


@staff_required
@require_POST
def world_chatter_delete(request, pk):
    line = get_object_or_404(Chatter, pk=pk)
    line.delete()
    messages.success(request, f"Deleted a line: {line}.")
    return redirect("weiss:world_chatter")


@staff_required
@require_POST
def world_chatter_check(request):
    """The editor checks the script as it's typed: its mistakes and labels, without saving it."""
    compiled, errors = chatter.compile_chatter(request.POST.get("script", "")[:scenes.MAX_SCRIPT + 1])
    return JsonResponse({"errors": errors, "labels": sorted(compiled["labels"])})


# ---------------------------------------------------------------- Quests (see weiss.quests)

STARTER_QUEST = {
    "key": "new-quest", "title": "A new quest", "giver": "", "gates": 2,
    "about": "What the quest log says it's about.",
    "offer": ["them: Can I ask you a favour?"],
    "stages": [{"text": "The first step", "objectives": [{"do": "defeat", "cpus": [""]}]}],
    "endings": [{"key": "done", "title": "Finish it", "script": ["them (pleased): Thank you."]}],
    "rewards": [{"coins": 300}],
}


def quest_preview(fields):
    """How a checked quest reads in the player's log: its stages' objectives and its endings, in words."""
    sample = WorldSave(slot=0)
    spec = fields["spec"]
    return {
        "title": fields["title"], "giver": fields["giver"] or "",
        "gate": world.rank_names()[fields["gate_rank"]] if fields["gate_rank"] and fields["gate_rank"] < len(world.rank_names()) else "",
        "about": spec["about"],
        "stages": [{"text": stage["text"], "objectives": [quests.describe(sample, obj) for obj in stage["objectives"]]} for stage in spec["stages"]],
        "endings": [{"title": ending["title"], "to": ending["to"], "locks": ending["locks"], "removes": ending["removes"],
                     "requires": [quests.describe(sample, obj) for obj in ending["requires"]]} for ending in spec["endings"]],
        "rewards": [quests.reward_text(sample, reward) for reward in spec["rewards"]],
        "hidden": spec["hidden"],
    }


def read_quest(text, but=None):
    """(fields, problems, preview, notes) for a quest's JSON as staff wrote it. `but`: the quest being edited, whose key
    it may keep. Notes are quests it locks or requires that aren't written yet: it can be saved, and they're said."""
    try:
        data = json.loads(text)
    except ValueError as error:
        return None, [f"That isn't JSON yet: {error}."], None, []
    keys = set(Quest.objects.exclude(pk=but.pk if but else None).values_list("key", flat=True))
    if isinstance(data, dict) and data.get("key") in keys:
        return None, [f"Another quest has the key “{data['key']}”."], None, []
    context = quests.known_context(extra_keys=[data.get("key")] if isinstance(data, dict) else [], loose=True)
    fields, problems = quests.check(data, context)
    preview = quest_preview(fields) if fields and not problems else None
    return fields, problems, preview, context.pending


@staff_required
def world_quest_list(request):
    """Every quest: who gives it, the rank it gates, its endings and what they close (the web of choices), any that no
    longer check out (a CPU renamed, a card gone), and which CPUs' big rank-ups have no gate quest yet."""
    found = list(Quest.objects.select_related("giver"))
    titles = {quest.key: quest.title for quest in found}
    started = {}
    for log in WorldSave.objects.exclude(quests={}).values_list("quests", flat=True):
        for key in (log or {}).get("log", {}):
            started[key] = started.get(key, 0) + 1
    context = quests.known_context(loose=True)
    names = world.rank_names()
    for quest in found:
        context.pending = []
        _, quest.problems = quests.check(quests.as_file(quest), context)
        quest.notes = context.pending
        quest.gate_name = names[quest.gate_rank] if quest.gate_rank and quest.gate_rank < len(names) else ""
        quest.endings = [{"title": e["title"], "to": e["to"], "locks": [titles.get(k, k) for k in e.get("locks", [])], "removes": e.get("removes", [])}
                         for e in quest.spec.get("endings", [])]
        quest.started = started.get(quest.key, 0)
    gated = {}
    for quest in found:
        if quest.giver_id and quest.gate_rank:
            gated.setdefault(quest.giver_id, set()).add(quest.gate_rank)
    scene_ranks = {}
    for cpu_id, rank in Chatter.objects.filter(context="rank_up", scene__isnull=False, cpu__isnull=False).values_list("cpu_id", "min_rank"):
        scene_ranks.setdefault(cpu_id, set()).add(rank)
    cpus = {cpu.pk: cpu.name for cpu in CpuProfile.objects.filter(pk__in=scene_ranks)}
    ungated = sorted((cpus[cpu_id], ", ".join(names[r] if r < len(names) else str(r) for r in sorted(ranks - gated.get(cpu_id, set()))))
                     for cpu_id, ranks in scene_ranks.items() if ranks - gated.get(cpu_id, set()))
    return render(request, "weiss/world_quest_list.html", {
        "quests": found, "ungated": ungated, "scene_cpus": len(scene_ranks), "broken": sum(1 for q in found if q.problems),
    })


@staff_required
def world_quest_edit(request, pk=None):
    """A quest as JSON, checked as it's typed, with how the player's log will read it. A quest with mistakes isn't saved
    (a broken quest could strand a save), but what was written stays on the page to fix."""
    quest = get_object_or_404(Quest.objects.select_related("giver"), pk=pk) if pk else None
    text = json.dumps(quests.as_file(quest) if quest else STARTER_QUEST, indent=2, ensure_ascii=False)
    problems, preview, notes = [], None, []
    if request.method == "POST":
        text = request.POST.get("quest", "")
        fields, problems, preview, notes = read_quest(text, but=quest)
        if not problems:
            if quest and fields["key"] != quest.key:
                quest.key = fields["key"]  # a new key for the same quest (saves that started it under the old one lose it)
                quest.save(update_fields=["key"])
            saved = quests.save_quest(fields)
            messages.success(request, f"Saved “{saved.title}”.")
            return redirect("weiss:world_quest_edit", pk=saved.pk)
        messages.error(request, f"Not saved: {len(problems)} mistake{'s' if len(problems) != 1 else ''} to fix first.")
    elif quest:
        _, problems, preview, notes = read_quest(text, but=quest)
    started = sum(1 for log in WorldSave.objects.exclude(quests={}).values_list("quests", flat=True) if quest and quest.key in (log or {}).get("log", {}))
    return render(request, "weiss/world_quest_edit.html", {
        "quest": quest, "text": text, "problems": problems, "preview": preview, "notes": notes, "started": started,
        "objectives": [(do, sorted(fields), about) for do, (fields, about) in quests.OBJECTIVES.items()],
        "ranks": list(enumerate(world.rank_names())), "places": WorldPlace.objects.all(), "gifts": GiftItem.objects.all(),
        "packs": quests.PACKS,
    })


@staff_required
@require_POST
def world_quest_check(request):
    """The editor checks the quest as it's typed: its mistakes, or how the log will read it."""
    quest = Quest.objects.filter(pk=request.POST.get("pk") or None).first()
    _, problems, preview, notes = read_quest(request.POST.get("quest", "")[:200_000], but=quest)
    html = render_to_string("weiss/world_quest_preview.html", {"preview": preview}) if preview else ""
    return JsonResponse({"problems": problems, "preview": html, "notes": notes})


@staff_required
@require_POST
def world_quest_delete(request, pk):
    quest = get_object_or_404(Quest, pk=pk)
    quest.delete()
    messages.success(request, f"Deleted “{quest.title}”. Saves that had started it no longer show it.")
    return redirect("weiss:world_quest_list")
