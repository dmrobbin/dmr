"""The music tracks the pages offer: the built-in styles (audio.js), with the names and deletions the staff music page
keeps (MusicTrack). The duel and the town both use the visible ones, in the music page's order."""
from .models import MusicTrack

MUSIC_STYLES = (("lofi", "Lo-fi"), ("rock_1", "Rock 1"), ("rock_2", "Rock 2"), ("rock_3", "Rock 3"), ("rock_4", "Rock 4"),
                 ("hip_hop", "Hip hop"), ("jazz", "Jazz"), ("funk", "Funk"), ("synthwave", "Synthwave"),
                 ("emo", "Emo"), ("metal", "Metal"),
                 ("cc0_1", "CC0 drums 1"), ("cc0_2", "CC0 drums 2"), ("cc0_3", "CC0 drums 3"),
                 ("cc0_4", "CC0 jazz"), ("cc0_5", "CC0 hip hop"),
                 ("cc0_6", "CC0 funk"), ("cc0_7", "CC0 emo"), ("cc0_8", "CC0 metal"))


def seed_music_tracks():
    """A row for each built-in style that doesn't have one yet; existing rows (renamed or deleted) are left as they are."""
    for position, (key, name) in enumerate(MUSIC_STYLES):
        MusicTrack.objects.get_or_create(key=key, defaults={"name": name, "position": position})


def visible_tracks():
    """The tracks not deleted, in the music page's order: [{key, name}], for a page's song choice."""
    seed_music_tracks()
    return [{"key": track.key, "name": track.name} for track in MusicTrack.objects.filter(hidden=False)]
