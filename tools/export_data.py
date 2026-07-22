"""Export the dataset in a compact TSV form the standalone Kotlin engine reads
(no JSON dep). Writes data/gen3_species.tsv and data/gen3_moves.tsv. The type
chart already ships in fixtures/crossgate.tsv (CHART rows)."""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "data", "gen3.json")))

sp_rows = []
for name, s in d["species"].items():
    t = s["types"]; b = s["base"]; ab = s["abilities"]
    sp_rows.append("\t".join([name, t[0], t[1] if len(t) > 1 else "",
                              str(b["hp"]), str(b["atk"]), str(b["def"]),
                              str(b["spa"]), str(b["spd"]), str(b["spe"]),
                              ab[0] if ab else "", ab[1] if len(ab) > 1 else "",
                              s.get("shape") or "", s.get("color") or ""]))
open(os.path.join(ROOT, "data", "gen3_species.tsv"), "w").write("\n".join(sp_rows) + "\n")

mv_rows = []
for name, m in d["moves"].items():
    sc = ";".join(f'{c["stat"]}:{c["change"]}' for c in m.get("stat_changes", []))
    mv_rows.append("\t".join([
        name, m["type"], str(m["power"] or 0), str(m["accuracy"] if m["accuracy"] is not None else -1),
        str(m["pp"] or 0), str(m["priority"] or 0), m.get("ailment") or "none",
        str(m.get("ailment_chance") or 0), str(m.get("flinch_chance") or 0),
        str(m.get("drain") or 0), str(m.get("healing") or 0),
        str(m.get("min_hits") or 0), str(m.get("max_hits") or 0), sc, m.get("target") or "selected-pokemon"]))
open(os.path.join(ROOT, "data", "gen3_moves.tsv"), "w").write("\n".join(mv_rows) + "\n")

ch_rows = [f"{atk}\t{dfn}\t{mult}" for atk, row in d["types"].items() for dfn, mult in row.items()]
open(os.path.join(ROOT, "data", "gen3_typechart.tsv"), "w").write("\n".join(ch_rows) + "\n")

print(f"wrote data/gen3_species.tsv ({len(sp_rows)}) + data/gen3_moves.tsv ({len(mv_rows)}) "
      f"+ data/gen3_typechart.tsv ({len(ch_rows)})")
