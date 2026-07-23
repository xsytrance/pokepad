# Poképad Arena — Master Plan

*Carry your Pokémon in your pocket, on a real glowing block, and battle your
friend with your **actual** team from your **actual** save — giving commands out
loud, like a real trainer.*

This is the plan for the guided, two-player, real-trainer battle experience. It
builds directly on what already works today (real Gen-III engine, on-block
rendering, two-block relay) and adds the pieces that turn a tech demo into the
thing Pokémon fanatics lose their minds over.

---

## 0. The thesis (why this is a revolution)

Every Pokémon game has been played on a screen. **This one lives on a physical
object you can hold, hand to a friend, and snap together.** Three things make it
special, and no official product has ever combined them:

1. **Your real save.** Not a demo roster — the six mon you actually raised, with
   their real IVs/EVs/natures/nicknames, pulled from your real cartridge dump.
2. **Real hardware.** A 15×15 glowing block that *is* your Pokémon. You carry it.
   You summon onto it. You snap two together to fight.
3. **Real-trainer play.** Turn-based, command-driven, voice-enabled — the battle
   cadence of the anime, not an autoplay.

The block is the hook. It's the reason someone buys a Lightpad, re-downloads
their save, and shows their friends. **That's the underground revolution:** a new
physical, social, tactile way to experience the games people already love.

---

## 1. What already works (the foundation)

- **Engine:** full Gen-III battle core in Kotlin — real base stats, 17-type
  chart, damage formula, status, stat stages, abilities, switching. Cross-gated
  bit-for-bit to a Python reference (285/285) and self-tested (200/200).
- **Art:** original 15×15 creatures for all 386 species + summon / attack / hurt
  / faint animations (covenant: no ripped sprites).
- **On the block:** connect a Lightpad over USB-MIDI, snap a second → a real
  battle plays **across both blocks** (hardware-verified 2026-07-22).
- **On the phone:** first-person + side battle cameras, HP boxes, message log.
- **Save parsing (Python, proven):** GBA `.sav` + GameCube `.gci` → SaveTruth
  (real party/box, IVs/EVs/nature/shiny/moves). Validated on two real saves.

The gap between here and the vision is four buildable systems: **on-device save
loading, human turn control, phone-to-phone multiplayer, and the guided UX.**

---

## 2. The guided experience (the whole point)

Everything is a wizard. No menus-within-menus, no jargon. A first-timer with a
block should be battling a friend in under three minutes.

```
MAIN MENU
  ▸ Quick Battle        (vs AI, random or your team — instant fun)
  ▸ 2-Player Battle     (the main event)
  ▸ My Team             (load save, view your mon)
  ▸ How to Play         (30-second animated tutorial)

2-PLAYER BATTLE  (guided, step by step)
  1. Load your save     → file picker → "Found NICK's team! 6 Pokémon ✨"
  2. Pick your squad    → tap your mon for this battle (grid of your real team)
  3. Choose the format  → 1v1 · 2v2 · 3v3 · [more…]  (see §3)
  4. Find your opponent → "Battle nearby" (QR / tap-to-pair) OR "Pass & Play"
  5. Both ready?        → big READY buttons, both must confirm
  6. "SNAP YOUR BLOCKS" → animated prompt; detects the snap; arena lights up
  7. FIGHT              → turn-based, command-driven, voice-enabled (§4)
  8. Result             → winner flourish on the blocks; "Rematch?" / "Save clip"
```

Design rules: **one decision per screen, always a Back, always show what happens
next, celebrate every step** ("Found your team!", "Opponent connected!", the
snap jingle). The block reacts at every stage — Poké Ball idle, a summon burst
when you pick a mon, a VS pulse when both are ready.

---

## 3. Battle formats

| Format | Mon each | Notes |
|---|---|---|
| **1v1** | 1 | Fastest, the default for a first game |
| **2v2** | 2 | Switching matters |
| **3v3** | 3 | The classic "half a team" link battle |
| **Full 6v6** | 6 | Behind an "are you sure?" — real matches run long |
| **Limitless** | any→any | 1v3, 3v1, 5v2… gated by a "Going big! 🔥" confirm |
| **Gauntlet** | your team vs a queue | "battle a ton" — chain fights, block never sleeps |

Formats are just team-size parameters to the same engine — the hard part is UX
(clear picking) and pacing (a 6v6 shows a "long battle ahead" heads-up).

---

## 4. Real-trainer control (turn-based + voice)

Today the AI auto-picks. For real play, **each trainer chooses each turn** — the
core change to the engine is swapping the AI move-picker for a "wait for the
human's command" hook (the engine is already deterministic and event-emitting,
so this is a clean insertion, not a rewrite).

**Turn loop (per trainer, on their phone):**
```
   FIGHT            SWITCH           (later) BAG / RUN
   ┌──────────┐     choose a mon
   │ Move 1   │     from your bench
   │ Move 2   │
   │ Move 3   │     ← shows type, power, PP, "super effective vs their mon"
   │ Move 4   │
   └──────────┘
```
Both commands lock in → the **host** resolves the turn by real mechanics
(priority, speed, accuracy, crits, secondary effects) → emits the event stream →
both phones + both blocks animate it → next turn.

**Voice mode** (the showstopper for the "like the cartoon" feel): tap the mic (or
always-on), say *"Pikachu, use Thunderbolt!"* or *"switch to Charizard!"* Android
`SpeechRecognizer` → a small command parser matches against the active mon's
legal moves / bench. Falls back to the tap menu on low confidence. This is the
detail that makes people *feel* like a trainer.

---

## 5. Multiplayer architecture (two phones, two saves)

