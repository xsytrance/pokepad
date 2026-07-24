# Poképad — Ideas & Improvements (running log)

My own suggestions as I build. Not commitments — a menu to pull from. Newest on
top. (Rod asked me to always add ideas/improvements as I go.)

## Pokéball Showcase (2026-07-24)

- **Species "cries".** Synthesize a per-species chirp from its stats/types
  (pure-code, covenant-clean: base pitch from species id, contour from shape)
  and play it at the reveal — every mon sounding different sells it hard.
- **Attract auto-cycle.** Idle in showcase for ~60s → the ball starts showing
  the party on its own (peek → reveal → a move → return, next mon), like a
  shop-window demo loop. One flag on the existing state machine.
- **Party carousel on the ball.** Swipe the glass left/right while closed to
  choose WHICH mon is "in" the ball (a colored dot per party slot along the
  bottom row); the name you speak still overrides.
- **Throw gesture.** Press-and-flick on the glass = throwing the ball: the
  ball art shrinks/arcs then bursts open. Touch decode already gives
  velocity — the flick IS the throw strength; harder throw = bigger burst.
- **Shiny ball tint.** While a shiny is inside, the closed ball's button
  glints gold every few seconds — collectors will notice before the reveal.
- **"Who's that Pokémon?"** party game: the block shows the mon's silhouette
  (all pixels one color), friends guess, any correct name spoken reveals.
- **Showcase → battle handoff.** From a revealed mon, say "battle!" to jump
  straight into Trainer mode with that mon as the lead.

## Engine & AI

- **[MOSTLY DONE] Model move drawbacks in the AI (found live).** Fixed: the
  moveset picker now excludes conditional/2-turn/self-KO moves (sane sets), the
  engine models recharge locks, Focus-Punch-fails-if-hit, self-KO faints, and
  turn order uses move priority. STILL TODO: 2-turn charge/semi-invulnerable
  moves (Solar Beam, Fly, Dig…) are excluded rather than modeled — model them so
  they can be used; and a smarter AI that *uses* boost/status moves (right now
  power-0 moves score 0 so are never chosen — status only appears via damaging
  moves' secondary effects).
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
- **[PARTIAL] Team preview / lead logic.** DONE: 6v6 with forced switch on
  faint, best-matchup send-in; 2026-07-24: HUMAN-chosen switches in Trainer
  mode + Duels (formats 1v1/2v2/3v3/limitless — the player picks who's next,
  AI keeps best-matchup). TODO: **voluntary** strategic switching mid-battle
  (pivot out of a bad matchup before fainting) — the thing that makes it feel
  *smart*. Guard against switch-loops (cap voluntary switches / only switch when
  the incoming mon is a clear improvement AND the active is in real danger).
- **Switch animation on the blocks.** A faint→send-next is a natural "return to
  ball → throw next ball" beat; on two blocks the incoming mon could *walk in
  from the far edge* across the seam.

## Save data → SaveTruth

- **PC boxes = the whole collection, not just the party.** Sections 5–13 hold
  ~420 boxed mon (30 bytes shorter each — no party stat block). Parsing them
  unlocks "summon anyone you've ever caught" and a physical, personal Pokédex on
  the block. Big payoff, moderate work (same crypto, box layout).
- **A save-truth diff between two saves of the same game** ("you released me in
  this file") needs stable identity — match on PID (unique per mon), not species.

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
