# Gen-III save format — parser notes (READ-ONLY)

How Poképad reads a Ruby/Sapphire/Emerald/FireRed/LeafGreen save into
**SaveTruth**. Implementation: `save/gen3.py`; round-trip test: `save/synth.py`
+ `tests/test_save.py`. **We never write saves.** (Reference: Bulbapedia
"Save data structure in Generation III" + PKHeX.)

## Container
- 128 KB file = **two 14-section slots** (A @ 0x0000, B @ 0xE000). Each section
  is 0x1000 bytes: data + a footer at 0x0FF4: section id (u16), checksum (u16),
  signature `0x08012025` (u32), save index (u32).
- Sections are stored rotated; the **section id** says which is which
  (0 = trainer, 1 = team/items, 2–4 = game state, 5–13 = PC boxes).
- The **active slot** is the one whose sections carry the **higher save index**
  (0xFFFFFFFF = unused).

## Section 0 — trainer
name (0x00, 7 bytes, Gen-3 charmap), gender (0x08), TID/SID (0x0A/0x0C),
playtime (0x0E h / 0x10 m), **game code** (0x00AC: 0=RS, 1=FRLG, else Emerald) —
which selects the team offsets.

## Section 1 — team
- RSE: size @ 0x0234, party @ 0x0238. FRLG: size @ 0x0034, party @ 0x0038.
- Party = up to 6 × **100-byte** Pokémon.

## A party Pokémon (100 bytes)
- 0x00 PID (u32), 0x04 OT ID (u32), 0x08 nickname (10), 0x14 OT name (7),
  0x1C checksum (u16), 0x20 **data (48 bytes, encrypted)**, 0x54 level,
  0x56 current HP.
- **Decryption:** key = `PID ^ OTID`; XOR each 32-bit word of the 48-byte block.
- **Substructure order** = `PID % 24` → a permutation of four 12-byte blocks
  `{Growth, Attacks, EVs, Misc}` (the 24-entry `ORDERS` table).
  - **Growth:** species (internal index), held item, experience, friendship.
  - **Attacks:** 4 move indices + PP.
  - **EVs:** HP/Atk/Def/Spe/SpA/SpD.
  - **Misc:** origins (met level, ball, game), a packed IV word (5 bits each +
    egg + ability bit), ribbons.
- **Derived facts** (computed, sacred): nature = `PID % 25`; shiny =
  `(TIDlo ^ TIDhi ^ PIDlo ^ PIDhi) < 8`; gender from the species ratio +
  `PID & 0xFF`; ability from the ability bit.

## Index maps (why the dataset carries them)
Saves store **internal indices**, not names: species (Gen-III internal ≠ dex #,
e.g. Treecko = 277) and moves (index, e.g. Ember = 52). `data/gen3.json` ships
`internal_to_national` and `move_index_to_name` so the parser resolves names,
and `save/bridge.py` turns a party entry into an engine Pokémon with its real
level/IVs/EVs/nature/moves.

## Covenant
Read-only. Facts (stats/IVs/moves/nature) are data; the *voice/art* the
companion wraps around them is original reinterpretation. Impossible values
(IVs > 31, illegal moves) should be surfaced as `undetermined`/`suspect`, not
silently fixed (a future integrity pass — see IDEAS.md).

## Validation status
Round-tripped via a synthetic save (`tests/test_save.py`, `tests/test_bridge.py`)
— crypto, checksums, substructure ordering (two PIDs), and every PID-derived
fact. The **final gate is a real save** (Rod's), like the touch-decode ritual:
drop a real `.sav`, run `python3 -m save.gen3 file.sav`, and confirm the party
matches the game.
