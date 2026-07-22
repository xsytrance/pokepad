"""Full-team (6v6) battles + switching, and battling a team parsed from a save.
Run: python3 tests/test_team.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Dex, Pokemon, Battle
from save.synth import build_pokemon, build_save
from save.gen3 import parse_save
from save import bridge

dex = Dex()
CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))
def team(*names): return [Pokemon(dex, s, level=50) for s in names]


def test_6v6_resolves_and_switches():
    A = team("charizard", "blastoise", "venusaur", "pikachu", "alakazam", "gengar")
    B = team("gyarados", "machamp", "lapras", "arcanine", "gengar", "snorlax")
    resolved = 0
    for seed in range(20):
        a = team("charizard", "blastoise", "venusaur", "pikachu", "alakazam", "gengar")
        b = team("gyarados", "machamp", "lapras", "arcanine", "gengar", "snorlax")
        w = Battle(dex, a, b, seed=seed, log=lambda *_: None).run()
        if w is not None and not w.fainted:
            resolved += 1
    check("20 6v6 battles resolve with a live winner", resolved == 20, resolved)


def test_winner_side_has_survivors_loser_wiped():
    a = team("alakazam", "gengar", "charizard")
    b = team("machamp", "snorlax", "blastoise")
    bt = Battle(dex, a, b, seed=3, log=lambda *_: None)
    w = bt.run()
    la = bt._side_alive(bt.ls); ra = bt._side_alive(bt.rs)
    check("exactly one side survives", la != ra, (la, ra))
    check("winner is on the surviving side", (w in (bt.ls if la else bt.rs)), w and w.name)


def test_best_switch_prefers_better_matchup():
    # left team leads with a bad Ground answer; on faint should send the best matchup
    bt = Battle(dex, team("pikachu", "blastoise", "venusaur"), team("machamp"), log=lambda *_: None)
    foe = bt.right
    idx = bt._best_switch(bt.ls, foe)
    check("best_switch returns an alive index", 0 <= idx < 3 and not bt.ls[idx].fainted, idx)


def test_full_team_from_save_battles():
    # a 3-mon saved party → team → battle
    mons = [
        build_pokemon(0x00030003, 0, DEXJ["charizard"], 50, nickname="EMBER", moves=(53, 89, 0, 0)),
        build_pokemon(0x11112222, 0, DEXJ["blastoise"], 50, moves=(57, 58, 0, 0)),
        build_pokemon(0x33334444, 0, DEXJ["venusaur"], 50, moves=(75, 92, 0, 0)),
    ]
    save = build_save({"name": "ROD", "gender": "male", "tid": 0, "sid": 0}, mons)
    st = parse_save(save)
    my_team = bridge.team_from_savetruth(dex, st)
    check("parsed a 3-mon team", len(my_team) == 3, len(my_team))
    check("first mon is EMBER", my_team[0].nickname == "EMBER", my_team[0].nickname)
    foe = team("gyarados", "machamp", "gengar")
    w = Battle(dex, my_team, foe, seed=1, log=lambda *_: None).run()
    check("your saved team battles to a result", w is not None)


import json
DEXJ = {n: v["gen3_index"] for n, v in
        json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gen3.json")))["species"].items()}


if __name__ == "__main__":
    for fn in (test_6v6_resolves_and_switches, test_winner_side_has_survivors_loser_wiped,
               test_best_switch_prefers_better_matchup, test_full_team_from_save_battles):
        fn()
    ok = sum(1 for _, c, _ in CHECKS if c)
    for n, c, d in CHECKS:
        print(("  ✅ " if c else "  ❌ ") + n + ("" if c else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
