# Poképad — Progress log

A running build log (newest on top). Decisions, milestones, and what's next.

## 2026-07-22

- **Real GBA `.sav` validated the flat-container path.** Rod dropped a real
  Emerald save → `save/gen3.py` parsed it clean: **trainer NICK** (TID 17925,
  135h30m playtime) + party (SALAMENCE Lv50 Quiet/Intimidate, MAGCARGO,
  Lv100 SMEARGLE), all IVs/EVs/nature/ability/moves. **Both parser paths are now
  proven on real saves** (`.gci` Box collection + `.sav` main-game trainer+party).
  Then the money shot: **NICK's real Emerald party vs Pierre's real Box team**
  battled autonomously by real mechanics (Tyranitar "Altruisa" won). Guarded
  real-`.sav` check added to `tests/test_save.py`. Personal saves gitignored
  (`*.sav`, `*.gci`).
- **Real save parsed — Pokémon Box RS `.gci`.** Rod dropped a real
  `01-GPXP-...box.gci` (GameCube, Pokémon Box: Ruby & Sapphire). `save/box_rs.py`
  reads it → **669 Pokémon / 382 species / 2 shinies**, all custom-nicknamed
  (Golded ✨, Lilorange ✨, Firesaur, Vento, SirCanon…). **This validated the
  whole Gen-III decoder against a genuine game dump** (crypto, PID%24 ordering,
  IV/nature/shiny derivations — checksum-verified across hundreds of real mon).
  Demo: **Pierre's real team battled autonomously by real mechanics.** Test
  `tests/test_box_rs.py` **+9** (synthetic `.gci` fixture, CI-safe, + a guarded
  real-save check). Personal saves are **gitignored** (never committed). Total
  **112/112** across 7 suites. Unlocks: "pick your team from the whole box", a
  living-Pokédex idle on the block (see IDEAS).
- **Full-team 6v6 battles + switching.** `Battle` is now team-capable
  (`left`/`right` = a Pokémon *or* a list; the active mon is a property). On a
  faint the side **sends in its best matchup** (forced switch, scored by
  `my_offense − their_offense`); a wiped side loses. Entry abilities
  (Intimidate) fire on every send-in. 1v1 is just team-of-1 → fully backward
  compatible (all prior tests unchanged). `save/bridge.team_from_savetruth`
  turns a whole parsed party into a team, so **your six saved mon can fight**.
  CLI now takes comma-separated teams: `python3 -m sim "charizard,alakazam"
  "gyarados,snorlax"`. Tests `tests/test_team.py` **+7**; total **103/103**
  across 6 suites. NEXT for battle-feel: *voluntary* strategic switching (only
  forced switches today — see IDEAS).

## 2026-07-21

- **Abilities (as hooks).** `sim/abilities.py` — a curated Gen-III set wired into
  the engine: type immunities (**Levitate** nullifies Ground, **Water/Volt
  Absorb** heal, **Flash Fire** immunity + fire boost, **Wonder Guard** only
  super-effective lands), damage mods (**Thick Fat**, **Huge Power**, **Guts**,
  **Blaze/Torrent/Overgrow/Swarm**, **Marvel Scale**), **Intimidate** on entry,
  status/stat-drop immunities (Limber/Immunity/Insomnia/Water Veil/Own Tempo/
  Clear Body…), and on-contact statusing (Static/Flame Body/Poison Point). The
  engine is now correct enough that Guts properly *ignores* burn (caught a naive
  test). Tests `tests/test_abilities.py` **+16**; total **96/96** across 5 suites.
  Deferred: weather-dependent abilities (Chlorophyll/Swift Swim) + the long tail
  (data-driven expansion — dataset already has every ability + effect text).
