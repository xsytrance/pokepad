"""Dependency-free verification for the reference engine (run: python3 tests/test_engine.py).

Validated against KNOWN references (not just self-consistency): the Gen-III stat
formula (Mewtwo's canonical Lv100 Speed), the type chart, dual-type products,
and battle resolution.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Dex, Pokemon, Battle, damage, nature_mod

dex = Dex()
CHECKS = []
def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))


def test_stat_formula():
    zard = Pokemon(dex, "charizard", level=50)          # IV31 EV0 neutral
    check("charizard Lv50 HP == 153", zard.max_hp == 153, zard.max_hp)
    check("charizard Lv50 Spe == 120", zard.stats["spe"] == 120, zard.stats["spe"])
    # Mewtwo Lv100 neutral: 0 EV Speed = 296, 252 EV Speed = 359 (canonical)
    m0 = Pokemon(dex, "mewtwo", level=100)
    check("mewtwo Lv100 0EV Spe == 296", m0.stats["spe"] == 296, m0.stats["spe"])
    m252 = Pokemon(dex, "mewtwo", level=100, evs={"hp": 0, "atk": 0, "def": 0, "spa": 0, "spd": 0, "spe": 252})
    check("mewtwo Lv100 252EV Spe == 359", m252.stats["spe"] == 359, m252.stats["spe"])


def test_natures():
    check("adamant boosts atk", nature_mod("adamant", "atk") == 1.1)
    check("adamant lowers spa", nature_mod("adamant", "spa") == 0.9)
    check("hardy neutral", nature_mod("hardy", "atk") == 1.0)
    ada = Pokemon(dex, "machamp", level=50, nature="adamant")
    neu = Pokemon(dex, "machamp", level=50, nature="hardy")
    check("adamant machamp atk > neutral", ada.stats["atk"] > neu.stats["atk"], (ada.stats["atk"], neu.stats["atk"]))


def test_type_chart():
    check("water->fire == 2", dex.type_eff("water", ["fire"]) == 2.0)
    check("fire->water == 0.5", dex.type_eff("fire", ["water"]) == 0.5)
    check("electric->ground == 0", dex.type_eff("electric", ["ground"]) == 0.0)
    check("normal->ghost == 0", dex.type_eff("normal", ["ghost"]) == 0.0)
    # dual-type product: Charizard (fire/flying) is 4x weak to rock
    check("rock->fire/flying == 4", dex.type_eff("rock", ["fire", "flying"]) == 4.0,
          dex.type_eff("rock", ["fire", "flying"]))


def test_damage_scaling():
    atk = Pokemon(dex, "venusaur", level=50)      # grass
    fire_def = Pokemon(dex, "charizard", level=50)  # fire/flying — grass resisted
    water_def = Pokemon(dex, "blastoise", level=50)  # water — grass super-effective
    se, _, _, _ = damage(dex, atk, water_def, "razor-leaf", roll=100, crit=False)
    rs, _, _, _ = damage(dex, atk, fire_def, "razor-leaf", roll=100, crit=False)
    check("super-effective > resisted (same move)", se > rs, (se, rs))
    check("damage is positive", se > 0)
    imm, eff, _, kind = damage(dex, atk, Pokemon(dex, "gengar", level=50), "earthquake", roll=100, crit=False) \
        if "earthquake" in atk.moves else (None, None, None, None)
    # immunity path (ground vs flying) — use a guaranteed immune combo directly:
    ch = Pokemon(dex, "charizard", level=50)  # flying -> immune to ground
    d2, eff2, _, kind2 = damage(dex, Pokemon(dex, "machamp", level=50), ch, "earthquake", roll=100, crit=False)
    check("ground vs flying == 0 (immune)", d2 == 0 and eff2 == 0.0, (d2, eff2))


def test_moveset_and_battle():
    for sp in ("charizard", "pikachu", "rayquaza", "gengar", "wailord"):
        ms = dex.best_moveset(sp)
        check(f"{sp} has a moveset", len(ms) >= 1 and all(m in dex.moves for m in ms), ms)
    w = Battle(dex, Pokemon(dex, "charizard", level=50), Pokemon(dex, "blastoise", level=50),
               seed=7, log=lambda *_: None).run()
    check("battle resolves with a winner", w is not None and w.fainted is False)


def test_dataset_integrity():
    d = dex.d
    check("386 species", len(d["species"]) == 386, len(d["species"]))
    check("17 types", len(d["types"]) == 17)
    bad = [s for s, v in d["species"].items() if len(v["types"]) not in (1, 2) or not v["base"]]
    check("every species has 1-2 types + base stats", not bad, bad[:5])
    # learnset moves must exist in the move table
    missing = set()
    for s, v in d["species"].items():
        for mv in v["learnset"]:
            if mv not in d["moves"]:
                missing.add(mv)
    check("all learnset moves exist in move table", not missing, list(missing)[:8])


if __name__ == "__main__":
    for fn in (test_stat_formula, test_natures, test_type_chart, test_damage_scaling,
               test_moveset_and_battle, test_dataset_integrity):
        fn()
    ok = sum(1 for _, p, _ in CHECKS if p)
    for name, passed, detail in CHECKS:
        print(("  ✅ " if passed else "  ❌ ") + name + ("" if passed else f"   got: {detail}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
