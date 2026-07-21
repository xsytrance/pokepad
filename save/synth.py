"""
Synthetic Gen-III save builder — for round-tripping the parser without a real
`.sav`. Encodes a trainer + party into the real container (encryption,
substructure order by PID%24, section footers) so `gen3.parse_save` reads it
back. The on-hardware gate is Rod's real save; this validates the crypto,
checksums, layout and PID-derivations end to end.
"""
from __future__ import annotations
import struct
from . import gen3
from .gen3 import ORDERS, SECTION_SIZE, SLOT_SECTIONS, SIGNATURE, encode_name


def build_pokemon(pid, otid, internal_species, level, *, nickname="", ot_name="TRAINER",
                  ivs=None, evs=None, moves=(1, 0, 0, 0), pp=(35, 0, 0, 0),
                  held=0, friendship=70, met_level=5, ball=4, ability_bit=0):
    ivs = ivs or {k: 31 for k in ("hp", "atk", "def", "spe", "spa", "spd")}
    evs = evs or {k: 0 for k in ("hp", "atk", "def", "spe", "spa", "spd")}
    mon = bytearray(100)
    struct.pack_into("<I", mon, 0x00, pid)
    struct.pack_into("<I", mon, 0x04, otid)
    mon[0x08:0x12] = encode_name(nickname, 10)
    struct.pack_into("<H", mon, 0x12, 2)                       # language = English
    mon[0x14:0x1B] = encode_name(ot_name, 7)

    G = bytearray(12); struct.pack_into("<H", G, 0, internal_species)
    struct.pack_into("<H", G, 2, held); struct.pack_into("<I", G, 4, 0); G[9] = friendship
    A = bytearray(12)
    for i in range(4): struct.pack_into("<H", A, i * 2, moves[i]); A[8 + i] = pp[i]
    E = bytearray(12)
    for i, k in enumerate(("hp", "atk", "def", "spe", "spa", "spd")): E[i] = evs[k]
    M = bytearray(12)
    origins = (met_level & 0x7F) | (2 << 7) | ((ball & 0xF) << 11)   # game=Emerald(2)
    struct.pack_into("<H", M, 2, origins)
    iv_word = (ivs["hp"] | (ivs["atk"] << 5) | (ivs["def"] << 10) | (ivs["spe"] << 15)
               | (ivs["spa"] << 20) | (ivs["spd"] << 25) | (ability_bit << 31))
    struct.pack_into("<I", M, 4, iv_word)

    blocks = {"G": bytes(G), "A": bytes(A), "E": bytes(E), "M": bytes(M)}
    order = ORDERS[pid % 24]
    data = bytearray(b"".join(blocks[c] for c in order))
    # checksum over the 48 decrypted bytes (24 LE u16 words)
    chk = sum(struct.unpack("<24H", data)) & 0xFFFF
    struct.pack_into("<H", mon, 0x1C, chk)
    # encrypt with key = PID ^ OTID
    key = pid ^ otid
    for i in range(0, 48, 4):
        struct.pack_into("<I", data, i, struct.unpack_from("<I", data, i)[0] ^ key)
    mon[0x20:0x50] = data
    mon[0x54] = level
    struct.pack_into("<H", mon, 0x56, 100)                     # current hp (placeholder)
    struct.pack_into("<H", mon, 0x58, 100)                     # max hp
    return bytes(mon)


def _section(section_id, payload, save_index=1):
    sec = bytearray(SECTION_SIZE)
    sec[0:len(payload)] = payload
    struct.pack_into("<H", sec, 0x0FF4, section_id)
    chk = sum(struct.unpack_from(f"<{(3968)//4}I", sec, 0)) & 0xFFFFFFFF
    struct.pack_into("<H", sec, 0x0FF6, ((chk >> 16) + (chk & 0xFFFF)) & 0xFFFF)
    struct.pack_into("<I", sec, 0x0FF8, SIGNATURE)
    struct.pack_into("<I", sec, 0x0FFC, save_index)
    return bytes(sec)


def build_save(trainer, party, save_index=1):
    """trainer: dict(name,gender,tid,sid,hours,minutes). party: list of 100-byte mons."""
    s0 = bytearray(3968)
    s0[0x00:0x07] = encode_name(trainer["name"], 7)
    s0[0x08] = 1 if trainer.get("gender") == "female" else 0
    struct.pack_into("<H", s0, 0x0A, trainer["tid"])
    struct.pack_into("<H", s0, 0x0C, trainer["sid"])
    struct.pack_into("<H", s0, 0x0E, trainer.get("hours", 0))
    s0[0x10] = trainer.get("minutes", 0)
    struct.pack_into("<I", s0, 0x00AC, 0x20000)               # nonzero => Emerald

    s1 = bytearray(3968)
    s1[0x0234] = len(party)                                    # RSE team size
    for i, mon in enumerate(party):
        s1[0x0238 + i * 100: 0x0238 + (i + 1) * 100] = mon

    save = bytearray(0x20000)                                  # 128 KB
    payloads = {0: bytes(s0), 1: bytes(s1)}
    for sid in range(SLOT_SECTIONS):
        payload = payloads.get(sid, b"")
        save[sid * SECTION_SIZE:(sid + 1) * SECTION_SIZE] = _section(sid, payload, save_index)
    # slot B left zeroed (unsigned) → parser picks slot A
    return bytes(save)
