import secrets

from django.db import models
from django.urls import reverse


class Card(models.Model):
    """One Weiss Schwarz card as listed on en.ws-tcg.com."""

    serial_number = models.CharField(max_length=50, unique=True, help_text="e.g. 'NIK/S135-E001S'")
    name = models.CharField(max_length=200)
    expansion = models.CharField(max_length=200, help_text="Expansion (set) name")
    expansion_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True, help_text="The site's expansion number, e.g. 290"
    )
    traits = models.CharField(max_length=300, blank=True, help_text="Separated by '・' as on the site")
    card_type = models.CharField(max_length=50, blank=True)
    rarity = models.CharField(max_length=20, blank=True)
    side = models.CharField(max_length=10, blank=True, help_text="Weiss or Schwarz")
    color = models.CharField(max_length=20, blank=True)
    level = models.IntegerField(null=True, blank=True)
    cost = models.IntegerField(null=True, blank=True)
    power = models.IntegerField(null=True, blank=True)
    trigger = models.CharField(max_length=100, blank=True, help_text="Trigger icons, e.g. 'soul' or 'soul soul'")
    soul = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, help_text="Card text; icons appear as e.g. [comeback]")
    flavor_text = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Original image on en.ws-tcg.com")
    image_s3_key = models.CharField(max_length=500, blank=True, help_text="Copy of the image in the S3 bucket")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expansion_id", "serial_number"]

    def __str__(self):
        return f"{self.serial_number} {self.name}"

    @property
    def tcgplayer_price(self):
        """This card's TCGplayer price row, if any (uses prefetched `prices` when available)."""
        return next((p for p in self.prices.all() if p.source == CardPrice.Source.TCGPLAYER), None)


class CardPrice(models.Model):
    """A card's price from one source; refreshed in place by `manage.py fetch_prices`."""

    class Source(models.TextChoices):
        TCGPLAYER = "tcgplayer", "TCGplayer (via TCGCSV)"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="prices")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.TCGPLAYER)
    market_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Based on recent sales; the price we show"
    )
    low_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Lowest current listing"
    )
    mid_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    high_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    printing = models.CharField(max_length=50, blank=True, help_text="TCGplayer sub-type, e.g. 'Normal'")
    tcgplayer_product_id = models.PositiveIntegerField(null=True, blank=True)
    product_url = models.URLField(max_length=500, blank=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["card", "source"], name="one_price_per_card_per_source")]

    def __str__(self):
        return f"{self.card.serial_number}: {self.market_price or '—'} ({self.get_source_display()})"


class CardList(models.Model):
    """A user's named list of cards (a deck, a want list, ...), with any number of copies per card."""

    MAX_LISTS_PER_USER = 100
    MAX_CARDS = 100  # total copies across the whole list
    MAX_STARS = 10  # wins shown as separate stars

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="card_lists")
    name = models.CharField(max_length=100)
    # A deck gets deck-building reminders (50 cards, 8 climaxes, 4 copies, level spread); nothing is enforced.
    is_deck = models.BooleanField(default=True)
    # The card pictured for this list on the lists page; blank means its first card (see lists.attach_covers).
    cover_card = models.ForeignKey("Card", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    wins = models.PositiveIntegerField(default=0, help_text="Games this list has won against human players; shown as stars")
    cpu_wins = models.PositiveIntegerField(default=0, help_text="Games this list has won against CPUs; shown as robots")
    express = models.JSONField(default=dict, blank=True, help_text="How express building made this deck: series, anchors, required names")
    reserved_for_cpu = models.BooleanField(default=False, help_text="Made in the CPU creation tab; kept out of players' lists and deck choices")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return self.name

    def _icons(self, icon, count):
        """A count as icons, or an icon and the number once there are too many to count by eye."""
        return icon * count if count <= self.MAX_STARS else f"{icon} ×{count}"

    @property
    def win_stars(self):
        return self._icons("★", self.wins)

    @property
    def cpu_win_icons(self):
        return self._icons("🤖", self.cpu_wins)

    def card_count(self):
        return self.entries.aggregate(total=models.Sum("quantity"))["total"] or 0


class CardListEntry(models.Model):
    card_list = models.ForeignKey(CardList, on_delete=models.CASCADE, related_name="entries")
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="list_entries")
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["card_list", "card"], name="one_entry_per_card_per_list")]
        verbose_name_plural = "card list entries"

    def __str__(self):
        return f"{self.quantity}× {self.card}"


