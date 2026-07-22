"""Deeper-mechanics verification: stat stages, status, and move effects.
Run: python3 tests/test_mechanics.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Dex, Pokemon, Battle, damage, stage_mult, acc_mult

dex = Dex()
CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))
def mon(sp, **kw): return Pokemon(dex, sp, level=50, **kw)


def test_stage_multipliers():
    check("stage_mult(0)==1", stage_mult(0) == 1.0)
    check("stage_mult(+1)==1.5", stage_mult(1) == 1.5)
    check("stage_mult(+2)==2.0", stage_mult(2) == 2.0)
    check("stage_mult(+6)==4.0", stage_mult(6) == 4.0)
    check("stage_mult(-1)==2/3", abs(stage_mult(-1) - 2/3) < 1e-9)
    check("stage_mult(-6)==0.25", stage_mult(-6) == 0.25)
    check("acc_mult(+1)==4/3", abs(acc_mult(1) - 4/3) < 1e-9)


def test_burn_halves_physical_only():
    # ability="pressure" is inert re: damage (Machamp's real ability is Guts,
    # which correctly ignores burn — tested in test_abilities, not here).
    tgt = mon("blastoise")
    normal, *_ = damage(dex, mon("machamp", ability="pressure"), tgt, "earthquake", roll=100, crit=False)
    burned = mon("machamp", ability="pressure"); burned.status = "brn"
    burn_d, *_ = damage(dex, burned, tgt, "earthquake", roll=100, crit=False)
    check("burn reduces physical dmg", burn_d < normal, (burn_d, normal))
    check("burn ~halves physical", abs(burn_d * 2 - normal) <= 4, (burn_d, normal))
    # special move unaffected by burn
    z = mon("charizard"); zb = mon("charizard"); zb.status = "brn"
    s0, *_ = damage(dex, z, tgt, "flamethrower", roll=100, crit=False)
    s1, *_ = damage(dex, zb, tgt, "flamethrower", roll=100, crit=False)
    check("burn does NOT reduce special dmg", s0 == s1, (s0, s1))


def test_paralysis_and_stages():
    p = mon("pikachu"); base_spe = p.eff_speed()
    p.status = "par"
    check("paralysis quarters speed", p.eff_speed() == base_spe // 4, (p.eff_speed(), base_spe))
    a = mon("machamp"); t = mon("blastoise")
    d0, *_ = damage(dex, a, t, "earthquake", roll=100, crit=False)
    a.boost("atk", 2)
    d2, *_ = damage(dex, a, t, "earthquake", roll=100, crit=False)
    check("+2 atk raises damage ~2x", d2 > d0 and abs(d2 - d0 * 2) <= 6, (d0, d2))


def test_crit_ignores_unfavorable_stage():
    a0 = mon("machamp"); t = mon("blastoise")
    crit0, *_ = damage(dex, a0, t, "earthquake", roll=100, crit=True)
    aneg = mon("machamp"); aneg.boost("atk", -2)
    critn, *_ = damage(dex, aneg, t, "earthquake", roll=100, crit=True)
    noncritn, *_ = damage(dex, aneg, t, "earthquake", roll=100, crit=False)
    check("crit ignores attacker's -atk stage", critn == crit0, (critn, crit0))
    check("non-crit still lowered by -atk stage", noncritn < crit0)


def test_status_immunities():
    b = Battle(dex, mon("charizard"), mon("blastoise"), log=lambda *_: None)
    check("fire immune to burn", b._status_immune(mon("charizard"), "brn"))
    check("poison immune to poison", b._status_immune(mon("gengar"), "psn"))   # gengar is poison
    check("steel immune to poison", b._status_immune(mon("metagross"), "psn") if "metagross" in dex.species else True)
    check("ice immune to freeze", b._status_immune(mon("lapras"), "frz") if "lapras" in dex.species else True)
    check("water NOT immune to burn", not b._status_immune(mon("blastoise"), "brn"))


def test_residual_damage():
    b = Battle(dex, mon("snorlax") if "snorlax" in dex.species else mon("blastoise"), mon("gengar"), log=lambda *_: None)
    p = b.left; p.status = "brn"; before = p.hp
    b._end_of_turn(p)
    check("burn residual ~ maxhp/8", before - p.hp == max(1, p.max_hp // 8), (before - p.hp, p.max_hp // 8))
    q = b.right; q.status = "tox"; q.status_counter = 1
    h0 = q.hp; b._end_of_turn(q); d1 = h0 - q.hp
    h1 = q.hp; b._end_of_turn(q); d2 = h1 - q.hp
    check("toxic escalates", d2 > d1, (d1, d2))


def test_status_battles_resolve():
    ok = 0
    for seed in range(20):
        w = Battle(dex, mon("gengar"), mon("snorlax") if "snorlax" in dex.species else mon("blastoise"),
                   seed=seed, log=lambda *_: None).run()
        if w is not None and not w.fainted:
            ok += 1
    check("20 seeded status-y battles all resolve", ok == 20, ok)


if __name__ == "__main__":
    for fn in (test_stage_multipliers, test_burn_halves_physical_only, test_paralysis_and_stages,
               test_crit_ignores_unfavorable_stage, test_status_immunities, test_residual_damage,
               test_status_battles_resolve):
        fn()
    ok = sum(1 for _, p, _ in CHECKS if p)
    for n, p, d in CHECKS:
        print(("  ✅ " if p else "  ❌ ") + n + ("" if p else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
