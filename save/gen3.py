"""
Poképad — Gen-III save parser → SaveTruth (READ-ONLY).

Parses Ruby/Sapphire/Emerald/FireRed/LeafGreen saves into the sacred SaveTruth
contract: trainer + party, every fact from the file. Never writes. Unknown →
None; the caller marks anything it can't verify `undetermined`.

Format (Bulbapedia "Save data structure in Generation III"): two 14-section
slots; the active slot is the one with the higher save index. Section 0 =
trainer, section 1 = team/items. Each party Pokémon is 100 bytes with a 48-byte
data block that is XOR-encrypted (key = PID ^ OTID) and whose four 12-byte
substructures {Growth, Attacks, EVs, Misc} are ordered by PID % 24. Nature,
shininess, gender and ability are derived from the PID/OTID (facts, computed).
"""
from __future__ import annotations
import json, os, struct

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gen3.json")

SECTION_SIZE = 0x1000
SLOT_SECTIONS = 14
SLOT_SIZE = SLOT_SECTIONS * SECTION_SIZE            # 0xE000
SIGNATURE = 0x08012025
# substructure orderings by PID % 24
ORDERS = ["GAEM", "GAME", "GEAM", "GEMA", "GMAE", "GMEA", "AGEM", "AGME",
          "AEGM", "AEMG", "AMGE", "AMEG", "EGAM", "EGMA", "EAGM", "EAMG",
          "EMGA", "EMAG", "MGAE", "MGEA", "MAGE", "MAEG", "MEGA", "MEAG"]
NATURES = ["hardy", "lonely", "brave", "adamant", "naughty", "bold", "docile",
           "relaxed", "impish", "lax", "timid", "hasty", "serious", "jolly",
           "naive", "modest", "mild", "quiet", "bashful", "rash", "calm",
           "gentle", "sassy", "careful", "quirky"]
BALLS = {1: "master", 2: "ultra", 3: "great", 4: "poke", 5: "safari",
         6: "net", 7: "dive", 8: "nest", 9: "repeat", 10: "timer",
         11: "luxury", 12: "premier"}
GENDER_THRESHOLD = {0: "male-only", 8: "female-only", 1: 31, 2: 63, 4: 127, 6: 191, 7: 225}

# Gen-III English character map (printable subset — enough for names)
_CHARMAP = {0x00: " ", 0xFF: ""}
for _i, _c in enumerate("0123456789"):
    _CHARMAP[0xA1 + _i] = _c
for _i in range(26):
    _CHARMAP[0xBB + _i] = chr(ord("A") + _i)
    _CHARMAP[0xD5 + _i] = chr(ord("a") + _i)
_CHARMAP.update({0xAB: "!", 0xAC: "?", 0xAD: ".", 0xAE: "-", 0xB0: "…",
                 0xB1: "“", 0xB2: "”", 0xB3: "‘", 0xB4: "’", 0xBA: "/", 0xB5: "♂", 0xB6: "♀"})
_REVMAP = {v: k for k, v in _CHARMAP.items() if v}


def decode_name(b: bytes) -> str:
    out = []
    for x in b:
        if x == 0xFF:
            break
        out.append(_CHARMAP.get(x, "?"))
    return "".join(out)


def encode_name(s: str, length: int) -> bytes:
    b = bytearray([0xFF] * length)
    for i, ch in enumerate(s[:length]):
        b[i] = _REVMAP.get(ch, 0x00)
    return bytes(b)


def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]


class Dex:
    def __init__(self, path=DATA):
        d = json.load(open(path))
        self.species = d["species"]
        self.i2n = d["internal_to_national"]

    def species_by_internal(self, idx: int):
        name = self.i2n.get(str(idx))
        return name, self.species.get(name) if name else None


def _read_slot(data: bytes, base: int):
    """return (save_index, {section_id: section_bytes}) or None if unsigned."""
    sections, save_index = {}, None
    for i in range(SLOT_SECTIONS):
        sec = data[base + i * SECTION_SIZE: base + (i + 1) * SECTION_SIZE]
        if len(sec) < SECTION_SIZE:
            return None
        if _u32(sec, 0x0FF8) != SIGNATURE:
            continue
        sid = _u16(sec, 0x0FF4)
        sections[sid] = sec
        save_index = _u32(sec, 0x0FFC)
    if not sections:
        return None
    return save_index, sections


def _pick_active(data: bytes):
    a = _read_slot(data, 0)
    b = _read_slot(data, SLOT_SIZE)
    cands = [x for x in (a, b) if x]
    if not cands:
        raise ValueError("no valid Gen-III save slot found (bad/again container?)")
    # active = higher save index (treat 0xFFFFFFFF as unused)
    def idx(x): return -1 if x[0] in (None, 0xFFFFFFFF) else x[0]
    return max(cands, key=idx)[1]


def _game_from_code(section0: bytes) -> str:
    code = _u32(section0, 0x00AC)
    return {0: "RS", 1: "FRLG"}.get(code, "Emerald")


