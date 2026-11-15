"""What a card does for a deck, for the Role filters beside the Type ones:

- combo: its text names a climax (quoted, as card text names cards), or it has a climax combo (abilities.has_combo,
  which also catches older combos without the 【CXCOMBO】 mark).
- support: it gets value from the back row: Assist, anything for "characters in front of this card", Brainstorm,
  an 【ACT】 paid for by resting this card, or an ability that checks this card is in your back stage.
"""
import re

from weiss import abilities
from weiss.models import Card

ROLES = [  # (value, label, what it picks out), in the order the filters offer them
    ("combo", "Combo", "Cards that name a climax, including every climax combo"),
    ("support", "Support", "Cards that help from the back row: Assist, Brainstorm, 【REST】 abilities and the like"),
]
ROLE_VALUES = {value for value, _, _ in ROLES}
LONGEST_NAME = 120  # no card name runs longer than this, so wider quote pairs aren't tried

SUPPORT = re.compile(
    r"\bAssist\b"
    r"|in front of this card"
    r"|\bBrainstorm\b"
    r"|【ACT】[^\[]*\[[^\]]*【REST】 this card"  # its cost rests this card
    r"|this card is (?:in|on) (?:the [^,.]*? of )?your back stage",
)


def climax_names():
    """Every climax's name, straightened and case-folded as named_climaxes compares them."""
    names = Card.objects.filter(card_type="Climax").values_list("name", flat=True).distinct()
    return {abilities.plain_name(name).casefold() for name in names}


def quoted(text):
    """Every stretch of text between two straight quotes. A name can hold quotes of its own, as can a quoted ability
    with names inside, so every pair is tried rather than only neighbours."""
    marks = [i for i, c in enumerate(text) if c == '"']
    for n, start in enumerate(marks):
        for end in marks[n + 1:]:
            if end - start > LONGEST_NAME:
                break
            yield text[start + 1:end].strip()


def names_a_climax(lines, climaxes):
    return any(name.casefold() in climaxes for line in lines for name in quoted(line))


def roles_of(text, climaxes):
    """This card text's roles (values from ROLES), given every climax name (climax_names())."""
    if not text:
        return []
    lines = abilities.plain_name_lines(text)  # split once: it's the slow part, and a set page does every card
    roles = []
    if any("【CXCOMBO】" in line or abilities.OLD_COMBO.search(line) for line in lines) or names_a_climax(lines, climaxes):
        roles.append("combo")  # (the first half is abilities.has_combo, on the lines already split)
    if any(SUPPORT.search(line) for line in lines):
        roles.append("support")
    return roles


def climax_names_for(request):
    """climax_names(), looked up once per request however many cards a page marks."""
    if request is None:
        return climax_names()
    if not hasattr(request, "_climax_names"):
        request._climax_names = climax_names()
    return request._climax_names
