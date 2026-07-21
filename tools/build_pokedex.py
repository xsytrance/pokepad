#!/usr/bin/env python3
"""
Poképad — Phase 1 data pipeline (the scrape).

Pulls Gen-III mechanical data from PokéAPI into ONE normalized, versioned,
offline dataset the app bundles: data/gen3.json.

Covenant: mechanical FACTS only (base stats, types, moves, abilities, the type
chart, Gen-III learnsets, evolutions). We deliberately do NOT ship copyrighted
EXPRESSION — no Pokédex flavor text, no sprites, no genus prose. Species names
are kept only as factual identifiers for save-matching.

Notes on Gen-III fidelity:
- The physical/special split is BY TYPE in Gen III, so we store each move's
  type and let the engine derive the category (PokéAPI's damage_class is the
  modern per-move split; we keep it as `modern_class` for reference only).
- Move power/accuracy use PokéAPI's current values; moves whose values changed
  in later gens are flagged (`changed_since_gen3`) for a later accuracy pass.

Usage:
    python3 tools/build_pokedex.py            # build
    python3 tools/build_pokedex.py --verify   # rebuild-free spot checks (needs a prior build)
"""
import json, os, sys, time, urllib.request, urllib.error

API = "https://pokeapi.co/api/v2"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, ".cache")
OUT = os.path.join(HERE, "data", "gen3.json")
DATA_VERSION = "poképad-gen3-v1"

GEN3_DEX_MAX = 386                       # national dex covered by Gen-III games
GEN3_VERSION_GROUPS = {"ruby-sapphire", "emerald", "firered-leafgreen"}
GEN_ORDER = ["generation-i", "generation-ii", "generation-iii",
             "generation-iv", "generation-v", "generation-vi",
             "generation-vii", "generation-viii", "generation-ix"]
GEN3_IDX = GEN_ORDER.index("generation-iii")
# 17 Gen-III types (no fairy; drop the non-battle pseudo-types)
GEN3_TYPES = ["normal", "fire", "water", "electric", "grass", "ice", "fighting",
              "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
              "dragon", "dark", "steel"]

os.makedirs(CACHE, exist_ok=True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)


