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
from sim.engine import Dex, Pokemon, damage, is_physical, stage_mult, acc_mult  # noqa

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

# 5) stat/accuracy stage multipliers (compared as int(1000*mult) to dodge float formatting)
for n in range(-6, 7):
    rows.append(f"STAGE\t{n}\t{int(1000 * stage_mult(n))}\t{int(1000 * acc_mult(n))}")

# 6) status math (residual, toxic escalation, paralysis speed)
for hp in (100, 153, 235, 267):
    rows.append(f"RES\t{hp}\t{max(1, hp // 8)}")
    for c in (1, 2, 3, 4):
        rows.append(f"TOX\t{hp}\t{c}\t{max(1, hp * c // 16)}")
for spe in (50, 90, 120, 155):
    rows.append(f"PARA\t{spe}\t{spe // 4}")

# 7) stage/burn/crit-aware damage
stage_cases = [("machamp", "blastoise", "earthquake", 2, 0, 0), ("machamp", "blastoise", "earthquake", -2, 0, 0),
               ("machamp", "blastoise", "earthquake", 0, 2, 0), ("machamp", "blastoise", "earthquake", 0, -2, 0),
               ("machamp", "blastoise", "body-slam", 0, 0, 1), ("charizard", "blastoise", "flamethrower", 4, 0, 0),
               ("charizard", "venusaur", "flamethrower", 0, -1, 0), ("alakazam", "machamp", "psychic", 2, 2, 0)]
for a, d, mv, ast, dst, burn in stage_cases:
    if mv not in dex.moves:
        continue
    atk = Pokemon(dex, a, level=50, ability="pressure")
    dfn = Pokemon(dex, d, level=50, ability="pressure")
    phys = is_physical(dex.moves[mv]["type"])
    atk.stages["atk" if phys else "spa"] = ast
    dfn.stages["def" if phys else "spd"] = dst
    if burn:
        atk.status = "brn"
    baseA = atk.stats["atk"] if phys else atk.stats["spa"]
    baseD = dfn.stats["def"] if phys else dfn.stats["spd"]
    mt = dex.moves[mv]["type"]; power = dex.moves[mv]["power"]
    for roll in (85, 100):
        for crit in (0, 1):
            dmg, _, _, _ = damage(dex, atk, dfn, mv, roll=roll, crit=bool(crit))
            rows.append(f"DMGX\t50\t{power}\t{baseA}\t{baseD}\t{ast}\t{dst}\t{burn}\t{1 if phys else 0}\t"
                        f"{','.join(atk.types)}\t{mt}\t{','.join(dfn.types)}\t{roll}\t{crit}\t{dmg}")

os.makedirs(os.path.join(ROOT, "fixtures"), exist_ok=True)
out = os.path.join(ROOT, "fixtures", "crossgate.tsv")
open(out, "w").write("\n".join(rows) + "\n")
n = {k: sum(1 for r in rows if r.split("\t", 1)[0] == k)
     for k in ("CHART", "STAT", "EFF", "DMG", "STAGE", "RES", "TOX", "PARA", "DMGX")}
print(f"wrote {out}: {n}  ({len(rows)} rows)")
