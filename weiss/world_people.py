"""The people journal (docs/round-two-plan.md, section 4): everyone the town's cast has, the ones this save has met in full,
and the rest as locked entries with no name. Each met person has their rank and its progress, the player's record against
them, the gifts they took (only those the player has given), their quests and their journal entries, which unlock with rank.

Built in batches, so the cost of a page doesn't grow with the number of people: one query each for the cast, the journal
lines, the gift names, the decks' cards and the quests; the ranks and quest statuses are worked out from those."""
from collections import defaultdict

from . import chatter, play, quests, world
from .models import CardListEntry, Chatter, GiftItem


def people(save):
    """The journal for this save: {"met": [person, ...] (by name), "unmet": [{"id"}], "met_count", "total"}. The cast is the
    town's (world.town_cast), so the total is only ever people who can show up."""
    rows = world.ranks()
    cast = list(world.town_cast().order_by("name", "pk"))
    met = [cpu for cpu in cast if str(cpu.pk) in save.relations]
    unmet = [{"id": cpu.pk} for cpu in cast if str(cpu.pk) not in save.relations]
    journal = defaultdict(list)  # cpu id -> [(min rank, script)], in rank order
    for cpu_id, min_rank, script in Chatter.objects.filter(context="journal", cpu_id__in=[cpu.pk for cpu in met]) \
            .order_by("cpu_id", "min_rank", "pk").values_list("cpu_id", "min_rank", "script"):
        journal[cpu_id].append((min_rank, script))
    tastes = {key for cpu in met for key in save.relations[str(cpu.pk)].get("tastes", {})}
    gift_names = dict(GiftItem.objects.filter(key__in=tastes).values_list("key", "name"))
    deck_ids = [cpu.deck_id for cpu in met if cpu.deck_id]
    deck_cards = defaultdict(list)
    for deck_id, color, quantity in CardListEntry.objects.filter(card_list_id__in=deck_ids).values_list("card_list_id", "card__color", "quantity"):
        deck_cards[deck_id].append((color, quantity))
    quest_rows = defaultdict(list)  # giver id -> the quests they give, with their status (none: not taken)
    for quest in quests.quests(save).values():
        status = quests.status(save, quest.key)
        if quest.giver_id and status in ("active", "settling", "done", "failed"):
            quest_rows[quest.giver_id].append({"title": quest.title, "status": "active" if status == "settling" else status})
    people_met = [person(save, cpu, rows, journal[cpu.pk], gift_names, deck_cards[cpu.deck_id], quest_rows[cpu.pk]) for cpu in met]
    return {"met": people_met, "unmet": unmet, "met_count": len(met), "total": len(cast)}


def person(save, cpu, rows, journal_rows, gift_names, cards, quest_rows):
    rel = save.relations[str(cpu.pk)]
    points = rel.get("points", 0)
    held = quests.cap(save, cpu.pk)  # the rank a gate quest holds back to (no query: the save's quests are already known)
    rank = max(i for i, row in enumerate(rows) if points >= row["points"])
    rank = rank if held is None else min(rank, held)
    nxt = rows[rank + 1] if rank + 1 < len(rows) else None
    if nxt is None or nxt["points"] <= rows[rank]["points"]:
        progress = 1.0
    else:
        progress = min(1.0, max(0.0, (points - rows[rank]["points"]) / (nxt["points"] - rows[rank]["points"])))
    values = {"player": save.user.username, "name": cpu.name, "rank": rows[rank]["name"]}

    def fill(text):
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        return text
    tastes = rel.get("tastes", {})

    def named(kind):
        return sorted((gift_names.get(key, key) for key, reaction in tastes.items() if reaction == kind), key=str.lower)
    entries = []
    for min_rank, script in journal_rows:  # a locked entry is not compiled: it has no text to show
        unlocked = min_rank <= rank
        text = ""
        if unlocked and script.strip():
            compiled, errors = chatter.compile_chatter(script)
            if not errors and compiled["steps"]:
                text = fill(chatter.first_said(compiled)[1])
        entries.append({"text": text, "unlocked": unlocked, "rank_name": rows[min_rank]["name"] if min_rank < len(rows) else ""})
    return {"id": cpu.pk, "name": cpu.name, "avatar": cpu.avatar, "image": cpu.image_url, "colors": play.colors_from(cards),
            "rank": rank, "rank_name": rows[rank]["name"], "next_rank_name": nxt["name"] if nxt else None,
            "progress": round(progress, 3), "record": {"won": rel.get("won", 0), "lost": rel.get("lost", 0)},
            "tastes": {"loved": named("loved"), "liked": named("liked"), "disliked": named("disliked")},
            "quests": quest_rows, "entries": entries}