class Avatar(models.Model):
    """A picture cut from a card: a circle on its image, measured in widths of the image."""

    avatar_card = models.ForeignKey(Card, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    avatar_x = models.FloatField(default=.5)
    avatar_y = models.FloatField(default=.5)
    avatar_r = models.FloatField(default=.5)

    class Meta:
        abstract = True

    @property
    def avatar(self):
        """How to show it: the image, and where it goes in a square that clips it to a circle (percentages)."""
        if not self.avatar_card_id:
            return None
        across = 2 * self.avatar_r
        return {"image": reverse("weiss:card_image", args=[self.avatar_card_id]), "width": round(100 / across, 3),
                "left": round(-(self.avatar_x - self.avatar_r) / across * 100, 3), "top": round(-(self.avatar_y - self.avatar_r) / across * 100, 3)}


class PlayerProfile(Avatar):
    """What a player has chosen for their profile."""

    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="player_profile")

    def __str__(self):
        return str(self.user)


class CpuImage(models.Model):
    """An image in the pool every CPU's avatar is chosen from. Only staff and the find_card_images command add them."""

    key = models.CharField(max_length=500, unique=True, help_text="Where it is in the S3 bucket")
    name = models.CharField(max_length=200, blank=True, help_text="Who or what it shows")
    series = models.CharField(max_length=200, blank=True, help_text="The show it's from, when known")
    kind = models.CharField(max_length=20, blank=True, help_text="official or unofficial, for a found image")
    source_url = models.URLField(max_length=1000, blank=True, help_text="Where a found image came from")
    source_card = models.ForeignKey(Card, null=True, blank=True, on_delete=models.SET_NULL, related_name="+", help_text="The card it was found for")
    created_by = models.ForeignKey("auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["series", "name", "pk"]

    def __str__(self):
        return self.name or self.key


class CpuProfile(Avatar):
    """A CPU opponent: how it plays and with what. Players can challenge it once it's finalized."""

    # Its screens, and the field holding each one's image. One left empty shows the main image.
    SCREENS = {"main": "image", "intro": "intro_image", "win": "player_win_image", "lose": "player_lose_image"}
    SCREEN_LABELS = {"main": "Main", "intro": "Intro", "win": "When the player wins", "lose": "When the player loses"}

    name = models.CharField(max_length=100)
    model = models.CharField(max_length=20, default="standard", help_text="Which behaviour it plays by; see weiss.cpu")
    aggression = models.PositiveSmallIntegerField(default=1, help_text="1 is the standard behaviour")
    deck = models.ForeignKey(CardList, null=True, blank=True, on_delete=models.SET_NULL, related_name="cpu_profiles")
    finalized = models.BooleanField(default=False, help_text="Offered to players under VS CPU")
    image = models.ForeignKey(CpuImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="profiles")
    intro_image = models.ForeignKey(CpuImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="intro_profiles")
    player_win_image = models.ForeignKey(CpuImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="win_profiles")
    player_lose_image = models.ForeignKey(CpuImage, null=True, blank=True, on_delete=models.SET_NULL, related_name="lose_profiles")
    intro_text = models.TextField(blank=True, help_text="Shown on its screen before a match")
    player_win_text = models.TextField(blank=True, help_text="Shown on the victory screen, when the player beats it")
    player_lose_text = models.TextField(blank=True, help_text="Shown on the defeat screen, when the player loses to it")
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def image_url(self):
        """Stable until the image changes, so browsers can keep it; a new upload has a new key, so a new link."""
        return self.screen_url("main")

    def screen_image(self, screen):
        """The image for one of its screens: its own, or else the main one."""
        return getattr(self, self.SCREENS.get(screen, "image")) or self.image

    def screen_url(self, screen):
        image = self.screen_image(screen)
        if not image:
            return ""
        return reverse("weiss:cpu_image", args=[self.pk]) + f"?screen={screen}&v=" + image.key.rsplit("/", 1)[-1]


class ArcadeScenario(models.Model):
    """A list of CPUs to fight through in arcade mode."""

    name = models.CharField(max_length=100, unique=True)
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def ordered_entries(self):
        """Opener, fillers, anchor: the order they're fought in, though the fillers shuffle."""
        order = ArcadeEntry.Role.values
        return sorted(self.entries.all(), key=lambda entry: (order.index(entry.role), entry.cpu.name))


class ArcadeEntry(models.Model):
    class Role(models.TextChoices):
        OPENER = "opener", "Opener"
        FILLER = "filler", "Filler"
        ANCHOR = "anchor", "Anchor"

    scenario = models.ForeignKey(ArcadeScenario, on_delete=models.CASCADE, related_name="entries")
    cpu = models.ForeignKey(CpuProfile, on_delete=models.CASCADE, related_name="arcade_entries")
    role = models.CharField(max_length=10, choices=Role.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["scenario", "cpu"], name="one_entry_per_cpu_per_scenario")]

    def __str__(self):
        return f"{self.cpu} as {self.role} in {self.scenario}"


