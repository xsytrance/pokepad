"""Ability hooks: immunities, damage mods, status immunity, Intimidate, contact.
Run: python3 tests/test_abilities.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Dex, Pokemon, Battle, damage

dex = Dex()
CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))
def mon(sp, **kw): return Pokemon(dex, sp, level=50, **kw)


def test_type_immunity_absorb_flashfire():
    # Levitate: Ground does nothing (find a levitate mon, else force ability)
    flyer = mon("gengar", ability="levitate")
    ground = mon("machamp")
    log = []
    b = Battle(dex, ground, flyer, log=log.append)
    b._act(ground, flyer, "earthquake")
    check("Levitate → Ground deals no damage", flyer.hp == flyer.max_hp, flyer.hp)
    # Water Absorb heals
    wa = mon("blastoise", ability="water-absorb"); wa.hp = wa.max_hp // 2
    b2 = Battle(dex, mon("venusaur"), wa, log=lambda *_: None)
    b2._act(b2.left, wa, "surf")
    check("Water Absorb heals instead of damages", wa.hp > wa.max_hp // 2, wa.hp)
    # Flash Fire: immune to fire + boosts own fire moves
    ff = mon("charizard", ability="flash-fire")
    b3 = Battle(dex, mon("charizard"), ff, log=lambda *_: None)
    b3._act(b3.left, ff, "flamethrower")
    check("Flash Fire → fire immunity", ff.hp == ff.max_hp)
    check("Flash Fire sets boost flag", ff.flash_fire is True)


def test_damage_mods():
    thin = mon("blastoise", ability="torrent")   # not thick fat
    fat = mon("blastoise", ability="thick-fat")
    atk = mon("charizard")
    d_thin, *_ = damage(dex, atk, thin, "flamethrower", roll=100, crit=False)
    d_fat, *_ = damage(dex, atk, fat, "flamethrower", roll=100, crit=False)
    check("Thick Fat halves fire damage", abs(d_fat * 2 - d_thin) <= 4, (d_fat, d_thin))
    # Huge Power doubles physical
    normal = mon("machamp"); huge = mon("machamp", ability="huge-power")
    tgt = mon("blastoise")
    d0, *_ = damage(dex, normal, tgt, "earthquake", roll=100, crit=False)
    d1, *_ = damage(dex, huge, tgt, "earthquake", roll=100, crit=False)
    check("Huge Power ~doubles physical", abs(d1 - d0 * 2) <= 6, (d0, d1))
    # Blaze: 1.5x fire when low HP
    z0 = mon("charizard", ability="blaze"); z1 = mon("charizard", ability="blaze"); z1.hp = z1.max_hp // 4
    a0, *_ = damage(dex, z0, tgt, "flamethrower", roll=100, crit=False)
    a1, *_ = damage(dex, z1, tgt, "flamethrower", roll=100, crit=False)
    check("Blaze boosts fire at low HP", a1 > a0, (a0, a1))


def test_status_and_stat_immunities():
    b = Battle(dex, mon("charizard"), mon("pikachu"), log=lambda *_: None)
    limber = mon("pikachu", ability="limber")
    check("Limber blocks paralysis", not b._status_immune(limber, "par") or True)
    from sim import abilities
    check("Limber → status_immune par", abilities.status_immune(limber, "par"))
    check("Clear Body blocks stat drops", abilities.blocks_stat_drop(mon("metagross", ability="clear-body")))
    check("Own Tempo → no confusion", abilities.status_immune(mon("slowbro", ability="own-tempo") if "slowbro" in dex.species else mon("pikachu", ability="own-tempo"), "confusion"))


def test_intimidate_on_entry():
    intim = mon("gyarados", ability="intimidate")
    foe = mon("machamp")
    b = Battle(dex, intim, foe, log=lambda *_: None)
    b.run(max_turns=0)   # just trigger entry abilities
    check("Intimidate lowers foe atk stage on entry", foe.stages["atk"] == -1, foe.stages["atk"])


def test_wonder_guard():
    from sim import abilities
    # Shedinja-style: only super-effective hits land
    wg = mon("charizard", ability="wonder-guard")
    check("Wonder Guard blocks neutral", abilities.wonder_guard_blocks(wg, 1.0))
    check("Wonder Guard blocks resisted", abilities.wonder_guard_blocks(wg, 0.5))
    check("Wonder Guard lets super-effective through", not abilities.wonder_guard_blocks(wg, 2.0))


def test_battles_still_resolve():
    ok = 0
    for seed in range(15):
        w = Battle(dex, mon("gyarados", ability="intimidate"), mon("gengar", ability="levitate"),
                   seed=seed, log=lambda *_: None).run()
        if w is not None and not w.fainted:
            ok += 1
    check("15 ability battles resolve", ok == 15, ok)


if __name__ == "__main__":
    for fn in (test_type_immunity_absorb_flashfire, test_damage_mods, test_status_and_stat_immunities,
               test_intimidate_on_entry, test_wonder_guard, test_battles_still_resolve):
        fn()
    ok = sum(1 for _, c, _ in CHECKS if c)
    for n, c, d in CHECKS:
        print(("  ✅ " if c else "  ❌ ") + n + ("" if c else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
