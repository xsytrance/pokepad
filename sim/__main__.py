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
    for name in (a.left, a.right):
        if name not in dex.species:
            raise SystemExit(f"unknown species '{name}'. e.g. charizard, blastoise, gengar, rayquaza")
    left = Pokemon(dex, a.left, level=a.level)
    right = Pokemon(dex, a.right, level=a.level)
    print(f"{left.name}: {'/'.join(left.types)}  stats={left.stats}")
    print(f"   moves: {', '.join(m.replace('-', ' ') for m in left.moves)}")
    print(f"{right.name}: {'/'.join(right.types)}  stats={right.stats}")
    print(f"   moves: {', '.join(m.replace('-', ' ') for m in right.moves)}\n")
    Battle(dex, left, right, seed=a.seed).run()


if __name__ == "__main__":
    main()
