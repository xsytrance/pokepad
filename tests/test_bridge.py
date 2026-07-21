"""SaveTruth → battle bridge: a parsed party carries real level/IVs/nature/moves
into the engine and battles. Run: python3 tests/test_bridge.py"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from save.synth import build_pokemon, build_save
from save.gen3 import parse_save
from save import bridge
from sim.engine import Dex as SimDex, Battle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEX = json.load(open(os.path.join(ROOT, "data", "gen3.json")))
def internal(n): return DEX["species"][n]["gen3_index"]

CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))


def run():
    zard = build_pokemon(0x00030003, 0, internal("charizard"), 55, nickname="EMBER",
                         ivs={"hp": 31, "atk": 30, "def": 31, "spe": 31, "spa": 31, "spd": 30},
                         evs={"hp": 4, "atk": 0, "def": 0, "spe": 252, "spa": 252, "spd": 0},
                         moves=(53, 89, 0, 0))          # flamethrower(53), earthquake(89)
    blast = build_pokemon(0x11112222, 0, internal("blastoise"), 55,
                          moves=(57, 58, 0, 0))          # surf(57), ice-beam(58)
    save = build_save({"name": "ROD", "gender": "male", "tid": 0, "sid": 0}, [zard, blast])
    st = parse_save(save)
    sim = SimDex()
    team = bridge.team_from_savetruth(sim, st)

    check("team of 2 built", len(team) == 2, len(team))
    m = team[0]
    check("EMBER nickname kept", m.nickname == "EMBER", m.nickname)
    check("real level 55", m.level == 55, m.level)
    check("real IV spe 31", m.ivs["spe"] == 31, m.ivs)
    check("real moves mapped", m.moves == ["flamethrower", "earthquake"], m.moves)
    check("real nature (from PID)", m.nature == "hasty", m.nature)
    # stats reflect the real spread (252 SpA EV Charizard SpA > a 0-EV one)
    from sim.engine import Pokemon
    vanilla = Pokemon(sim, "charizard", level=55)
    check("EV-trained SpA beats vanilla", m.stats["spa"] > vanilla.stats["spa"], (m.stats["spa"], vanilla.stats["spa"]))
    w = Battle(sim, team[0], team[1], seed=4, log=lambda *_: None).run()
    check("your team battles to a result", w is not None and not w.fainted)


if __name__ == "__main__":
    run()
    ok = sum(1 for _, c, _ in CHECKS if c)
    for n, c, d in CHECKS:
        print(("  ✅ " if c else "  ❌ ") + n + ("" if c else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