- **Phase 3 — Gen-III save parser → SaveTruth (READ-ONLY).** `save/gen3.py`
  parses RSE/FRLG saves: 14-section slots, active-slot selection, trainer +
  party; each Pokémon decrypted (key = PID^OTID), substructures ordered by
  PID%24, and nature/shininess/gender/ability/IVs/EVs derived. Dataset gained
  `internal_to_national` (species: Treecko=277) and `move_index_to_name`
  (Ember=52) since saves store internal indices. `save/bridge.py` turns a party
  entry into an engine Pokémon with its **real** level/IVs/EVs/nature/moves.
  - Verified without a real `.sav` via a synthetic builder (`save/synth.py`):
    `tests/test_save.py` **24/24** (crypto, checksums, substructure ordering
    across two PIDs, every PID-derived fact) and `tests/test_bridge.py` — a
    parsed team (shiny "EMBER" Charizard, real spread) battles by real
    mechanics. Format doc: `docs/SAVE_FORMAT.md`.
  - Final gate = a real save (like the touch-decode ritual): `python3 -m
    save.gen3 file.sav`. TODO: PC boxes, items/money (encrypted), save-integrity
    flags (mark illegal spreads `undetermined`).
- **Engine depth pass — status, stages, effects, priority.** The reference
  engine now models: **stat stages** (−6..+6, main + accuracy/evasion) with
  crits ignoring unfavorable stages; **status** (burn/poison/toxic/paralysis/
  sleep/freeze) with real combat effects, end-of-turn residuals, and type-based
  immunities; **confusion**; and per-move **secondary effects** driven by the
  dataset metadata (ailment%, stat changes, flinch, drain, healing, multi-hit,
  recharge). Turn order now uses **move priority** then speed (Quick Attack
  first, Focus Punch last), and drawback moves are handled: **recharge** locks a
  turn, **Focus Punch** fails if hit first, **self-KO** (Explosion/Self-Destruct)
  faints the user, and the auto-moveset picker excludes conditional/2-turn/
  self-KO moves so autonomous sets are sane. Tests: `tests/test_mechanics.py`
  **+22** (burn halves physical only, paralysis ¼ speed, +2 Atk ~2×, crit
  ignores stages, immunities, toxic escalation, seeded status battles resolve).
  Total **48/48**. Still deferred (in IDEAS): 2-turn charge/semi-invuln moves,
  held items, weather, switching/team AI.
- **Reference battle engine (Python) — landed.** `sim/engine.py`: full core
  Gen-III mechanics on the *real* dataset (all 386 species / 372 moves / real
  type chart) — Gen-III stat formula (with natures), damage formula,
  physical/special split *by type*, STAB, crits, the 0.85–1.00 roll, an
  autonomous best-damage AI, and a turn loop. CLI: `python3 -m sim charizard
  blastoise`. This is the canonical **spec** the on-device Kotlin engine gets
  validated against (MultiVera verification gate).
  - Tests: `tests/test_engine.py` — **26/26**, validated against *known*
    references (Mewtwo Lv100 Speed 296/359, the type chart, dual-type products,
    dataset integrity), not just self-consistency.
  - Extension points staged for later passes (each with tests): stat stages,
    status, abilities, held items, weather, move machinery (recharge/charge/
    multi-hit/priority). See `IDEAS.md` for the AI/move-drawback refinement the
    first demo surfaced.
- **Data: Gen-III past-values pass.** 87 moves rolled back to real Gen-III
  power/accuracy/pp/type (Flamethrower 95, Thunder 120, Jump Kick 70); modern
  values kept under `move.modern`.
- **Phase 1 — offline dataset.** `tools/build_pokedex.py` → `data/gen3.json`
  (386 species w/ exact base stats, 372 moves, 76 abilities, 17-type chart,
  Gen-III learnsets, 184 evolutions). Facts only (covenant-clean). Repo
  scaffolded; plans copied into `docs/`.

**Next:** (a) held items + the drawback/moveset refinement; (b) the
damage-calc cross-check fixture; (c) begin the Kotlin on-device engine (port +
validate against this spec) and ART-M1 (`CreatureRenderer`); (d) Phase-3 Gen-III
save parser → SaveTruth. See `MASTER_PLAN.md`.

## Decisions (locked 2026-07-21)
Poképad · Gen III · offline Kotlin engine+data+parser on the phone (drives the
blocks) + optional Python MultiVera backend for chat · repo `xsytrance/pokepad`.
Covenant: facts usable as data; expression = original reinterpretation.
