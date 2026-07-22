"""
Export a cross-engine fixture: Python (the reference spec) computes expected
values; the Kotlin on-device engine must reproduce them bit-for-bit. This is the
"one rule-set, two engines, one gate" verification.

Writes fixtures/crossgate.tsv with four record kinds:
  CHART <atkType> <defType> <mult>              — the type chart (non-1.0 cells)
  STAT  <base> <iv> <ev> <level> <isHp> <natMul> <expected>
  EFF   <moveType> <defTypesCSV> <expected>
  DMG   <level> <power> <atk> <def> <atkTypesCSV> <moveType> <defTypesCSV> <phys> <roll> <crit> <expected>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.engine import Dex, Pokemon, damage, is_physical, stage_mult  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dex = Dex()
rows = []


def stat_calc(base, iv, ev, level, is_hp, nat):
    inner = (2 * base + iv + ev // 4) * level // 100
    return inner + level + 10 if is_hp else int((inner + 5) * nat)


# 1) type chart
for atk, row in dex.chart.items():
    for d, mult in row.items():
        rows.append(f"CHART\t{atk}\t{d}\t{mult}")

# 2) stat formula cases
for base in (35, 78, 100, 135):
    for iv in (0, 31):
        for ev in (0, 252):
            for level in (50, 100):
                for is_hp in (0, 1):
                    for nat in (1.0, 1.1, 0.9):
                        if is_hp and nat != 1.0:
                            continue                       # HP ignores nature
                        exp = stat_calc(base, iv, ev, level, is_hp, nat)
                        rows.append(f"STAT\t{base}\t{iv}\t{ev}\t{level}\t{is_hp}\t{nat}\t{exp}")

# 3) type-effectiveness cases
eff_cases = [("water", ["fire"]), ("fire", ["water"]), ("electric", ["ground"]),
             ("normal", ["ghost"]), ("rock", ["fire", "flying"]), ("ice", ["grass"]),
             ("ground", ["steel"]), ("ghost", ["normal"]), ("grass", ["water", "ground"]),
             ("dragon", ["dragon"]), ("psychic", ["dark"]), ("fighting", ["ghost"]),
             ("bug", ["psychic"]), ("dark", ["steel"]), ("ice", ["dragon", "flying"])]
for mt, dts in eff_cases:
    exp = dex.type_eff(mt, dts)
    rows.append(f"EFF\t{mt}\t{','.join(dts)}\t{exp}")

# 4) damage cases (inert ability so it's the pure formula)
pairs = [("charizard", "blastoise", "flamethrower"), ("blastoise", "charizard", "surf"),
         ("venusaur", "blastoise", "razor-leaf"), ("venusaur", "charizard", "razor-leaf"),
         ("machamp", "blastoise", "earthquake"), ("alakazam", "machamp", "psychic"),
         ("gengar", "alakazam", "shadow-ball"), ("gyarados", "charizard", "surf"),
         ("pikachu", "gyarados", "thunderbolt"), ("snorlax", "gengar", "body-slam")]
for a, d, mv in pairs:
    if mv not in dex.moves:
        continue
    atk = Pokemon(dex, a, level=50, ability="pressure")
    dfn = Pokemon(dex, d, level=50, ability="pressure")
    phys = is_physical(dex.moves[mv]["type"])
    A = atk.stats["atk"] if phys else atk.stats["spa"]
    D = dfn.stats["def"] if phys else dfn.stats["spd"]
    mt = dex.moves[mv]["type"]; power = dex.moves[mv]["power"]
    for roll in (85, 93, 100):
        for crit in (0, 1):
            dmg, eff, cr, kind = damage(dex, atk, dfn, mv, roll=roll, crit=bool(crit))
            rows.append(f"DMG\t50\t{power}\t{A}\t{D}\t{','.join(atk.types)}\t{mt}\t"
                        f"{','.join(dfn.types)}\t{1 if phys else 0}\t{roll}\t{crit}\t{dmg}")

os.makedirs(os.path.join(ROOT, "fixtures"), exist_ok=True)
out = os.path.join(ROOT, "fixtures", "crossgate.tsv")
open(out, "w").write("\n".join(rows) + "\n")
n = {k: sum(1 for r in rows if r.startswith(k)) for k in ("CHART", "STAT", "EFF", "DMG")}
print(f"wrote {out}: {n}  ({len(rows)} rows)")
