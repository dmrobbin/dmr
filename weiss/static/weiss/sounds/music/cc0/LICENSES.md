# Sampled music: sources and licences

Every sound in the CC0 songs (cc0_*.wav, their layers, and kit/) and in the shared drum kit (../kit/) comes from these
libraries. All are CC0-1.0 (public domain dedication: free to use, no attribution required). Each was downloaded from
its GitHub release under https://github.com/sfzinstruments/.

| Library | Version | Author | Used for |
|---|---|---|---|
| Big Rusty Drums | 1.100 | Karoryfer Samples | Kick |
| Frankensnare | 2.100 | Karoryfer Samples | Snare, brush, rimshot, claps |
| Swirly Drums | 1.104 | Karoryfer Samples | Hats, ride, crash, toms, cowbell |
| Gogodze Phu Vol II | 1.001 | Karoryfer Samples | Kick, snare, hats (earlier hip hop loop) |
| Black And Green Guitars | 1.000 | Karoryfer Samples | Distorted rhythm guitar, muted guitar, lead guitar |
| Emilyguitar | 1.001 | Karoryfer Samples | Clean guitar arpeggios |
| Growlybass | 1.002 | Karoryfer Samples | Electric bass |
| Fashionbass | 1.001 | Karoryfer Samples | Slap bass (funk) |
| D. Smolken double bass | 1.001 | D. Smolken | Upright bass (jazz) |
| Osiris Piano | 0.925 | Versilian Studios and Karoryfer Samples | Piano |
| Bear Sax | 1.004 | Karoryfer Samples | Baritone sax |
| Weresax | 1.003 | Karoryfer Samples | Alto sax |
| String Cyborgs | 1.001 | Karoryfer Samples | Strings |
| Karoryfer Bigcat cello | 1.001 | Karoryfer Samples and Bigcat Instruments | Cello |
| Caveman Cosmonaut | 1.001 | Karoryfer Samples | Violin |

How they're made (scripts in e2e/, run from the downloaded libraries in e2e/scratch, which aren't in git):
- e2e/export_kit.py: the shared one-shot drum kit (../kit/) that the synth songs play.
- e2e/music/instruments.py: the instrument banks. Some libraries name octaves differently; the offsets were measured
  with e2e/music/calibrate.py, so every note plays at its real pitch.
- e2e/music/catalog.py (with songs.py): the seven CC0 songs, four bars each, as nine layers: core, top, bass, chords,
  lead, extra, drive, climax and splash. cc0_N.wav is the full loop without the climax, the engine's fallback.
- e2e/render_stems.py: the per-song sound-effect kit (cc0/kit/).

Not used, because they need credit or share-alike terms: DRSKit (CC-BY-4.0), Muldjord Kit (CC-BY-4.0), Naked Drums
(CC-BY-4.0), Salamander Drumkit (CC-BY-SA-3.0) and Sam's Sonor (CC-BY-SA-4.0).