def get(path):
    """GET {API}/{path} with an on-disk JSON cache and polite retries."""
    key = path.strip("/").replace("/", "__") + ".json"
    fp = os.path.join(CACHE, key)
    if os.path.exists(fp):
        with open(fp) as f:
            return json.load(f)
    url = f"{API}/{path}"
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pokepad-builder/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            with open(fp, "w") as f:
                json.dump(data, f)
            time.sleep(0.05)             # be polite
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            wait = 1.5 * (attempt + 1)
            print(f"  ! {url} failed ({e}); retry in {wait:.1f}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"gave up on {url}")


def gen_index(name):
    try:
        return GEN_ORDER.index(name)
    except ValueError:
        return 99


def short_effect(entries):
    for e in entries:
        if e.get("language", {}).get("name") == "en":
            return e.get("short_effect") or e.get("effect")
    return None


# ── type chart ───────────────────────────────────────────────────────────────
def build_type_chart():
    chart = {}
    for t in GEN3_TYPES:
        d = get(f"type/{t}")["damage_relations"]
        row = {}
        for x in d["double_damage_to"]:
            if x["name"] in GEN3_TYPES: row[x["name"]] = 2.0
        for x in d["half_damage_to"]:
            if x["name"] in GEN3_TYPES: row[x["name"]] = 0.5
        for x in d["no_damage_to"]:
            if x["name"] in GEN3_TYPES: row[x["name"]] = 0.0
        chart[t] = row                  # only non-1.0 entries
    return chart


# ── moves ────────────────────────────────────────────────────────────────────
def build_moves():
    listing = get("move?limit=2000")["results"]
    moves = {}
    for i, ref in enumerate(listing):
        m = get(f"move/{ref['name']}")
        if gen_index(m["generation"]["name"]) > GEN3_IDX:
            continue                     # move didn't exist in Gen III
        meta = m.get("meta") or {}
        stat_changes = [{"stat": s["stat"]["name"], "change": s["change"]}
                        for s in m.get("stat_changes", [])]
        changed = any(pv for pv in m.get("past_values", []))
        moves[m["name"]] = {
            "name": m["name"],
            "type": m["type"]["name"],
            "power": m["power"],
            "accuracy": m["accuracy"],
            "pp": m["pp"],
            "priority": m["priority"],
            "modern_class": m["damage_class"]["name"],   # reference only; engine splits by type
            "target": m["target"]["name"],
            "effect_chance": m["effect_chance"],
            "ailment": (meta.get("ailment") or {}).get("name"),
            "ailment_chance": meta.get("ailment_chance"),
            "crit_rate": meta.get("crit_rate"),
            "drain": meta.get("drain"),
            "healing": meta.get("healing"),
            "flinch_chance": meta.get("flinch_chance"),
            "min_hits": meta.get("min_hits"),
            "max_hits": meta.get("max_hits"),
            "stat_changes": stat_changes,
            "short_effect": short_effect(m.get("effect_entries", [])),
            "changed_since_gen3": changed,
        }
        if (i + 1) % 100 == 0:
            print(f"  moves: {i+1}/{len(listing)} scanned, {len(moves)} kept")
    return moves


# ── abilities ────────────────────────────────────────────────────────────────
def build_abilities():
    listing = get("ability?limit=1000")["results"]
    abilities = {}
    for ref in listing:
        a = get(f"ability/{ref['name']}")
        if gen_index(a["generation"]["name"]) > GEN3_IDX:
            continue
        abilities[a["name"]] = {
            "name": a["name"],
            "short_effect": short_effect(a.get("effect_entries", [])),
        }
    return abilities


# ── species ──────────────────────────────────────────────────────────────────
def gen3_learnset(pkmn):
    """level-up / machine / tutor / egg moves available in a Gen-III version group"""
    out = {}
    for mv in pkmn["moves"]:
        name = mv["move"]["name"]
        best = None
        for d in mv["version_group_details"]:
            if d["version_group"]["name"] in GEN3_VERSION_GROUPS:
                method = d["move_learn_method"]["name"]
                lvl = d["level_learned_at"]
                # keep the lowest level-up entry; remember any method
                if best is None or (method == "level-up" and lvl and (best[0] != "level-up" or lvl < best[1])):
                    best = (method, lvl)
        if best:
            out[name] = {"method": best[0], "level": best[1]}
    return out


def build_species():
    species = {}
    for dex in range(1, GEN3_DEX_MAX + 1):
        p = get(f"pokemon/{dex}")
        s = get(f"pokemon-species/{dex}")
        stats = {x["stat"]["name"]: x["base_stat"] for x in p["stats"]}
        types = [t["type"]["name"] for t in sorted(p["types"], key=lambda z: z["slot"])]
        abils = [a["ability"]["name"] for a in p["abilities"] if not a["is_hidden"]]  # no hidden abilities in Gen III
        species[s["name"]] = {
            "dex": dex,
            "name": s["name"],
            "types": types,
            "base": {                    # canonical stat keys
                "hp": stats["hp"], "atk": stats["attack"], "def": stats["defense"],
                "spa": stats["special-attack"], "spd": stats["special-defense"],
                "spe": stats["speed"],
            },
            "abilities": abils,
            "height_dm": p["height"], "weight_hg": p["weight"],
            "gender_rate": s["gender_rate"],          # -1 genderless, else female eighths
            "capture_rate": s["capture_rate"],
            "is_legendary": s["is_legendary"],
            "is_mythical": s["is_mythical"],
            "egg_groups": [g["name"] for g in s["egg_groups"]],
            # rendering seeds (metadata, not expression):
            "shape": (s.get("shape") or {}).get("name"),
            "color": (s.get("color") or {}).get("name"),
            "learnset": gen3_learnset(p),
        }
        if dex % 50 == 0:
            print(f"  species: {dex}/{GEN3_DEX_MAX}")
    return species


# ── evolutions ───────────────────────────────────────────────────────────────
def build_evolutions(species):
    """flatten evolution chains into from->to edges with a trigger"""
    edges = []
    seen_chains = set()
    for name in list(species.keys()):
        s = get(f"pokemon-species/{species[name]['dex']}")
        chain_url = s["evolution_chain"]["url"] if s.get("evolution_chain") else None
        if not chain_url:
            continue
        cid = chain_url.rstrip("/").split("/")[-1]
        if cid in seen_chains:
            continue
        seen_chains.add(cid)
        chain = get(f"evolution-chain/{cid}")["chain"]

        def walk(node):
            base = node["species"]["name"]
            for ev in node["evolves_to"]:
                det = ev["evolution_details"][0] if ev["evolution_details"] else {}
                edges.append({
                    "from": base, "to": ev["species"]["name"],
                    "trigger": (det.get("trigger") or {}).get("name"),
                    "min_level": det.get("min_level"),
                    "item": (det.get("item") or {}).get("name") if det.get("item") else None,
                })
                walk(ev)
        walk(chain)
    # keep only edges within the Gen-III dex
    names = set(species.keys())
    return [e for e in edges if e["from"] in names and e["to"] in names]


def main():
    if "--verify" in sys.argv:
        return verify(json.load(open(OUT)))

    print("Poképad Phase-1 scrape (PokéAPI → data/gen3.json)")
    print("· type chart");   types = build_type_chart()
    print("· abilities");    abilities = build_abilities()
    print("· moves");        moves = build_moves()
    print("· species (1..386) + learnsets"); species = build_species()
    print("· evolutions");   evolutions = build_evolutions(species)

    dataset = {
        "meta": {
            "data_version": DATA_VERSION,
            "generation": 3,
            "source": "https://pokeapi.co (mechanical data only; no expression)",
            "counts": {"species": len(species), "moves": len(moves),
                       "abilities": len(abilities), "types": len(types),
                       "evolutions": len(evolutions)},
            "notes": "phys/special split is by TYPE (Gen III); modern_class is reference only. "
                     "move power/accuracy are current values; changed_since_gen3 flags a later accuracy pass.",
        },
        "types": types, "abilities": abilities, "moves": moves,
        "species": species, "evolutions": evolutions,
    }
    with open(OUT, "w") as f:
        json.dump(dataset, f, separators=(",", ":"), sort_keys=True)
    kb = os.path.getsize(OUT) // 1024
    print(f"\nwrote {OUT} ({kb} KB)")
    verify(dataset)


def verify(d):
    c = d["meta"]["counts"]
    print("\n=== spot checks ===")
    print("counts:", c)
    assert c["species"] == 386, "expected 386 species"
    assert c["types"] == 17, "expected 17 types"
    zard = d["species"]["charizard"]["base"]
    assert (zard["hp"], zard["atk"], zard["def"], zard["spa"], zard["spd"], zard["spe"]) == (78, 84, 78, 109, 85, 100), zard
    print("charizard base:", zard, "OK")
    pika = d["species"]["pikachu"]
    print(f"pikachu: types={pika['types']} shape={pika['shape']} color={pika['color']} "
          f"abilities={pika['abilities']} learnset={len(pika['learnset'])} moves")
    print("type chart water->fire:", d["types"]["water"].get("fire"), "(expect 2.0)")
    assert d["types"]["water"].get("fire") == 2.0
    print("type chart electric->ground:", d["types"]["electric"].get("ground"), "(expect 0.0)")
    assert d["types"]["electric"].get("ground") == 0.0
    fb = d["moves"].get("flamethrower")
    print("flamethrower:", {k: fb[k] for k in ("type", "power", "accuracy", "modern_class")})
    print("all spot checks passed ✅")


if __name__ == "__main__":
    main()
