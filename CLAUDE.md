# Poképad

<!-- CANON:BEGIN v1 2026-08-07 — managed by the Singularity Event. Edit the source, not this block. -->
## The Dominion — standing canon (v1)

**Theme.** Everything in this fleet is named and spoken in the register of
**magic, science, and military** — *"Doctor Doom meets Master Chief."* Imperial,
arcane, martial, over real engineering. Music is the soul that runs through all
three. The Lexicon (`hermes360/docs/codex/lexicon.json`) is the source of truth
for names; a themed name with no Lexicon entry is a bug, not creativity.

> **The Iron Rule.** The theme is a **naming / lore / presentation layer over
> stable technical identifiers. It NEVER renames the substrate.** Ports stay
> numeric in code; unit names, API paths, file names, env vars, and DB tables are
> unchanged. Themed names appear in agent speech, UIs, docs, and conversation —
> never in code identifiers. Renaming the substrate would break every running
> system, backup, and timer on the fleet.

Core terms: fleet → **the Dominion** · owner → **the Sovereign** · host →
**Realm** · PRIME → **the Citadel** · exxo-1 → **the Foundry** · tailnet →
**the Ley Lines** · service → **Engine** · agent → **Champion** · port →
**Portal** · endpoint → **Gate** · code → **Spell** · function → **Incantation**
· database → **Vault** · config → **Ward** · secret → **Seal** · doc → **Tome**
· log/receipt → **Chronicle** · backup → **Wardstone** · monitor → **the Augury**
· LLM → **Familiar** · notification → **a Sending** · Singularity → **the Grand
Archive**. *(Top names blessed by the Sovereign 2026-08-07.)*

**Reporting.** Every substantive reply ends with a `## TL;DR` — last, after the
detail, 3–5 bullets. Lead with anything the Sovereign must act on. Corrections
go **in** the TL;DR, never buried in the body.

**ISI.** On a big feature, a big change, a security posture, a schema change, or
a new project: **Intent** (what is he really trying to achieve?), **Sanity** (is
this the right approach? say so plainly, once), **Improvement** (is there a
better way? what would I add?). Verify with commands — measured beats plausible.
ISI is advisory, not a veto: raise it, recommend, then build. If he reaffirms,
that's the decision. Not permission to stall, and not permission to gold-plate.

**Secrets.** `~/.config/<system>/env`, mode 600. Never in a chat box, a commit,
or a screenshot. Exposed once = rotate the same day. `docs/SECURITY.md` is law.

**The Five Foundations.** One network (the tailnet) · one wallet (OpenRouter,
named key per system) · one secrets pattern · one memory (this) · one ark
(exxo-1). Full text: `docs/MASTER_PLAN.md`.

**Birth and death.** A new system gets, on day 0: `git init`, an env file (600),
a named key if it spends, a **Lexicon entry**, a row in `docs/SYSTEMS.md`, and an
Eye config if it has a UI. *A system not in the registry does not exist.* Cold
for 60 days → `~/archive/`. Archiving is honorable; drift is not.
<!-- CANON:END -->

<!-- BULLETIN:BEGIN 2026-08-08T12:42 — managed by the Singularity Event. Facts, not rules. Edit the registry, not this block. -->
## The Dominion — the roster (41 systems)

You are in **pokepad**. ROLI Lightpad Block as a physical Pokéball: shows/battles Pokémon from real Gen 3 save data; snap 2 blocks to fight.

**Tell the Archive anything that matters:** `tell-singularity "…"` (`--birth <sys>` · `--death <sys>` · `--change <sys>` · `--ask "…"`)
**Find out what you missed:** `~/singularity/scripts/brief.sh`

### Born or changed in the last 14 days
- **planet-studio** — 2026-08-08 — satellite (music) — Android studio companion for x1c7.com: the Wall, galaxy, cover studio…
- **audiex** (the Warhorn) — 2026-08-08 — satellite (music) — standalone offline-first player for the Suno catalog; the planet-studio…
- **stem-racer** — 2026-08-07 — satellite (music/game) — stem-based racing game; APK served from ~/apk-share.
- **cadence** — 2026-08-07 — the Dominion's ceremony bus (Portal 8114). Any Engine posts a rite; it decides how it is felt…
- **vgclan** — 2026-08-02 — satellite — VG Clan revival site; re-recruit the founders, deploy to vgclan.x1c7.com.
- **NEXUS** — 2026-07-31 — command vault (obsidian) — Gradle project with mobile-web application components.
- **memguard** — 2026-07-31 — utility — guards against memory exhaustion on Prime; the GPU is shared (16 GB) and a runaway…
- **singularity** (the Grand Archive) — 2026-07-31 — the Grand Archive. System of record for a life: every chat, doc, photo and receipt, dated…