class ArcadeRun(models.Model):
    """One player's attempt at a scenario. It keeps the names, so it outlasts the scenario and deck."""

    class Status(models.TextChoices):
        ACTIVE = "active", "In progress"
        CLEARED = "cleared", "Cleared"
        ABANDONED = "abandoned", "Stopped"

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="arcade_runs")
    scenario = models.ForeignKey(ArcadeScenario, null=True, on_delete=models.SET_NULL, related_name="runs")
    scenario_name = models.CharField(max_length=100)
    deck_name = models.CharField(max_length=100, blank=True)
    order = models.JSONField(default=list, help_text="CpuProfile ids, in the order they're fought")
    position = models.PositiveSmallIntegerField(default=0, help_text="How many of them have been beaten")
    losses = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    started = models.DateTimeField(auto_now_add=True)
    finished = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started", "-pk"]

    def __str__(self):
        return f"{self.user}: {self.scenario_name} ({self.status})"

    @property
    def total(self):
        return len(self.order)


class ArcadeClear(models.Model):
    """A deck's marker: which scenario it has cleared, and how many times."""

    deck = models.ForeignKey("CardList", on_delete=models.CASCADE, related_name="arcade_clears")
    scenario = models.ForeignKey(ArcadeScenario, null=True, on_delete=models.SET_NULL, related_name="+")
    name = models.CharField(max_length=100)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["deck", "scenario"], name="one_marker_per_scenario_per_deck")]

    def __str__(self):
        return f"{self.deck}: {self.name} x{self.count}"


CPU_USERNAME = "cpu-player"


def cpu_user():
    """The account in a CPU's seat: game state is keyed by user, but nobody can log in as this one."""
    from django.contrib.auth.models import User
    user, created = User.objects.get_or_create(username=CPU_USERNAME, defaults={"is_active": False})
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


def new_room_token():
    return secrets.token_urlsafe(24)


class GameRoom(models.Model):
    """A two-player table. The host shares an invite link; whoever opens it first takes the other seat."""

    MAX_OPEN_ROOMS = 20  # per host

    class Status(models.TextChoices):
        SETUP = "setup", "Choosing decks"
        PLAYING = "playing", "Playing"

    host = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="rooms_hosted")
    guest = models.ForeignKey("auth.User", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="rooms_joined")
    invite_token = models.CharField(max_length=64, unique=True, default=new_room_token, editable=False)
    host_deck = models.ForeignKey(CardList, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    guest_deck = models.ForeignKey(CardList, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    # In a game against a CPU, the guest is cpu_user() and these say which CPU it is. The name stays if the profile goes.
    cpu_name = models.CharField(max_length=100, blank=True, help_text="The CPU in the guest seat, if it's a game against one")
    cpu_profile = models.ForeignKey(CpuProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    arcade_run = models.ForeignKey(ArcadeRun, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SETUP)
    state = models.JSONField(default=dict, blank=True, help_text="See weiss.game for the format")
    version = models.PositiveIntegerField(default=0, help_text="Goes up on every change, so browsers can poll cheaply")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return f"{self.host} vs {self.guest or '(open seat)'}"

    def seat_of(self, user):
        if user.pk == self.host_id:
            return "host"
        if user.pk == self.guest_id:
            return "guest"
        return None

    def opponent_of(self, user):
        return self.guest if user.pk == self.host_id else self.host

    @property
    def vs_cpu(self):
        return bool(self.cpu_name)

    @property
    def guest_name(self):
        return self.cpu_name or (self.guest.username if self.guest else "")


class GameRecord(models.Model):
    """One finished game, for the players' profiles. It keeps the names, so it outlasts the room and decks."""

    SEATS = [("host", "Host"), ("guest", "Guest")]

    host = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    guest = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    host_name = models.CharField(max_length=150)
    guest_name = models.CharField(max_length=150)
    host_deck_name = models.CharField(max_length=100, blank=True)
    guest_deck_name = models.CharField(max_length=100, blank=True)
    cpu = models.BooleanField(default=False)
    cpu_profile = models.ForeignKey(CpuProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    winner = models.CharField(max_length=5, choices=SEATS)
    reason = models.CharField(max_length=20, blank=True)
    game_number = models.PositiveSmallIntegerField(default=1)
    turns = models.PositiveSmallIntegerField(default=0)
    finished = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-finished", "-pk"]

    def __str__(self):
        return f"{self.host_name} vs {self.guest_name}: {self.winner} won"

    def view_for(self, user):
        """Set what the profile page shows, from this user's side."""
        hosting = user.pk == self.host_id
        self.won = self.winner == ("host" if hosting else "guest")
        self.opponent_name = self.guest_name if hosting else self.host_name
        self.my_deck_name = self.host_deck_name if hosting else self.guest_deck_name
