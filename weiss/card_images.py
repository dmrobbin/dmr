"""Finding images from outside the official card site: another source for a card whose picture is
missing, and art of the characters on cx combo cards. Used by the find_card_images command."""
import json
import re
import time
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import abilities, tcgcsv

USER_AGENT = "darylsite-weiss/1.0 (card image lookup)"
ANILIST_URL = "https://graphql.anilist.co"
DANBOORU_URL = "https://danbooru.donmai.us"
# Only ever images rated general. These sets are full of characters who are children, and this search
# runs unattended with nobody looking at what comes back, so this isn't something to loosen.
BOORU_RATING = "g"
MIN_ART_WIDTH = 300
ART_TRIES = 3  # results to try downloading before giving up on a search
ART_PAGES = 3  # pages of results to look through: newest first, and many are of other things
MIN_SHOW_NAME = 4  # shorter titles or tags would match inside too many others
ANILIST_DELAY = 2.2  # its limit is 30 requests a minute
TCGPLAYER_IMAGE = "https://tcgplayer-cdn.tcgplayer.com/product/{}_in_1000x1000.jpg"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MIN_NAME_PART = 3  # shorter parts of a name would match inside too many other words
CHARACTER_QUERY = """query($title: String, $page: Int) {
  Media(search: $title) {
    title { romaji english native }
    characters(page: $page, perPage: 50, sort: ROLE) {
      pageInfo { hasNextPage }
      nodes { name { full alternative } image { large } }
    }
  }
}"""


class ImageSourceError(Exception):
    pass


class NotFound(ImageSourceError):
    pass


def get(url, data=None, headers=None):
    """(bytes, content type) from a URL, waiting and trying once more if it says to slow down."""
    request = Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    for attempt in (1, 2):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read(), response.headers.get_content_type()
        except HTTPError as exc:
            if exc.code == 429 and attempt == 1:
                time.sleep(min(int(exc.headers.get("Retry-After") or 60), 120))
                continue
            raise (NotFound if exc.code == 404 else ImageSourceError)(f"HTTP {exc.code} for {url}") from exc
        except (OSError, HTTPException, ValueError) as exc:
            raise ImageSourceError(f"{exc} for {url}") from exc
    raise ImageSourceError(f"Gave up on {url}")


def image_type(head):
    """(extension, content type) from a file's first bytes, whatever it's called. SVG isn't on the list: it can hold scripts."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg", "image/jpeg"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif", "image/gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp", "image/webp"
    return None


def download_image(url):
    """(bytes, extension, content type) if this URL really gives an image of a size to keep, else None."""
    try:
        data, _ = get(url)
    except ImageSourceError:
        return None
    kind = image_type(data[:12])
    return (data, *kind) if kind and len(data) <= MAX_IMAGE_BYTES else None


# --- A card's own picture --------------------------------------------------------------------------------

def tcgplayer_image_url(card, product_ids):
    """The TCGplayer picture of this card, if we know its product. `product_ids` is {serial: product id} for its set."""
    price = card.tcgplayer_price
    product = (price.tcgplayer_product_id if price else None) or product_ids.get(card.serial_number)
    return TCGPLAYER_IMAGE.format(product) if product else None


def product_ids_for(expansion, serials):
    """{serial: TCGplayer product id} for a set's cards, as far as tcgcsv.com lists them."""
    found = {}
    try:
        for group, _ in tcgcsv.find_groups(expansion, serials):
            found |= {serial: info["tcgplayer_product_id"] for serial, info in tcgcsv.card_prices(group["groupId"]).items()}
    except tcgcsv.TcgcsvError:
        return found
    return found


# --- Which characters a climax is about ----------------------------------------------------------------

def series_title(expansion):
    """The show a set is from: 'Attack on Titan Vol.2' -> 'Attack on Titan',
    '[EX] Premium Booster Persona 3 Reload™' -> 'Persona 3 Reload'."""
    title = re.sub(r"[™®©]", "", expansion or "")
    title = re.sub(r"^\s*\[[^\]]*\]\s*", "", title)  # "[TD]", "[EX]"
    title = re.sub(r"^\s*(?:Premium Booster|Extra Booster|Booster Pack|Trial Deck\+?|Meta Trial Deck)\s*[-:–]?\s*", "", title, flags=re.I)
    title = re.sub(r"\s*(?:[-:–]\s*)?(?:Vol\.?\s*\d+|Part\s*\d+|ver\.\s*\w+|Trial Deck\+?.*|Booster Pack.*|Extra Booster.*|Premium Booster.*)\s*$", "", title, flags=re.I)
    return title.strip(" []【】") or (expansion or "").strip()


