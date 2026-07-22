"""
Poképad — Pokémon Box: Ruby & Sapphire (.gci) reader → SaveTruth (READ-ONLY).

Pokémon Box (GameCube, game code GPXP) stores GBA Pokémon in the *standard*
Gen-III encrypted format, so the same decode as `gen3.py` works. Rather than
reverse the whole GameCube save/box container, we **scan** the file for slots
whose 48-byte data block checksums correctly after decryption (a strong
signature), then filter to real species and dedupe (Box keeps backup copies).
Validated against a real save: 676 Pokémon / ~384 species, custom nicknames,
shininess — the decryption/derivation logic matches a genuine game dump.

Read-only. This never writes the save.
"""
from __future__ import annotations
import struct
from collections import Counter
from .gen3 import Dex, decode_pokemon

BOX_MON = 0x50   # boxed Pokémon are 80 bytes (no party stat block)


def _checksum_ok(b: bytes, off: int) -> bool:
    if off + BOX_MON > len(b):
        return False
    pid = struct.unpack_from("<I", b, off)[0]
    otid = struct.unpack_from("<I", b, off + 4)[0]
    if pid == 0 or otid == 0:
        return False
    stored = struct.unpack_from("<H", b, off + 0x1C)[0]
    key = pid ^ otid
    dec = bytearray(b[off + 0x20:off + 0x50])
    for i in range(0, 48, 4):
        struct.pack_into("<I", dec, i, struct.unpack_from("<I", dec, i)[0] ^ key)
    return (sum(struct.unpack("<24H", dec)) & 0xFFFF) == stored and any(dec)


def parse_gci(data: bytes) -> dict:
    """.gci bytes → SaveTruth with a `box` (the whole collection)."""
    dex = Dex()
    header_game = data[0:4].decode("ascii", "replace")
    seen, box = set(), []
    for off in range(0, len(data) - BOX_MON, 4):
        if not _checksum_ok(data, off):
            continue
        m = decode_pokemon(dex, data[off:off + BOX_MON])
        if not m or not m["species"]:
            continue
        if not (1 <= (m["internal_index"] or 0) <= 411):      # drop garbage that happens to checksum
            continue
        key = (m["species"], m["nickname"], tuple(m["ivs"].values()), m["ot_id"], m["pid"])
        if key in seen:
            continue                                          # Box keeps backup copies
        seen.add(key)
        box.append(m)

    ot = Counter(m["ot_name"] for m in box).most_common(1)
    return {
        "schema_version": "pokepad-boxrs-savetruth-v1",
        "source": {"game": "Pokémon Box RS", "container": "gci", "code": header_game,
                   "size_bytes": len(data)},
        "trainer": {"name": ot[0][0] if ot else None},
        "counts": {"pokemon": len(box), "species": len({m["species"] for m in box}),
                   "shiny": sum(1 for m in box if m["shiny"])},
        "box": box,
    }


if __name__ == "__main__":
    import sys, json
    st = parse_gci(open(sys.argv[1], "rb").read())
    print(f"{st['source']['code']} — {st['trainer']['name']}: {st['counts']}")
    for m in sorted(st["box"], key=lambda m: -sum(m["ivs"].values()))[:15]:
        s = "✨" if m["shiny"] else "  "
        print(f"  {s} {m['species']:>12} '{m['nickname']}'  {m['nature']}  IVsum={sum(m['ivs'].values())}")
