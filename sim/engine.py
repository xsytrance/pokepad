"""
Poképad — reference Gen-III battle engine (Python).

The canonical, readable spec for the mechanics. The on-device Kotlin engine is
validated against this (the MultiVera verification gate). Runs on the real
scraped dataset (data/gen3.json): all 386 species, real moves, real type chart.

Gen-III faithful: physical/special split BY TYPE; the Gen-III stat and damage
formulas; STAB; type effectiveness; crits; the 0.85–1.00 damage roll; natures.
Status / stat-stages / abilities / items are staged extension points (see the
NotImplemented markers) — added in later passes, each with tests.
"""
from __future__ import annotations
import json, os, random
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gen3.json")

# Gen-III physical/special split is by TYPE (not per-move)
PHYSICAL_TYPES = {"normal", "fighting", "flying", "ground", "rock", "bug", "ghost", "poison", "steel"}

# 25 natures: (stat_boosted +10%, stat_lowered -10%); neutral = no change
_UP = {"lonely": "atk", "brave": "atk", "adamant": "atk", "naughty": "atk",
       "bold": "def", "relaxed": "def", "impish": "def", "lax": "def",
       "modest": "spa", "mild": "spa", "quiet": "spa", "rash": "spa",
       "calm": "spd", "gentle": "spd", "sassy": "spd", "careful": "spd",
       "timid": "spe", "hasty": "spe", "jolly": "spe", "naive": "spe"}
_DOWN = {"lonely": "def", "bold": "atk", "modest": "atk", "calm": "atk", "timid": "atk",
         "brave": "spe", "relaxed": "spe", "quiet": "spe", "sassy": "spe",
         "adamant": "spa", "impish": "spa", "careful": "spa", "jolly": "spa",
         "naughty": "spd", "lax": "spd", "rash": "spd", "mild": "spd", "hasty": "spd", "naive": "spd",
         "gentle": "def", "lonely2": "def"}  # (careful/others above)
# fix a couple mappings explicitly for correctness
_DOWN.update({"lonely": "def", "brave": "spe", "adamant": "spa", "naughty": "spd",
              "bold": "atk", "relaxed": "spe", "impish": "spa", "lax": "spd",
              "modest": "atk", "mild": "spd", "quiet": "spe", "rash": "spd",
              "calm": "atk", "gentle": "def", "sassy": "spe", "careful": "spa",
              "timid": "atk", "hasty": "def", "jolly": "spa", "naive": "spd"})


class Dex:
    def __init__(self, path: str = DATA):
        with open(path) as f:
            self.d = json.load(f)
        self.species = self.d["species"]
        self.moves = self.d["moves"]
        self.abilities = self.d["abilities"]
        self.chart = self.d["types"]

    def type_eff(self, atk_type: str, def_types: list[str]) -> float:
        m = 1.0
        for dt in def_types:
            m *= self.chart.get(atk_type, {}).get(dt, 1.0)
        return m

    def best_moveset(self, species: str, n: int = 4) -> list[str]:
        """pick n sensible damaging moves from the Gen-III learnset (highest power,
        one per type where possible)."""
        learn = self.species[species]["learnset"]
        dmg = [(name, self.moves[name]) for name in learn
               if name in self.moves and (self.moves[name]["power"] or 0) > 0]
        dmg.sort(key=lambda kv: kv[1]["power"], reverse=True)
        chosen, seen_types = [], set()
        for name, mv in dmg:
            if mv["type"] not in seen_types:
                chosen.append(name); seen_types.add(mv["type"])
            if len(chosen) == n:
                return chosen
        for name, _ in dmg:  # fill remaining slots
            if name not in chosen:
                chosen.append(name)
            if len(chosen) == n:
                break
        return chosen or ["tackle"]


def nature_mod(nature: str, stat: str) -> float:
    if _UP.get(nature) == stat: return 1.1
    if _DOWN.get(nature) == stat: return 0.9
    return 1.0


