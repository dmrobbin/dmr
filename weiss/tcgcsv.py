"""TCGplayer price data from tcgcsv.com, a free daily mirror of TCGplayer's official API.

Data is organised as category (Weiss Schwarz is 20) -> group (a set) -> products and prices.
TCGCSV refreshes once a day, so there's no point fetching more often than that.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://tcgcsv.com/tcgplayer"
WEISS_CATEGORY_ID = 20
USER_AGENT = "darylsite-weiss/1.0 (personal card price tracker)"


class TcgcsvError(Exception):
    pass


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


def find_group(expansion_name):
    """The TCGplayer group whose name matches our expansion name (case and spacing ignored)."""
    wanted = " ".join(expansion_name.split()).lower()
    return next((g for g in groups() if " ".join(g["name"].split()).lower() == wanted), None)


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
        cards[number.strip()] = {
            "tcgplayer_product_id": product["productId"],
            "product_url": product.get("url") or "",
            "market_price": price.get("marketPrice"),
            "low_price": price.get("lowPrice"),
            "mid_price": price.get("midPrice"),
            "high_price": price.get("highPrice"),
            "printing": price.get("subTypeName") or "",
        }
    return cards
