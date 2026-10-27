"""Read card details from the official English card list at en.ws-tcg.com."""
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

BASE_URL = "https://en.ws-tcg.com"
USER_AGENT = "Mozilla/5.0 (compatible; darylsite-weiss/1.0)"
SIDES = {"w": "Weiss", "s": "Schwarz"}


class ScraperError(Exception):
    pass


def fetch(path, params=None):
    """GET a page (or image) from the card site and return (bytes, content type)."""
    url = urljoin(BASE_URL, path) + (f"?{urlencode(params)}" if params else "")
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=30) as response:
            return response.read(), response.headers.get_content_type()
    except HTTPError as exc:
        raise ScraperError(f"HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise ScraperError(f"{exc.reason} for {url}") from exc


def fetch_html(path, params=None):
    return BeautifulSoup(fetch(path, params)[0], "html.parser")


def expansion_serials(expansion_id, delay=1.0):
    """Every serial number in an expansion, in the site's order.

    The search results page loads 15 cards at a time from `cardsearch_ex`; keep asking for
    the next page until one comes back empty.
    """
    serials = []
    page = 1
    while True:
        soup = fetch_html("/cardlist/cardsearch_ex", {"expansion": expansion_id, "view": "text", "page": page})
        found = [p.get_text(strip=True) for p in soup.select("p.number")]
        new = [s for s in found if s not in serials]
        if not new:
            return serials
        serials += new
        page += 1
        time.sleep(delay)


def icon_name(img):
    """Icons are images like .../partimages/soul.gif; the file name is the icon, e.g. 'soul'."""
    return img["src"].rsplit("/", 1)[-1].rsplit(".", 1)[0]


def icon_names(tag):
    return [icon_name(img) for img in tag.find_all("img")] if tag else []


def number(tag):
    text = tag.get_text(strip=True) if tag else ""
    return int(text) if re.fullmatch(r"-?\d+", text) else None


def card_text(tag):
    """Card text with <br> as newlines and icons written as [name]."""
    if not tag:
        return ""
    tag = BeautifulSoup(str(tag), "html.parser")  # work on a copy
    for img in tag.find_all("img"):
        img.replace_with(f"[{icon_name(img)}]")
    for br in tag.find_all("br"):
        br.replace_with("\n")
    text = tag.get_text().strip()
    return "" if text == "-" else text


def fetch_card(serial_number):
    """Details for one card, or None if the site has no card with that serial number."""
    return parse_card(fetch_html("/cardlist/", {"cardno": serial_number}))


def parse_card(soup):
    details = soup.select_one(".p-cards__detail-textarea")
    if not details or not details.select_one("p.number"):
        return None
    fields = {dl.dt.get_text(strip=True): dl.dd for dl in details.find_all("dl") if dl.dt and dl.dd}

    def text(label):
        return fields[label].get_text(strip=True) if label in fields else ""

    side = icon_names(fields.get("Side"))
    color = icon_names(fields.get("Color"))
    image = soup.select_one(".p-cards__detail-wrapper .image img")
    expansion_link = soup.select_one('a[href*="searchresults/?expansion="]')
    soul_icons = icon_names(fields.get("Soul"))
    return {
        "serial_number": details.select_one("p.number").get_text(strip=True),
        "name": details.select_one("p.ttl").get_text(strip=True),
        "expansion": text("Expansion"),
        "expansion_id": int(re.search(r"expansion=(\d+)", expansion_link["href"]).group(1)) if expansion_link else None,
        "traits": text("Traits"),
        "card_type": text("Card Type"),
        "rarity": text("Rarity"),
        "side": SIDES.get(side[0], side[0]) if side else "",
        "color": color[0].capitalize() if color else "",
        "level": number(fields.get("Level")),
        "cost": number(fields.get("Cost")),
        "power": number(fields.get("Power")),
        "trigger": " ".join(icon_names(fields.get("Trigger"))),
        "soul": len(soul_icons) if soul_icons else number(fields.get("Soul")),
        "description": card_text(details.select_one(".p-cards__detail p")),
        "flavor_text": card_text(details.select_one(".p-cards__detail-serif p")),
        "image_url": urljoin(BASE_URL, image["src"]) if image else "",
    }
