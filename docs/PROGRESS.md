# Poképad — Progress log

A running build log (newest on top). Decisions, milestones, and what's next.

> **Where the app lives:** HERE — `app/` (`applicationId dev.pokepad`, label
> "Poképad"), migrated from the `clawdpad-app` repo's `:pokepad-app` module on
> 2026-07-23 (pre-migration history in that repo's git log). This repo also
> holds the reference engine (Python), the cross-gate fixtures, the
> save-format tooling, and the design docs. Build/run: see `CLAUDE.md`.

## 2026-07-23 — Poképad moves into its own house

- The Android app module migrated from `clawdpad-app` into this repo as
  `app/` (Gradle root scaffolding added; `include(":app")`). APK verified
  building here; ClawdPad verified still building without it. From now on
  all Poképad work — code, docs, sessions — happens in this repo.

## 2026-07-23 — the app becomes a game

- **👑 2-PLAYER DUEL — verified phone-vs-phone.** The crown feature of the
  [Arena master plan](ARENA_MASTERPLAN.md): two phones on one wifi, one hosts,
  one joins (UDP-beacon auto-discovery, typed-IP fallback), each trainer
  commands their own mon, and the **host runs the one true engine** — the
  joiner sends only its move; the host resolves and broadcasts the turn's
  event stream; both phones render the same truth mirrored to each trainer's
  perspective. Pure-Kotlin protocol stack (`net/DuelProto|DuelCore|DuelNet`,
  dependency-free line protocol) — which made it testable without Android:
  desktop direct-wire battle ✓, socket-loopback battle ✓, PC-python-challenger
  vs phone over real LAN ✓, then **Pixel 8 vs Pixel 10 Pro XL** ✓ (perfect
  mirrored battle on both screens). If your Lightpad is connected, your block
  mirrors YOUR mon + HP during the duel (`block/MirrorScene`).
- **🎮 TRAINER MODE (Phase 2) — you give the commands.** `Battle` gained an
  interactive per-turn driver (`startInteractive`/`stepInteractive`/`stepPvp`);
  the Director can now render ONE turn's events as a mini-reel. UI: classic
  move menu (type + power, type-tinted buttons), turn animates, prompt returns.
  Win/lose ends in an unmistakable full-screen **🏆 VICTORY! / 💥 DEFEAT**
  verdict overlay (added after playtest feedback — both players used to think
  they'd won).
- **🎤 VOICE — like the cartoon.** Toggle VOICE MODE and every turn it listens
  by itself: say your Pokémon's **name** → ack chirp + vibration →
  *"⚡ Salamence! …your command?"* → say the **attack**. Saying the move
  directly also works; it re-listens on misses and backs off if it can't hear.
  Works in Trainer mode and Duels (SpeechRecognizer + fuzzy matcher).
- **🔊 Synthesized sound kit.** 10 chiptune SFX generated from pure code
  (squares/triangles/sweeps/noise — zero sampled audio, covenant-clean):
  summon ball-pop, hit/super/resist impacts, faint slide, victory fanfare,
  defeat descend, menu blips, voice-ack chirp, block-link chime. Cues are
  stamped into the reel at beat starts and fired frame-accurately at playback.
- **📁 Your save, on-device (Phase 1).** `Gen3Save` — a Kotlin port of
  `save/gen3.py`, verified byte-for-byte against the Python reference on a
  real Emerald cartridge dump. "MY TEAM" loads a `.sav` via the system picker,
  shows the real party (sprites, nicknames, natures, shinies), and any mon
  battles with its true level/IVs/EVs/nature/moves. **Read-only, always.**
  The loaded save is persisted and auto-restored at launch ("load once, keep
  forever") and flows automatically into Trainer battles, Duels, and
  block battles.
- **⏱ Pacing.** `HP_PACE = 2`: effective HP pool doubled so fights breathe
  like the anime (stats + damage formula remain real Gen-III; residuals stay
  proportional). HP now holds until the impact frame, then drains over 4
  frames.
- **🎨 Hero art** grew to 19 hand-drawn species (front + back views — backs
  power the first-person camera and the coming vertical face-off), including
  the real save team (salamence/magcargo/smeargle). First-person camera is the
  phone default; SIDE view one tap away.
- **Smoothness pass** (no new features, by directive): edge-to-edge insets
  fixed app-wide; duel disconnects return to the lobby (never eject); JOIN
  scans until a host appears; back-press mid-battle confirms; NEW BATTLE
  restarts without flicker; home buttons show live status ("MY TEAM — NICK ✓",
  "BLOCKS — CONNECTED ✓").
- **On the blocks:** snap-to-battle loops fresh matchups while snapped; the
  lossy master→block-2 relay is made reliable by resending each frame from
  block 2's real ACK position; if a save is loaded, your real mon lead the
  block fights.
- *Engineering notes:* Kotlin nests block comments (`/*` inside a KDoc broke a
  build); Android 15 forces edge-to-edge (insets must be applied manually);
  `getDevices()` misses an already-present USB-MIDI device (use the
  added-callback / `getDevicesForTransport`).

## 2026-07-22

- **END-TO-END: a real battle, rendered.** The engine and the art are now one
  pipeline. `Battle.kt` gained a **typed event sink** (`sealed class Ev`:
  `SendIn` / `Used` / `Faint` / `Win`) with a no-op default `emit` — purely
  additive, so the **200/200** self-test and **285/285** cross-gate are
  untouched. `kotlin/BattleReel.kt` (the **director**) runs a real Gen-III 2v2 on
  the engine, captures that event stream, and turns each event into the matching
  animation beat on a two-panel 15x15 grid: **SendIn→summon, Used→attack+hurt,
  Faint→faint, Win→hold**. Fully autonomous (AI picks moves, the type chart +
  damage formula decide everything). Output → `build/real_battle.gif` (Charizard
  2-KOs and wins; Air Slash super-effective on Venusaur, etc.). **This is exactly
  the pipeline the on-device Scene will run across two snapped blocks** — the only
  thing left is wiring these files into the Android app (needs hardware).
- **Action animations — the block's battle vocabulary.** `kotlin/Anim.kt`: four
  beats, each a pure fn of `(base frame, t)` so the Scene fires them straight
  from engine events. **summon** (Poké Ball drops, snaps open in a white burst,
  creature materialises out of the flash and bounces to settle), **attack**
  (wind-up → lunge with a leading impact streak → recover), **hurt** (white/red
  flash + recoil shove), **faint** (desaturate to grey, tip over via shear, sink
  off-bottom, fade). Poké Ball drawn from primitives (covenant-clean). Frame ops
  (shiftH/shiftDown/shear/tint/grey/dim/revealDisk/over) all return fresh Frames.
  Reel → `build/battle_beats.gif`.
- **Idle animation.** `Renderer.render(…, t)` drives a 16-frame loop: a gentle
  breathing bob, an eye-blink, and the flame-tail flickers tall/short.
  `build/creature_idle.gif` (8 hero mon looping). Renderer `main` modes:
  `static` (full 28-creature sheet), default (idle GIF frames), `action`
  (2-panel beat reel).

- **Kotlin on-device engine — bit-identical to the Python spec.** First step of
  the port that will run on the blocks. `kotlin/Pokepad.kt` implements the
  Gen-III core (stat formula, type chart, damage) in Kotlin; `tools/
  export_fixture.py` has Python emit `fixtures/crossgate.tsv` (311 cases with
  expected values); `tools/kotlin_crossgate.sh` compiles the Kotlin (via the
  Kotlin compiler bundled in the local Gradle dist — no SDK/Android needed) and
  validates it against the Python reference bit-for-bit (the "one rule-set, two
  engines, one gate"). This same fixture will guard the engine when it moves into
  the Android app.
  - **Now covers: stat formula, type chart, damage, stat stages, stage/burn/crit-
    aware damage, and status math** (residual / toxic escalation / paralysis
    speed) — **285/285 cases match** (fixture: 108 chart + 128 stat + 15 eff +
    60 dmg + 13 stage + 24 status + 32 stageDmg). Run: `./tools/kotlin_crossgate.sh`.
  - **Full Kotlin engine now runs** (`kotlin/Battle.kt`): Dex (loads compact
    `data/gen3_{species,moves,typechart}.tsv`), Mon (stats/stages/status),
    abilities, and the complete battle loop — status gating, confusion, flinch,
    recharge, self-KO, priority order, secondary effects, teams + best-matchup
    switching, and the AI — a faithful port of the Python engine. `./tools/
    kotlin_play.sh` runs a 3v3 demo + a self-test (**200/200 seeded battles
    resolve**). Kotlin split into `Engine.kt` (shared math, cross-gated 285/285)
    + `CrossGate.kt` + `Battle.kt`. The on-device brain is complete; RNG-battle
    logic can't cross-gate (Python `random` ≠ Java `Random`) so it's self-tested.
- **ART-M1 started — CreatureRenderer (first pass).** `kotlin/Renderer.kt`:
  turns a species' PokéAPI `shape` + types into an ORIGINAL 15x15 pixel creature
  (archetype from shape: blob/quadruped/biped/serpent/fish/winged/tentacled/
  armor; palette from type) — a block-ready `Frame` + a PNG gallery
  (`tools/…` compile via the bundled Kotlin compiler → `build/creature_gallery.png`,
  sent to Rod for review). Reads by silhouette + type-color; covenant-clean (no
  ripped sprites). **Next: signature features per species** (wings/ears/tails/
  flame) so same-archetype mon differ, then summon/attack/faint **animations** —
  best done with Rod's eyes on the gallery.
  - NEXT (needs hardware/you): wire the Kotlin engine + renderer into a block
    **Scene** in the Android app (reuse clawdpad-app snap/relay/arena). That's
    the "playable on the blocks" step.
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
