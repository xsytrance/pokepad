"""SaveTruth → battle. Turns a parsed party entry into an engine Pokémon,
carrying the REAL level / IVs / EVs / nature / moves from the save. This is the
seam where "your actual mon" enters the sim — facts sacred."""
from __future__ import annotations
from sim.engine import Pokemon


def to_battle_mon(sim_dex, entry: dict) -> Pokemon:
    i2n = sim_dex.d["move_index_to_name"]
    names = [i2n[str(mi)] for mi in entry.get("moves_index", [])
             if str(mi) in i2n and i2n[str(mi)] in sim_dex.moves]
    has_damage = any((sim_dex.moves[n]["power"] or 0) > 0 for n in names)
    moves = names if has_damage else sim_dex.best_moveset(entry["species"])
    return Pokemon(
        sim_dex, entry["species"], level=entry.get("level") or 50,
        ivs=entry["ivs"], evs=entry["evs"], nature=entry["nature"],
        moves=moves, nickname=entry.get("nickname"),
    )


def team_from_savetruth(sim_dex, savetruth: dict) -> list[Pokemon]:
    return [to_battle_mon(sim_dex, e) for e in savetruth["party"] if e.get("species")]
