# Poképad — Ideas & Improvements (running log)

My own suggestions as I build. Not commitments — a menu to pull from. Newest on
top. (Rod asked me to always add ideas/improvements as I go.)

## Engine & AI

- **Model move drawbacks in the AI (found live).** The reference AI currently
  grabs the highest raw-BP move, so it happily picks Hyper Beam / Hydro Cannon /
  Blast Burn (recharge) and Focus Punch (priority −3, fails if hit first). Two
  fixes: (a) the *moveset picker* should build a *competitively sane* set
  (spread of types, avoid two recharge moves, include coverage), and (b) the
  *engine* should model recharge / charge-up / priority so those moves carry
  their real cost. Until then, tag such moves in the dataset with a `drawback`
  field so the AI discounts them.
- **A proper damage-calc cross-check.** Add a fixture of ~30 famous Gen-III
  matchups with the exact damage ranges from a trusted calc (min–max rolls),
  and assert our engine's spread matches. This is the real "our mechanics are
  correct" proof and the gate the Kotlin port must also pass.
- **Deterministic replays.** A battle is a seed + two teams. Store the seed so
  any block battle can be re-simulated/verified off-device — great for the
  MultiVera truth-audit ("the block showed X; here's the same battle in Python").
- **Speed ties, and Gen-III turn quirks.** We coin-flip speed ties (correct).
  Later: model Gen-III specifics players will notice — the old crit system
  (stages, Focus Energy *lowering* crits was a Gen-I bug, fixed by III),
  Hyper Beam not recharging on KO, Wrap/Bind, Destiny Bond, etc.
- **Team preview / lead logic.** When save data gives a 6-mon team, the "AI"
  should switch, not just spam the lead. Even simple heuristics (switch on a
  bad matchup) make autonomous battles feel *smart* on the blocks.

## Save data → SaveTruth

- **The "your actual mon" gut-punch.** When a battle uses a mon from the real
  save, surface its *provenance* on the block: OT, met location/level, the date
  you caught it, its friendship. A Lv63 Charizard you raised from a Charmander
  in 2009 hits different than a generated one. That provenance IS the product.
- **Illegal/hacked-save honesty.** Per the covenant, if a save has impossible
  values (IVs > 31, an egg-move it can't learn), don't silently "fix" it — mark
  it `undetermined`/`suspect` in SaveTruth and let the companion *comment* on it
  ("that's… not a legal spread, trainer"). Facts sacred means honest, not tidy.
- **Cross-save "Divergence" on the table.** Two blocks, two of your saves → the
  same species speaks to the fork. Physicalized "Across Your Saves."

## Rendering / blocks (beyond RENDERING_PLAN.md)

- **The type aura as a readability crutch, not decoration.** On a 15×15 you
  can't always tell a quadruped from another quadruped — but the *aura color* +
  a single *signature pixel* (a spark, a leaf, a flame) lets you read species by
  vibe across the room. Lean on it.
- **Attack FX that cross the seam are the signature.** We already fly moves from
  block to block. Make the *whole arena* react: a Surf wave sweeps left→right
  across both screens; Earthquake shakes both; Sunny Day tints both. The two
  blocks as one weather system is the "wow."
- **Faint = return to ball, not just a poof.** Reuse the return-beam animation
  as the faint, so the loop reads as real Pokémon (KO → recalled → next mon).
- **Shiny is a *save fact*, not a toggle.** Derive it from the PID in SaveTruth
  and render the shimmer only then. A shiny on the block should feel earned.

## Poképad-specific (only possible because it's hardware + save-aware)

- **Snap-to-battle as a social object.** Two people, two phones, two blocks —
  snap them and your real teams fight. That's a *thing you do at a table*, not
  an app you open. Lean the whole design toward that moment.
- **The block as a Pokédex you hold.** Between battles, the block cycles your
  caught species (from the save's dex) as living idles — a physical, personal
  Pokédex.
- **Gym-leader / rival personas from the save.** Your rival's name and team are
  in the save. Summon *your rival's* team onto the second block for a grounded
  rematch, with the companion voicing them (reinterpreted).
- **Battle royale = the topology is the bracket.** 3–6 snapped blocks; the ROLI
  connection graph decides adjacency/matchups. Rearranging blocks on the table
  literally reseeds the tournament.

## Verification / process (the MultiVera discipline)

- **One rule-set, two engines, one gate.** This Python engine is the spec;
  the Kotlin on-device engine must pass the *same* fixture suite. Wire a shared
  JSON of `(team, seed) → expected event log` both engines validate against.
- **Data provenance in the dataset.** `gen3.json.meta` already records source +
  version; add per-field source notes for anything hand-corrected so future-me
  can audit why a value is what it is.
