"""
Poképad — Gen-III abilities as hooks.

A curated set of the impactful ones, expressed as small pure functions the
engine calls (no import from engine → no cycle). Everything takes primitives /
the Pokémon object. Unlisted abilities are simply inert for now (data-driven
expansion is a later pass; the dataset already carries every ability + effect
text). Weather-dependent abilities (Chlorophyll/Swift Swim) wait on the weather
feature.
"""
from __future__ import annotations

BLAZE_FAMILY = {"overgrow": "grass", "blaze": "fire", "torrent": "water", "swarm": "bug"}
ABSORB = {"water-absorb": "water", "volt-absorb": "electric"}
CONTACT_ABIL = {"static": "par", "flame-body": "brn", "poison-point": "psn"}
# physical moves that DON'T make contact (so contact abilities don't trigger)
NON_CONTACT = {"earthquake", "rock-slide", "rock-throw", "magnitude", "bone-club",
               "bonemerang", "bone-rush", "fissure", "sand-tomb", "mud-shot",
               "razor-leaf", "rock-tomb", "ancient-power", "gust", "twister"}


def type_immunity(defender, move_type: str):
    """None | 'immune' | 'absorb' (heal ¼) | 'flashfire' (fire immunity + boost)."""
    ab = defender.ability
    if ab == "levitate" and move_type == "ground":
        return "immune"
    if ABSORB.get(ab) == move_type:
        return "absorb"
    if ab == "flash-fire" and move_type == "fire":
        return "flashfire"
    return None


def wonder_guard_blocks(defender, eff: float) -> bool:
    return defender.ability == "wonder-guard" and eff <= 1.0


def offense_mult(attacker, move_type: str, phys: bool) -> float:
    ab = attacker.ability
    m = 1.0
    if ab == "huge-power" and phys:
        m *= 2.0
    if ab == "guts" and attacker.status and phys:
        m *= 1.5
    if ab in BLAZE_FAMILY and move_type == BLAZE_FAMILY[ab] and attacker.hp * 3 <= attacker.max_hp:
        m *= 1.5
    if getattr(attacker, "flash_fire", False) and move_type == "fire":
        m *= 1.5
    return m


def defense_mult(defender, move_type: str, phys: bool) -> float:
    ab = defender.ability
    m = 1.0
    if ab == "thick-fat" and move_type in ("fire", "ice"):
        m *= 0.5
    if ab == "marvel-scale" and defender.status and phys:
        m *= 1.5
    return m


def status_immune(defender, code: str) -> bool:
    return (defender.ability, code) in {
        ("limber", "par"), ("immunity", "psn"), ("immunity", "tox"),
        ("insomnia", "slp"), ("vital-spirit", "slp"), ("water-veil", "brn"),
        ("magma-armor", "frz"), ("own-tempo", "confusion"),
    }


def blocks_stat_drop(defender) -> bool:
    return defender.ability in {"clear-body", "white-smoke"}


def contact_status(move_name: str, phys: bool, defender, rng):
    """defender's on-contact ability may status the ATTACKER (30%)."""
    if not phys or move_name in NON_CONTACT:
        return None
    ab = defender.ability
    if ab in CONTACT_ABIL and rng.randint(1, 100) <= 30:
        return CONTACT_ABIL[ab]
    return None


def on_switch_in(mon, foe, log):
    """entry abilities (Intimidate). Returns nothing; mutates foe."""
    if mon.ability == "intimidate" and not mon.fainted:
        if not blocks_stat_drop(foe):
            got = foe.boost("atk", -1)
            if got:
                log(f"  {mon.name}'s Intimidate cut {foe.name}'s attack!")
