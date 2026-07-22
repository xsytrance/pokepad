"""CLI: simulate an autonomous Gen-III battle between two real species.

    python3 -m sim charizard blastoise
    python3 -m sim gengar alakazam --level 50 --seed 3
"""
import argparse
from .engine import Dex, Pokemon, Battle


def main():
    ap = argparse.ArgumentParser(description="Poképad reference Gen-III battle sim")
    ap.add_argument("left"); ap.add_argument("right")
    ap.add_argument("--level", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    dex = Dex()

    def build(spec):
        names = [s.strip() for s in spec.split(",")]
        for n in names:
            if n not in dex.species:
                raise SystemExit(f"unknown species '{n}'. e.g. charizard, gengar, rayquaza (comma-separate for a team)")
        mons = [Pokemon(dex, n, level=a.level) for n in names]
        return mons if len(mons) > 1 else mons[0]

    left, right = build(a.left), build(a.right)
    for side in (left, right):
        for m in (side if isinstance(side, list) else [side]):
            print(f"{m.name}: {'/'.join(m.types)}  {m.ability}  moves: {', '.join(x.replace('-', ' ') for x in m.moves)}")
    print()
    Battle(dex, left, right, seed=a.seed).run()


if __name__ == "__main__":
    main()
