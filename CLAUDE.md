# Poképad

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