@dataclass
class Pokemon:
    dex: Dex
    species: str
    level: int = 50
    ivs: dict = field(default_factory=lambda: {k: 31 for k in ("hp", "atk", "def", "spa", "spd", "spe")})
    evs: dict = field(default_factory=lambda: {k: 0 for k in ("hp", "atk", "def", "spa", "spd", "spe")})
    nature: str = "hardy"           # neutral
    moves: list[str] | None = None
    nickname: str | None = None

    def __post_init__(self):
        s = self.dex.species[self.species]
        self.base = s["base"]; self.types = s["types"]
        if self.moves is None:
            self.moves = self.dex.best_moveset(self.species)
        self.stats = {k: self._calc(k) for k in ("hp", "atk", "def", "spa", "spd", "spe")}
        self.max_hp = self.stats["hp"]; self.hp = self.max_hp

    def _calc(self, k: str) -> int:
        base, iv, ev, lvl = self.base[k], self.ivs[k], self.evs[k], self.level
        inner = (2 * base + iv + ev // 4) * lvl // 100
        if k == "hp":
            return inner + lvl + 10
        return int((inner + 5) * nature_mod(self.nature, k))

    @property
    def name(self): return self.nickname or self.species.title()
    @property
    def fainted(self): return self.hp <= 0


def is_physical(move_type: str) -> bool:
    return move_type in PHYSICAL_TYPES


def damage(dex: Dex, attacker: Pokemon, defender: Pokemon, move_name: str,
           roll: int = None, crit: bool = None, rng: random.Random = None):
    """Gen-III single-hit damage. roll 85..100 (None = random), crit (None = 1/16)."""
    mv = dex.moves[move_name]
    power = mv["power"] or 0
    if power == 0:
        return 0, 1.0, False, "status"
    eff = dex.type_eff(mv["type"], defender.types)
    if eff == 0:
        return 0, 0.0, False, "immune"
    phys = is_physical(mv["type"])
    A = attacker.stats["atk"] if phys else attacker.stats["spa"]
    D = defender.stats["def"] if phys else defender.stats["spd"]
    if crit is None:
        crit = (rng or random).randint(1, 16) == 1
    if roll is None:
        roll = (rng or random).randint(85, 100)
    dmg = (((2 * attacker.level) // 5 + 2) * power * A) // D
    dmg = dmg // 50 + 2
    if crit:
        dmg *= 2
    if mv["type"] in attacker.types:      # STAB
        dmg = dmg * 3 // 2
    dmg = int(dmg * eff)                   # type effectiveness
    dmg = dmg * roll // 100               # 0.85..1.00
    return max(1, dmg), eff, crit, "hit"


def choose_move(dex: Dex, attacker: Pokemon, defender: Pokemon) -> str:
    """best expected-damage move (accuracy-weighted); the autonomous AI."""
    best, best_score = attacker.moves[0], -1.0
    for name in attacker.moves:
        mv = dex.moves.get(name)
        if not mv:
            continue
        power = mv["power"] or 0
        eff = dex.type_eff(mv["type"], defender.types)
        phys = is_physical(mv["type"])
        A = attacker.stats["atk"] if phys else attacker.stats["spa"]
        D = defender.stats["def"] if phys else defender.stats["spd"]
        stab = 1.5 if mv["type"] in attacker.types else 1.0
        acc = (mv["accuracy"] or 100) / 100
        score = power * (A / D) * stab * eff * acc
        if score > best_score:
            best_score, best = score, name
    return best


class Battle:
    def __init__(self, dex: Dex, left: Pokemon, right: Pokemon, seed: int = 0, log=print):
        self.dex, self.left, self.right = dex, left, right
        self.rng = random.Random(seed)
        self.log, self.over, self.winner = log, False, None

    def _order(self):
        ls, rs = self.left.stats["spe"], self.right.stats["spe"]
        left_first = ls > rs or (ls == rs and self.rng.random() < 0.5)
        return [self.left, self.right] if left_first else [self.right, self.left]

    def _act(self, attacker: Pokemon, defender: Pokemon):
        move = choose_move(self.dex, attacker, defender)
        mv = self.dex.moves[move]
        if self.rng.randint(1, 100) > (mv["accuracy"] or 100):
            self.log(f"  {attacker.name} used {move.replace('-', ' ').title()} — it missed!")
            return
        dmg, eff, crit, kind = damage(self.dex, attacker, defender, move, rng=self.rng)
        defender.hp = max(0, defender.hp - dmg)
        tag = {2.0: " (super effective!)", 4.0: " (super effective!)", 0.5: " (resisted)", 0.25: " (resisted)", 0.0: " (no effect)"}.get(eff, "")
        crit_tag = " CRIT!" if crit else ""
        self.log(f"  {attacker.name} used {move.replace('-', ' ').title()} → {dmg} dmg{tag}{crit_tag}  "
                 f"({defender.name} {defender.hp}/{defender.max_hp})")
        if defender.fainted:
            self.over, self.winner = True, attacker
            self.log(f"  {defender.name} fainted! {attacker.name} wins.")

    def run(self, max_turns: int = 200):
        self.log(f"{self.left.name} (Lv{self.left.level}) vs {self.right.name} (Lv{self.right.level})")
        t = 0
        while not self.over and t < max_turns:
            t += 1
            self.log(f"— turn {t} —")
            for attacker in self._order():
                if attacker.fainted:
                    continue
                defender = self.right if attacker is self.left else self.left
                self._act(attacker, defender)
                if self.over:
                    break
        return self.winner