def decode_pokemon(dex: Dex, mon: bytes) -> dict | None:
    pid = _u32(mon, 0x00)
    otid = _u32(mon, 0x04)
    if pid == 0 and otid == 0:
        return None                                   # empty slot
    nickname = decode_name(mon[0x08:0x12])
    ot_name = decode_name(mon[0x14:0x1B])
    # decrypt the 48-byte data block
    key = pid ^ otid
    enc = bytearray(mon[0x20:0x50])
    for i in range(0, 48, 4):
        w = _u32(enc, i) ^ key
        struct.pack_into("<I", enc, i, w)
    order = ORDERS[pid % 24]
    blocks = {order[p]: bytes(enc[p * 12:(p + 1) * 12]) for p in range(4)}
    G, A, E, M = blocks["G"], blocks["A"], blocks["E"], blocks["M"]

    internal = _u16(G, 0)
    sp_name, sp = dex.species_by_internal(internal)
    held = _u16(G, 2)
    experience = _u32(G, 4)
    friendship = G[9]
    moves = [_u16(A, 0), _u16(A, 2), _u16(A, 4), _u16(A, 6)]
    pp = [A[8], A[9], A[10], A[11]]
    evs = {"hp": E[0], "atk": E[1], "def": E[2], "spe": E[3], "spa": E[4], "spd": E[5]}
    origins = _u16(M, 2)
    met_level = origins & 0x7F
    ball = (origins >> 11) & 0xF
    iv_word = _u32(M, 4)
    ivs = {"hp": iv_word & 31, "atk": (iv_word >> 5) & 31, "def": (iv_word >> 10) & 31,
           "spe": (iv_word >> 15) & 31, "spa": (iv_word >> 20) & 31, "spd": (iv_word >> 25) & 31}
    is_egg = bool((iv_word >> 30) & 1)
    ability_bit = (iv_word >> 31) & 1

    nature = NATURES[pid % 25]
    tid_low, tid_high = otid & 0xFFFF, otid >> 16
    pid_low, pid_high = pid & 0xFFFF, pid >> 16
    shiny = (tid_low ^ tid_high ^ pid_low ^ pid_high) < 8

    ability = None
    if sp and sp.get("abilities"):
        ability = sp["abilities"][ability_bit] if ability_bit < len(sp["abilities"]) else sp["abilities"][0]

    gender = None
    if sp:
        rate = sp.get("gender_rate", -1)
        thr = GENDER_THRESHOLD.get(rate)
        if rate == -1:
            gender = "genderless"
        elif thr == "male-only":
            gender = "male"
        elif thr == "female-only":
            gender = "female"
        elif isinstance(thr, int):
            gender = "female" if (pid & 0xFF) < thr else "male"

    # party-only stat block (100-byte layout) — level lives at 0x54
    level = mon[0x54] if len(mon) >= 0x55 else None
    cur_hp = _u16(mon, 0x56) if len(mon) >= 0x58 else None

    return {
        "species": sp_name, "internal_index": internal,
        "nickname": nickname or (sp_name.title() if sp_name else None),
        "level": level, "current_hp": cur_hp,
        "nature": nature, "ability": ability, "gender": gender, "shiny": shiny,
        "is_egg": is_egg, "friendship": friendship, "experience": experience,
        "ivs": ivs, "evs": evs,
        "held_item_index": held or None,
        "moves_index": [m for m in moves if m], "pp": pp,
        "ot_name": ot_name, "ot_id": tid_low, "secret_id": tid_high,
        "met_level": met_level, "poke_ball": BALLS.get(ball, ball or None),
        "pid": pid,
    }


def parse_save(data: bytes) -> dict:
    """bytes of a .sav -> SaveTruth (read-only)."""
    if len(data) < SLOT_SIZE:
        raise ValueError(f"save too small ({len(data)} bytes)")
    dex = Dex()
    sections = _pick_active(data)
    if 0 not in sections or 1 not in sections:
        raise ValueError("active slot missing trainer/team sections")
    s0, s1 = sections[0], sections[1]

    game = _game_from_code(s0)
    trainer = {
        "name": decode_name(s0[0x00:0x07]),
        "gender": "female" if s0[0x08] else "male",
        "trainer_id": _u16(s0, 0x0A), "secret_id": _u16(s0, 0x0C),
        "playtime_hours": _u16(s0, 0x0E), "playtime_minutes": s0[0x10],
        "game": game,
    }
    # team offsets differ FRLG vs RSE
    if game == "FRLG":
        size_off, team_off = 0x0034, 0x0038
    else:
        size_off, team_off = 0x0234, 0x0238
    team_size = min(s1[size_off], 6)
    party = []
    for i in range(team_size):
        mon = s1[team_off + i * 100: team_off + (i + 1) * 100]
        dec = decode_pokemon(dex, mon)
        if dec:
            party.append(dec)

    return {
        "schema_version": "pokepad-gen3-savetruth-v1",
        "source": {"game": game, "size_bytes": len(data)},
        "trainer": trainer,
        "party": party,
    }


if __name__ == "__main__":
    import sys
    st = parse_save(open(sys.argv[1], "rb").read())
    print(json.dumps(st, indent=2, default=str))
