"""TCGplayer price data from tcgcsv.com, a free daily mirror of TCGplayer's official API.

Data is organised as category (Weiss Schwarz is 20) -> group (a set) -> products and prices.
TCGCSV refreshes once a day, so there's no point fetching more often than that.
"""
import json
import re
from collections import Counter
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://tcgcsv.com/tcgplayer"
WEISS_CATEGORY_ID = 20
USER_AGENT = "darylsite-weiss/1.0 (personal card price tracker)"


class TcgcsvError(Exception):
    pass


@lru_cache(maxsize=None)  # one download per path per run, e.g. when several of our sets share a group
def get(path):
    request = Request(f"{BASE_URL}/{path}", headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise TcgcsvError(f"HTTP {exc.code} for {path}") from exc
    except URLError as exc:
        raise TcgcsvError(f"{exc.reason} for {path}") from exc
    if not data.get("success", True):
        raise TcgcsvError(f"{path}: {data.get('errors')}")
    return data["results"]


def groups():
    return get(f"{WEISS_CATEGORY_ID}/groups")


def normalize(name):
    """Compare set names loosely: 【】 vs [], 'Booster Pack' / '[TD] Trial Deck' prefixes, case, spacing."""
    name = name.replace("【", "[").replace("】", "]").lower()
    name = re.sub(r"^(booster pack|\[td\] trial deck|trial deck|\[td\])\s*", "", name.strip())
    return " ".join(name.split())


def series_code(serial_number):
    """'OSK/S107-E086' -> 'OSK'."""
    return serial_number.split("/", 1)[0].upper()


def find_groups(expansion_name, serial_numbers):
    """TCGplayer groups holding these cards, as [(group, cards it has)], most cards first.

    Names don't line up reliably (the official '[TD] 【OSHI NO KO】' trial deck is inside TCGplayer's
    '[OSHI NO KO]' group), so candidates are groups with a matching name or the same series code
    in their abbreviation, ranked by how many of our card numbers they contain. A set can span
    several groups, e.g. a promo packed with Vol.2 but listed under Vol.1.
    """
    serials = set(serial_numbers)
    code = Counter(series_code(s) for s in serials).most_common(1)[0][0] if serials else ""
    wanted = normalize(expansion_name)
    candidates = [
        g for g in groups()
        if normalize(g["name"]) == wanted or (g.get("abbreviation") or "").split("/", 1)[0].upper() == code
    ]
    matches = [(group, len(serials & set(card_prices(group["groupId"])))) for group in candidates]
    return sorted([m for m in matches if m[1]], key=lambda m: m[1], reverse=True)


def card_prices(group_id):
    """{serial number: price info} for every card in a group that has a card number."""
    prices = {}
    for price in get(f"{WEISS_CATEGORY_ID}/{group_id}/prices"):
        # A product can have several printings (e.g. Normal, Foil); prefer Normal.
        if price["productId"] not in prices or price["subTypeName"] == "Normal":
            prices[price["productId"]] = price

    cards = {}
    for product in get(f"{WEISS_CATEGORY_ID}/{group_id}/products"):
        number = next((e["value"] for e in product.get("extendedData", []) if e["name"] == "Number"), None)
        if not number:
            continue  # booster boxes, supply products, etc.
        price = prices.get(product["productId"], {})
        # Some sets append the rarity, e.g. 'OSK/S107-E001 RR'; the serial is the first word.
        cards[number.split()[0]] = {
            "tcgplayer_product_id": product["productId"],
            "product_url": product.get("url") or "",
            "market_price": price.get("marketPrice"),
            "low_price": price.get("lowPrice"),
            "mid_price": price.get("midPrice"),
            "high_price": price.get("highPrice"),
            "printing": price.get("subTypeName") or "",
        }
    return cards
