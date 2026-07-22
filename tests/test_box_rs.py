"""Pokémon Box RS (.gci) reader. A synthetic .gci fixture makes this CI-safe
(no private save committed); if a real .gci sits in the repo root it also runs a
guarded check against it. Run: python3 tests/test_box_rs.py"""
import os, sys, json, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from save.box_rs import parse_gci
from save.synth import build_pokemon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEXJ = {n: v["gen3_index"] for n, v in json.load(open(os.path.join(ROOT, "data", "gen3.json")))["species"].items()}
CHECKS = []
def check(n, c, d=""): CHECKS.append((n, bool(c), d))


def _fake_gci():
    """64-byte GCI header + a few boxed mon (80-byte slices) scattered in blocks."""
    buf = bytearray(64) + bytearray(0x4000)
    buf[0:4] = b"GPXP"
    # shiny needs (TIDlo^TIDhi^PIDlo^PIDhi) < 8; OTID must be nonzero (0 = empty slot)
    mons = {
        0x400: build_pokemon(0x00050005, 0x00010001, DEXJ["gyarados"], 50, nickname="SEADRAKE")[0:0x50],
        0x1200: build_pokemon(0xABCD1234, 0x00002233, DEXJ["dragonite"], 55, nickname="DRACO")[0:0x50],
        0x2800: build_pokemon(0x0BADF00D, 0x00001111, DEXJ["mewtwo"], 70, nickname="")[0:0x50],
    }
    for off, mon in mons.items():
        buf[off:off + 0x50] = mon
    return bytes(buf)


def test_synthetic_gci():
    st = parse_gci(_fake_gci())
    check("code GPXP", st["source"]["code"] == "GPXP", st["source"]["code"])
    check("found 3 boxed mon", st["counts"]["pokemon"] == 3, st["counts"])
    names = {m["species"] for m in st["box"]}
    check("gyarados/dragonite/mewtwo parsed", names == {"gyarados", "dragonite", "mewtwo"}, names)
    seadrake = next(m for m in st["box"] if m["species"] == "gyarados")
    check("nickname SEADRAKE", seadrake["nickname"] == "SEADRAKE", seadrake["nickname"])
    check("SEADRAKE shiny (PID/OTID derived)", seadrake["shiny"] is True, seadrake["shiny"])
    check("garbage (all-zero blocks) not counted", st["counts"]["pokemon"] == 3)


def test_real_gci_if_present():
    hits = glob.glob(os.path.join(ROOT, "*.gci"))
    if not hits:
        check("real .gci present (skipped — none in repo)", True, "skipped")
        return
    st = parse_gci(open(hits[0], "rb").read())
    check("real save: 600+ Pokémon parsed", st["counts"]["pokemon"] > 600, st["counts"])
    check("real save: 300+ species (near living dex)", st["counts"]["species"] > 300, st["counts"])
    check("real save: a trainer name resolved", bool(st["trainer"]["name"]), st["trainer"])


if __name__ == "__main__":
    for fn in (test_synthetic_gci, test_real_gci_if_present):
        fn()
    ok = sum(1 for _, c, _ in CHECKS if c)
    for n, c, d in CHECKS:
        print(("  ✅ " if c else "  ❌ ") + n + ("" if c else f"   got: {d}"))
    print(f"\n{ok}/{len(CHECKS)} checks passed")
    sys.exit(0 if ok == len(CHECKS) else 1)