def anilist_show(title):
    """({"name", "names", "image"} for each character, the show's other titles) for what AniList finds
    under this title, or under just the part after a colon ("GODDESS OF VICTORY: NIKKE")."""
    tail = title.rsplit(":", 1)[-1].strip()
    for candidate in dict.fromkeys((title, tail)):
        characters, titles = characters_of(candidate)
        if characters:
            return characters, titles
        time.sleep(ANILIST_DELAY)
    return [], []


def characters_of(title):
    characters, titles, page = [], [], 1
    while True:
        body = json.dumps({"query": CHARACTER_QUERY, "variables": {"title": title, "page": page}}).encode()
        try:
            data, _ = get(ANILIST_URL, data=body, headers={"Content-Type": "application/json", "Accept": "application/json"})
        except NotFound:  # how it answers a search that finds nothing
            return characters, titles
        media = (json.loads(data).get("data") or {}).get("Media")
        if not media:
            return characters, titles
        titles = [t for t in media["title"].values() if t]
        found = media["characters"]
        for node in found["nodes"]:
            full = node["name"]["full"]
            if full:
                characters.append({"name": full, "names": [full, *(node["name"].get("alternative") or [])], "image": (node.get("image") or {}).get("large")})
        if not found["pageInfo"]["hasNextPage"] or page >= 4:
            return characters, titles
        page += 1
        time.sleep(ANILIST_DELAY)


def name_parts(character):
    """Whole names first, then the separate words of the main name long enough to mean something."""
    parts = [name for name in character["names"] if name]
    parts += [word for word in re.split(r"[\s\-]+", character["name"]) if len(word) >= MIN_NAME_PART]
    return parts


def characters_named(text, characters):
    """The characters this text names, in the order it names them. A character's whole name counts
    before part of one, and a word goes to the first character it could be, who the cast lists by
    importance: "Eren Yeager" isn't also someone else called Yeager, nor "Mikasa" Mikasa's father."""
    found = {}
    taken = []
    for whole in (True, False):
        for character in characters:
            parts = [n for n in character["names"] if n] if whole else name_parts(character)
            for part in parts:
                match = re.search(rf"(?<!\w){re.escape(part)}(?!\w)", text, re.I)
                if match and character["name"] not in found and not any(a <= match.start() < b for a, b in taken):
                    found[character["name"]] = (match.start(), character)
                    taken.append(match.span())
                    break
    return [character for _, character in sorted(found.values(), key=lambda item: item[0])]


def names_in_card(name):
    """Who a card's name is about, when the show's cast isn't known: '"Cleanup" Levi', 'Levi: Cleanup',
    'Cleaning Up, Levi', 'Ann as PANTHER' and 'Simon & Nia' all come down to the names."""
    name = re.sub(r'^\s*[“"][^”"]*[”"]\s*', "", name or "")
    name = name.rsplit(",", 1)[-1]
    name = re.split(r":| as | in ", name, maxsplit=1)[0]
    return [part.strip() for part in re.split(r"&| and ", name) if part.strip()]


def card_characters(card, cast):
    """The characters on a card, at most 2, from the show's cast if it names any."""
    names = names_in_card(card.name)
    named = characters_named(card.name, cast)
    if cast and any(re.match(r"protagonist\b", n, re.I) for n in names):
        # Not a name at all: the show's lead, who its cast lists first.
        named = [cast[0], *(c for c in named if c is not cast[0])]
    if named:
        return named[:2]
    return [{"name": n, "names": [n], "image": None} for n in names[:2]]


# --- Art of a character --------------------------------------------------------------------------------

def fandom_slugs(title):
    """Addresses the show's wiki might have: "Persona 3 Reload" -> persona3reload, persona3, persona."""
    words = [word for word in re.split(r"[^a-z0-9]+", title.lower()) if word]
    return [slug for slug in ("".join(words[:n]) for n in range(len(words), 0, -1)) if len(slug) >= MIN_SHOW_NAME]


def fandom_image_url(title, character):
    """The main picture on the character's page, on the show's Fandom wiki, if it has one at the usual address."""
    query = urlencode({"action": "query", "generator": "search", "gsrsearch": character, "gsrlimit": 1, "prop": "pageimages", "piprop": "original", "format": "json"})
    words = {word.lower() for word in re.split(r"[\s\-]+", character) if len(word) >= MIN_NAME_PART}
    for slug in fandom_slugs(title):
        try:
            data, _ = get(f"https://{slug}.fandom.com/api.php?{query}")
            pages = (json.loads(data).get("query") or {}).get("pages") or {}
        except (ImageSourceError, ValueError):
            continue  # no wiki at that address
        for page in pages.values():
            if words & {word.lower() for word in re.split(r"[\s\-()]+", page.get("title", ""))} and page.get("original"):
                return page["original"]["source"]
    return None


