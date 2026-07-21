# Poképad

A **save-aware Pokémon companion, embodied on ROLI Lightpad blocks** — part of
the MultiVera family (one engine, many worlds; *facts are sacred, feelings are
free*). Read your **own** Gen-III save, summon your real Pokémon onto a block,
and **snap two blocks together to battle** by the *actual* Gen-III mechanics.

- **Codename:** Poképad · **Target:** Gen III (Ruby/Sapphire/Emerald/FR/LG)
- **Runtime:** self-contained Kotlin on the phone (battle engine + bundled data +
  save parser, offline, drives the blocks) + an optional Python MultiVera
  backend for the companion chat. `SaveTruth` JSON is the shared contract.
- **Covenant:** read-only saves; mechanical **facts** (stats/types/moves) are
  usable data; **expression** (dex prose, sprites, names, music) is *original
  reinterpretation* only — no ripped assets. Original branding.

## Docs
- `docs/MASTER_PLAN.md` — the phased build (scrape → engine → SaveTruth → blocks → companion).
- `docs/RENDERING_PLAN.md` — every Pokémon + balls + animations on 15×15, procedurally.
- `docs/VISION.md` — the seed / why it's not a knockoff.

## Phase 1 — the data (this repo, now)
`tools/build_pokedex.py` scrapes **PokéAPI** into a normalized, versioned,
**offline** Gen-III dataset (`data/gen3.json`) that the app bundles. Facts only
(no flavor text / sprites). Run:

```bash
python3 tools/build_pokedex.py           # builds data/gen3.json (caches to .cache/)
python3 tools/build_pokedex.py --verify  # re-print the spot-checks
```

Data: **386 species**, all Gen-III **moves / abilities**, the **17-type chart**,
learnsets, and evolutions — sourced from [PokéAPI](https://pokeapi.co)
(mechanical data; we ship no copyrighted expression).
