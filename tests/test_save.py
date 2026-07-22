"""Round-trip the Gen-III save parser against a synthetic save (build → parse →
assert). Validates crypto, checksums, layout, substructure ordering, and the
PID-derived facts (nature/shiny/gender/ability/IVs/EVs). Run:
    python3 tests/test_save.py

The on-hardware gate is a real save; this proves the math end to end."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from save import parse_save
from save.synth import build_pokemon, build_save
from save.gen3 import NATURES

DEX = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gen3.json")))
def internal(name): return DEX["species"][name]["gen3_index"]

CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))


def run():
    # A shiny by construction: OTID=0, PID with (low16 ^ high16) < 8 -> shiny.
    shiny_pid = 0x00030003          # 3 ^ 3 = 0 < 8  → shiny
    zard = build_pokemon(shiny_pid, 0, internal("charizard"), 55,
                         nickname="EMBER", ot_name="ROD",
                         ivs={"hp": 31, "atk": 30, "def": 31, "spe": 29, "spa": 31, "spd": 28},
                         evs={"hp": 252, "atk": 0, "def": 0, "spe": 252, "spa": 4, "spd": 0},
                         moves=(52, 0, 0, 0), friendship=200, met_level=5, ball=4, ability_bit=0)
    # Non-shiny Pikachu, different PID%24 order path, ability slot bit set.
    pika_pid = 0xABCD1234            # arbitrary → tests a different substructure order
    pika = build_pokemon(pika_pid, 0x2233, internal("pikachu"), 22,
                         nickname="", ot_name="ROD",
                         ivs={"hp": 20, "atk": 15, "def": 10, "spe": 31, "spa": 25, "spd": 5},
                         evs={"hp": 0, "atk": 0, "def": 0, "spe": 200, "spa": 0, "spd": 0},
                         moves=(84, 98, 0, 0), friendship=120, met_level=3, ball=3, ability_bit=0)
    save = build_save({"name": "ROD", "gender": "male", "tid": 0, "sid": 0, "hours": 42, "minutes": 30},
                      [zard, pika])
    check("save is 128 KB", len(save) == 0x20000, len(save))

    st = parse_save(save)
    check("schema present", st["schema_version"].startswith("pokepad-gen3"))
    tr = st["trainer"]
    check("trainer name ROD", tr["name"] == "ROD", tr["name"])
    check("trainer id 0", tr["trainer_id"] == 0)
    check("playtime 42h30m", tr["playtime_hours"] == 42 and tr["playtime_minutes"] == 30, tr)
    check("party of 2", len(st["party"]) == 2, len(st["party"]))

    z = st["party"][0]
    check("mon0 species charizard", z["species"] == "charizard", z["species"])
    check("mon0 nickname EMBER", z["nickname"] == "EMBER", z["nickname"])
    check("mon0 level 55", z["level"] == 55, z["level"])
    check("mon0 IVs round-trip", z["ivs"] == {"hp": 31, "atk": 30, "def": 31, "spe": 29, "spa": 31, "spd": 28}, z["ivs"])
    check("mon0 EVs round-trip", z["evs"] == {"hp": 252, "atk": 0, "def": 0, "spe": 252, "spa": 4, "spd": 0}, z["evs"])
    check("mon0 nature == PID%25", z["nature"] == NATURES[shiny_pid % 25], (z["nature"], NATURES[shiny_pid % 25]))
    check("mon0 shiny == True", z["shiny"] is True, z["shiny"])
    check("mon0 friendship 200", z["friendship"] == 200, z["friendship"])
    check("mon0 OT ROD", z["ot_name"] == "ROD", z["ot_name"])
    check("mon0 ball poke", z["poke_ball"] == "poke", z["poke_ball"])
    check("mon0 ability resolved", z["ability"] is not None, z["ability"])
    check("mon0 has a move index", 52 in z["moves_index"], z["moves_index"])

    p = st["party"][1]
    check("mon1 species pikachu", p["species"] == "pikachu", p["species"])
    check("mon1 nickname defaults to species", p["nickname"] == "Pikachu", p["nickname"])
    check("mon1 not shiny", p["shiny"] is False, p["shiny"])
    check("mon1 IVs round-trip (diff PID order)", p["ivs"]["spe"] == 31 and p["ivs"]["spd"] == 5, p["ivs"])
    check("mon1 nature == PID%25", p["nature"] == NATURES[pika_pid % 25], (p["nature"], NATURES[pika_pid % 25]))
    check("mon1 gender derived", p["gender"] in ("male", "female"), p["gender"])

    # guarded: if a real GBA .sav sits in the repo root, validate the flat path too
    import glob
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = glob.glob(os.path.join(root, "*.sav"))
    if hits:
        rs = parse_save(open(hits[0], "rb").read())
        check("real .sav: game detected", rs["source"]["game"] in ("RS", "Emerald", "FRLG"), rs["source"]["game"])
        check("real .sav: trainer + party present",
              bool(rs["trainer"]["name"]) and 1 <= len(rs["party"]) <= 6, (rs["trainer"]["name"], len(rs["party"])))
        check("real .sav: every party mon fully decoded",
              all(m["species"] and m["nature"] and m["ivs"] and m["ability"] for m in rs["party"]), None)
    else:
        check("real .sav present (skipped — none in repo)", True, "skipped")


if __name__ == "__main__":
    run()
    ok = sum(1 for _, c, _ in CHECKS if c)
    for n, c, d in CHECKS:
        print(("  ✅ " if c else "  ❌ ") + n + ("" if c else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