def compact(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def from_the_show(post, shows):
    """Whether a post's copyright tags say it's from this show, under any of its titles."""
    for tag in post.get("tag_string_copyright", "").split():
        tag = compact(tag)
        if len(tag) >= MIN_SHOW_NAME and any(len(show) >= MIN_SHOW_NAME and (tag in show or show in tag) for show in shows):
            return True
    return False


def booru_posts(tags, page=1):
    """Danbooru posts for these tags. Two tags are all it allows a script, and its rating isn't one of them."""
    query = urlencode({"tags": f"{tags} rating:{BOORU_RATING}", "limit": 100, "page": page})
    data, _ = get(f"{DANBOORU_URL}/posts.json?{query}", headers={"Accept": "application/json"})
    posts = json.loads(data)
    return [post for post in posts if isinstance(post, dict) and post.get("rating") == BOORU_RATING and post.get("file_url")]


def character_tag(name, shows):
    """Danbooru's tag for this character in this show, or None. Its tags order names their own way."""
    words = [word for word in re.split(r"[^a-z0-9]+", name.lower()) if len(word) >= MIN_NAME_PART]
    for wanted in (words, words[-1:]):
        if not wanted:
            continue
        longest = max(wanted, key=len)
        for search in dict.fromkeys((longest, long_vowels(longest))):  # the same name can be spelled Kirijo or Kirijou
            query = urlencode({"search[name_matches]": f"*{search}*", "search[category]": 4, "search[order]": "count", "limit": 20})
            data, _ = get(f"{DANBOORU_URL}/tags.json?{query}", headers={"Accept": "application/json"})
            tags = [tag["name"] for tag in json.loads(data) if names_match(wanted, tag["name"])]
            for tag in tags[:3]:
                time.sleep(1)
                if any(from_the_show(post, shows) for post in booru_posts(f"{tag} solo")):
                    return tag
    return None


def long_vowels(word):
    return word.replace("ou", "o").replace("oo", "o").replace("uu", "u")


def names_match(wanted, tag):
    """Whether a tag has each word of this name, however its long vowels are spelled."""
    words = [long_vowels(word) for word in re.split(r"[^a-z0-9]+", tag)]
    return all(long_vowels(want) in words for want in wanted)


def fits_art(post, tag, shows, official):
    """A picture of only this character, from this show, of the kind wanted."""
    every = post["tag_string"].split()
    # A costume has its own tag beside the character's, like "rapi_(red_hood)_(nikke)".
    base = tag.split("_(")[0]
    characters = post.get("tag_string_character", "").split()
    return (post.get("rating") == BOORU_RATING and "solo" in every and tag in characters and all(c.split("_(")[0] == base for c in characters)
            and ("official_art" in every) == official and from_the_show(post, shows)
            and post.get("file_ext") in ("png", "webp", "jpg") and (post.get("image_width") or 0) >= MIN_ART_WIDTH
            and (post.get("file_size") or 0) <= MAX_IMAGE_BYTES and not post.get("is_banned") and not post.get("is_deleted"))


def booru_art(tag, shows, official):
    """(image data, extension, content type, where it's from): a transparent background if there's one to be had."""
    for search in (f"{tag} transparent_background", f"{tag} official_art" if official else f"{tag} solo"):
        for page in range(1, ART_PAGES + 1):
            time.sleep(1)
            results = booru_posts(search, page)
            posts = [post for post in results if fits_art(post, tag, shows, official)]
            posts.sort(key=lambda post: ("transparent_background" not in post["tag_string"].split(), -(post.get("score") or 0)))
            for post in posts[:ART_TRIES]:
                found = download_image(post["file_url"])
                if found:
                    return (*found, f"{DANBOORU_URL}/posts/{post['id']}")
            if len(results) < 100:
                break
    return None


def character_art(title, other_titles, character):
    """{"official": found, "unofficial": found} for one character, each (image data, extension, content
    type, where it's from) or None. Official art can also come from the show's wiki or AniList."""
    shows = {compact(t) for t in (title, title.rsplit(":", 1)[-1], *other_titles) if compact(t)}
    art = {"official": None, "unofficial": None}
    try:
        tag = character_tag(character["name"], shows)
    except (ImageSourceError, ValueError):
        tag = None
    for kind in art if tag else ():  # one search failing shouldn't lose the other
        try:
            art[kind] = booru_art(tag, shows, kind == "official")
        except (ImageSourceError, ValueError):
            pass
    if not art["official"]:
        for url in (fandom_image_url(title, character["name"]), character.get("image")):
            found = download_image(url) if url else None
            if found:
                art["official"] = (*found, url)
                break
    return art
