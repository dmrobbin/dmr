from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import roles
from .models import Card, CardList, CardListEntry

CLIMAXES = {"old tales", "unbreakable sphere", "sun, shining"}


class RolesOfTests(SimpleTestCase):
    def roles(self, text):
        return roles.roles_of(text, CLIMAXES)

    def test_a_climax_combo_is_a_combo(self):
        self.assertEqual(self.roles('【AUTO】 【CXCOMBO】 When "OLD TALES" is placed on your climax area, draw 1 card.'), ["combo"])

    def test_an_old_unmarked_combo_is_a_combo(self):
        self.assertEqual(self.roles('【AUTO】 When this card attacks, if "Some Climax" is in your climax area, draw 1 card.'), ["combo"])

    def test_naming_a_climax_anywhere_is_a_combo(self):
        # Curly quotes and any case, as card text may write them.
        self.assertEqual(self.roles("【AUTO】 When this card is placed on stage, search your deck for up to 1 “Old Tales”, put it into your hand."), ["combo"])
        # Inside a quoted ability, beside another name.
        self.assertEqual(self.roles('【AUTO】 This card gets "【AUTO】 Search your deck for up to 1 "UNBREAKABLE SPHERE" or "Sun, Shining", and put it into your hand."'), ["combo"])

    def test_naming_a_character_is_not_a_combo(self):
        self.assertEqual(self.roles('【CONT】 If you have another "Old Tales Reader", this card gets +1000 power.'), [])

    def test_back_row_abilities_are_support(self):
        for text in (
            "【CONT】 Assist All of your characters in front of this card get +500 power.",
            "【CONT】 All of your characters in front of this card get +1 soul.",
            "【ACT】 Brainstorm [(1) 【REST】 2 of your characters] Flip over 4 cards from the top of your deck.",
            "【ACT】 [【REST】 this card] Choose 1 of your characters, and that character gets +500 power until end of turn.",
            '【ACT】 [(1) Reveal 1 "Some Card" in your hand & 【REST】 this card] Draw 1 card.',
            "【AUTO】 When your other character becomes 【REVERSE】, if this card is in your back stage, draw 1 card.",
            "【CONT】 If this card is in the middle position of your back stage, all of your characters get +500 power.",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.roles(text), ["support"])

    def test_front_row_abilities_are_not_support(self):
        for text in (
            "【AUTO】 When this card attacks, this card gets +1000 power until end of turn.",
            "【AUTO】 When this card becomes 【REVERSE】 in battle, you may pay the cost. If you do, 【REST】 this card.",
            "【CONT】 This card gets +1000 power for each other character in your back stage.",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.roles(text), [])

    def test_a_card_can_be_both(self):
        text = '【ACT】 【CXCOMBO】 Brainstorm [(1) 【REST】 this card] Flip over 5 cards. For each climax revealed, search for "OLD TALES".'
        self.assertEqual(self.roles(text), ["combo", "support"])


class RoleFilterPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("daryl", password="x", is_staff=True)
        self.client.force_login(self.user)
        base = {"expansion": "NIKKE Vol.2", "expansion_id": 290, "image_url": "https://en.ws-tcg.com/x.png"}
        self.combo = Card.objects.create(serial_number="NIK/S135-E001", name="Elegg", card_type="Character", level=1,
                                         description='【AUTO】 When this card attacks, if "FOOTSTEP" is in your climax area, draw 1 card.', **base)
        self.support = Card.objects.create(serial_number="NIK/S135-E002", name="Anis", card_type="Character", level=0,
                                           description="【CONT】 Assist All of your characters in front of this card get +500 power.", **base)
        self.event = Card.objects.create(serial_number="NIK/S135-E003", name="Plan", card_type="Event", level=0,
                                         description='Search your deck for up to 1 "FOOTSTEP", and put it into your hand.', **base)
        self.climax = Card.objects.create(serial_number="NIK/S135-E120", name="FOOTSTEP", card_type="Climax", **base)

    def names(self, **params):
        response = self.client.get(reverse("weiss:set", args=[290]), params)
        return sorted(card.name for card in response.context["cards"])

    def test_set_page_filters_by_role(self):
        self.assertEqual(self.names(role="combo"), ["Elegg", "Plan"])
        self.assertEqual(self.names(role="support"), ["Anis"])
        self.assertEqual(self.names(role=["combo", "support"]), ["Anis", "Elegg", "Plan"])  # either
        self.assertEqual(self.names(role="combo", type="Character"), ["Elegg"])  # and the type too
        self.assertEqual(self.names(role="bogus"), ["Anis", "Elegg", "FOOTSTEP", "Plan"])
        response = self.client.get(reverse("weiss:set", args=[290]), {"role": "combo"})
        self.assertContains(response, 'value="combo" checked')
        self.assertTrue(response.context["filtered"])

    def test_set_page_offers_only_roles_its_cards_have(self):
        Card.objects.filter(pk=self.support.pk).update(description="")
        response = self.client.get(reverse("weiss:set", args=[290]))
        self.assertEqual([value for value, _, _ in response.context["roles"]], ["combo"])
        Card.objects.update(description="")
        self.assertNotContains(self.client.get(reverse("weiss:set", args=[290])), 'name="role"')

    def test_list_cards_are_marked_with_their_roles(self):
        deck = CardList.objects.create(user=self.user, name="Deck")
        for card in (self.combo, self.support, self.climax):
            CardListEntry.objects.create(card_list=deck, card=card, quantity=1)
        page = self.client.get(reverse("weiss:list", args=[deck.pk]))
        self.assertContains(page, 'data-filter-field="roles"')
        self.assertContains(page, 'data-type="character" data-roles="combo"')
        self.assertContains(page, 'data-type="character" data-roles="support"')
        self.assertContains(page, 'data-type="climax" data-roles=""')