### The full roster
`sayhai` · `stem-racer` · `va-academy` · `vgclan` · `cadence` · `entangled-private` · `entangled-tools` · `xsyverse` · `fft-psx-vera` · `hermes360-c2-artifacts` · `argus-risk-adviser` · `clawdpad-app` · `aurex16pp` · `ember-lite` · `kinetica` · `planet-studio` · `audiex` · `vAIb` · `pokepad` · `ossicle-backups` · `Hermes` · `ossicle` · `singularity-integration` · `x1c7.com` · `AGENOR-Horology` · `atlas` · `entangled` · `undertale-vera` · `eye-of-thundera` · `hermes360` · `xsywatch` · `NEXUS` · `memguard` · `singularity` · `skynet` · `xsynet` · `ossicle-worktrees` · `dazzler` · `claudeblock` · `ember-pro` · `prism`

Live: `GET :8801/api/event/roster` · Canonical: `singularity/docs/SYSTEMS.md`
<!-- BULLETIN:END -->

MultiVera "read real save → SaveTruth → real Gen-III battles on ROLI Lightpad blocks".
This repo is the whole product; the Android app was migrated here from clawdpad-app on 2026-07-23
(its pre-migration git history lives in github.com/xsytrance/clawdpad-app under `pokepad-app/`).

## Layout

- `app/` — the Android app (`applicationId dev.pokepad`, label "Poképad").
  - `dev.pokepad.core` — Gen-III battle engine + Renderer/Anim/Director (cross-gated vs the Python spec).
  - `dev.pokepad.ui` — home, BattleView, TrainerActivity (turn-based), DuelActivity (LAN 2-player), PickerActivity, SaveActivity, Voice, Music, Sfx.
  - `dev.pokepad.save` — Kotlin Gen-III save parser (verified byte-for-byte vs Python on a real Emerald cart).
  - `dev.pokepad.block` — Lightpad block stack (MIDI transport, Streamer w/ lossy-relay resend, Host/Keeper, scenes).
  - `dev.pokepad.net` — duel protocol (TCP 47474, UDP 47475 discovery), host-authoritative.
- `sim/`, `save/` (Python) — the SPEC engine + save parsers; Kotlin is validated against these (285/285 cross-gate, 115 Python checks).
- `kotlin/` — desktop-runnable copies for galleries/crossgate (`HeroArt.kt` must stay in sync with `app/`'s copy).
- `docs/` — MASTER_PLAN, ARENA_MASTERPLAN (north star), RENDERING_PLAN, SAVE_FORMAT, PROGRESS, IDEAS.
- `data/`, `fixtures/` — offline Gen-III dataset + cross-gate fixtures. TSVs also ship in `app/src/main/assets/poke/`.

## Build (no gradlew, no java on PATH)

```
export JAVA_HOME=/home/xsyprime/.gradle/jdks/eclipse_adoptium-17-amd64-linux.2
/home/xsyprime/.gradle/wrapper/dists/gradle-9.6.1-bin/*/gradle-9.6.1/bin/gradle assembleDebug --console=plain
```

SDK path comes from `local.properties` (`/home/xsyprime/Android/Sdk`, gitignored).
Desktop Kotlin (galleries/crossgate): the gradle dist's bundled K2JVMCompiler — see `tools/kotlin_play.sh` / `tools/kotlin_crossgate.sh`.
Python spec tests: `python3 -m pytest tests/` (115 checks; real-save checks are guarded, saves are gitignored).

## Hardware

- Rod's Pixel 10 Pro XL (P1): wifi adb `adb connect 192.168.1.62:5555`. Don't drive/screenshot it while Rod is using it.
- Pixel 8 (P2): USB serial 39261FDJH00G5V, wifi 192.168.1.190. Density differs from P1 — uiautomator-dump for tap bounds, don't reuse dp-derived px.
- Blocks connect as **Android MIDI** devices (USB-C or BLE-MIDI); open from `onDeviceAdded`, replug after reinstall if not re-registered.
- `cmd statusbar collapse` before adb taps (shade intercepts).

## Rules

- NEVER commit saves (`*.sav`, `*.gci` gitignored) — Rod's personal saves sit in the repo root.
- Covenant: facts (stats/moves/types) are sacred data; expression (art/names/dex text) is original only. No ripped assets. Non-commercial.
- Kotlin nests block comments — `/*` inside a KDoc breaks the build.
- No `Date.now()` assumptions in tests; deterministic engine is the point.
- Always log new ideas in `docs/IDEAS.md`; keep `docs/PROGRESS.md` current. Commit every big step.
