# Poképad — Progress log

A running build log (newest on top). Decisions, milestones, and what's next.

## 2026-07-21

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