The new hard system. Two co-located friends, each with a phone, a block, and a
save. Design goals: **no internet required, no accounts, pair in one tap,
authoritative and cheat-resistant.**

**Transport:** Google **Nearby Connections** (purpose-built offline
device-to-device: discovery + reliable messaging over BT/Wi-Fi, no server).
Fallback: LAN sockets with a QR-code to exchange host IP. "Pass & Play" (one
phone, take turns) needs no transport at all — the zero-friction on-ramp.

**Authority (the anti-desync trick):** one phone is the **battle host**. Both
players' teams live on the host (the joiner sends their SaveTruth team at pairing
— tiny payload). Each turn, the joiner sends only their **command** (move/switch)
to the host; the host runs the one true engine, rolls the RNG, and broadcasts the
resulting **event stream** (the same `Ev` list we already render). Both sides
render identical outcomes because only one machine computes them. No lockstep, no
divergence, no trust required in the client.

**Physical setups (all supported):**
- **Arena (snap):** two blocks snapped, the **host phone drives both** (today's
  working relay). Each block shows one trainer's active mon; the joiner's phone is
  a controller + team source over Nearby. This is the "snap them together" dream.
- **Duel (apart):** each phone drives its own block; phones paired over Nearby.
  Works across a table or a room — no physical snap needed.
- **Share-one-block:** shrink both mon onto a single 15×15 (top/bottom halves),
  one phone, two players tapping in turn. The cheapest way in — you only need one
  block between two people.

---

## 6. Real saves on-device (the covenant core)

Port the proven Python parser to Kotlin so the app reads a save **on the phone**:
`.sav` (GBA: RSE/FRLG) and `.gci` (GameCube: Pokémon Box). The format is fully
documented and test-covered in Python (`save/gen3.py`, `save/box_rs.py`,
`docs/SAVE_FORMAT.md`) — this is a disciplined port, not research:

- 14-section slot select, party + box decode, per-mon decrypt (key = PID^OTID),
  PID%24 substructure order, nature/shininess/IV/EV/ability/moves derivation.
- Cross-gate the Kotlin parser against the Python one (same fixture discipline
  that got the engine bit-perfect) so we *know* it reads real cartridges right.
- **Read-only, always.** We never write saves. "Facts are sacred."

Unlocks: "load your save → here's your real team" — the emotional gut-punch that
makes someone care. This is Phase 1 for a reason: it's the single biggest
"whoa" and it needs no multiplayer.

---

## 7. Pokémon cards — `cashemall` (future)

Rod has a `cashemall` repo with real work already in it (TCG-related). Once the
battle spine is solid, cards become a second on-ramp and a collection layer:
- Scan / own a card → summon that Pokémon to your block.
- A card-driven team source (for people without a save).
- Possibly a light TCG mode later.
I haven't opened `cashemall` yet — when we reach this phase I'll read it and fold
it in properly.

---

## 8. The covenant & the IP reality (said plainly)

- **Covenant:** *facts are sacred, feelings are free.* Real stats/lore/mechanics
  are used as data; **all art is original** (no ripped sprites, ever).
- **IP reality:** game mechanics and stats are facts (not copyrightable), but the
  names, characters, and likenesses are Nintendo/Game Freak's. Original art keeps
  us clean on sprites; the trademarks are the line. So: **keep it non-commercial
  and community/underground** (as you said), original art only, and if it ever
  goes public, consider a "generic names" toggle. Build it for love, share it
  with the community, don't try to sell Nintendo's trademarks. That's the honest
  boundary — and it's exactly the "underground" spirit you already named.

---

## 9. Roadmap (each phase is a shippable, showable thing)

| Phase | Deliverable | Needs HW? |
|---|---|---|
| **0 — Art** | Recognizable per-species art (Pikachu ≠ Raichu at a glance) | no |
| **1 — Your team** | On-device Kotlin save parser → load your real save, battle it vs AI | no |
| **2 — Trainer control** | Turn-based FIGHT/SWITCH menus + **voice commands** vs AI | no |
| **3 — Duel** | Two phones over Nearby, host-authoritative, 1v1 real battle | 2 blocks |
| **4 — Formats** | 2v2 / 3v3 / 6v6 / Limitless + team builder from your box | some |
| **5 — Arena & share** | Snap-to-arena (host drives both), share-one-block mode, vertical face-off | blocks |
| **6 — Cards** | `cashemall` integration | — |
| **7 — Guided polish** | The full wizard, tutorial, victory clips, "make it effortless" | phones |

Recommended order to maximize "whoa" per week: **0 → 1 → 2 → 3**. By the end of
Phase 3 you have the headline demo: *two friends, two blocks, two real saves,
giving voice commands, battling for real.* That clip is what sells the block.

---

## 10. What makes them lose their minds

It's not the feature list — it's the **moment**:

> You hand your friend a glowing block. They load the save from the cartridge
> they've had since they were ten. Their starter — the one with the dumb nickname
> — materializes on the glass in a Poké Ball burst. You snap your blocks together.
> You say *"Charizard, Flamethrower!"* out loud. The block flashes, their mon
> reels, the HP drops for real by real math. You're not watching a game. You're
> **standing across from a friend, as trainers, with the Pokémon you actually
> raised, on a thing you can hold.**

Nobody has ever been able to do that. That's why they'll want the block. That's
the revolution. Let's build it. 🔥

---

*Companion docs: [VISION.md](VISION.md), [MASTER_PLAN.md](MASTER_PLAN.md) (the
original phased build), [SAVE_FORMAT.md](SAVE_FORMAT.md), [IDEAS.md](IDEAS.md).*
