"""
Poképad — reference Gen-III battle engine (Python).

The canonical, readable spec for the mechanics. The on-device Kotlin engine is
validated against this (the MultiVera verification gate). Runs on the real
scraped dataset (data/gen3.json): all 386 species, real moves, real type chart.

Gen-III faithful: physical/special split BY TYPE; the Gen-III stat and damage
formulas; STAB; type effectiveness; crits (ignoring unfavorable stat stages);
the 0.85–1.00 damage roll; natures; STAT STAGES (−6..+6); STATUS (burn, poison,
toxic, paralysis, sleep, freeze) + confusion; and per-move EFFECTS driven by the
dataset metadata (ailment, stat changes, flinch, drain, healing, multi-hit,
recharge).

Still staged for later passes (each with tests): held items, weather, entry
hazards, 2-turn charge/semi-invulnerable moves, switching/team AI. See IDEAS.md.
"""
from __future__ import annotations
import json, os, random
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gen3.json")

PHYSICAL_TYPES = {"normal", "fighting", "flying", "ground", "rock", "bug", "ghost", "poison", "steel"}
STATS = ("hp", "atk", "def", "spa", "spd", "spe")
RECHARGE = {"hyper-beam", "blast-burn", "hydro-cannon", "frenzy-plant"}   # Gen-III recharge moves
TWO_TURN = {"solar-beam", "razor-wind", "sky-attack", "skull-bash", "fly", "dig", "bounce", "dive"}  # deferred
SELF_KO = {"explosion", "self-destruct"}
# moves a naive auto-AI shouldn't pick (conditional / 2-turn / self-KO / fixed-
# damage); excluded from best_moveset so autonomous sets are reliable damage.
EXCLUDE_AUTO = SELF_KO | TWO_TURN | {
    "focus-punch", "dream-eater", "sucker-punch", "fake-out", "last-resort",
    "snore", "future-sight", "doom-desire", "beat-up", "spit-up",
    "counter", "mirror-coat", "bide", "endeavor", "false-swipe", "flail", "reversal",
}
# PokéAPI ailment name -> our status code
AILMENT = {"burn": "brn", "poison": "psn", "paralysis": "par", "freeze": "frz",
           "sleep": "slp", "toxic": "tox", "confusion": "confusion"}

_UP = {"lonely": "atk", "brave": "atk", "adamant": "atk", "naughty": "atk",
       "bold": "def", "relaxed": "def", "impish": "def", "lax": "def",
       "modest": "spa", "mild": "spa", "quiet": "spa", "rash": "spa",
       "calm": "spd", "gentle": "spd", "sassy": "spd", "careful": "spd",
       "timid": "spe", "hasty": "spe", "jolly": "spe", "naive": "spe"}
_DOWN = {"lonely": "def", "brave": "spe", "adamant": "spa", "naughty": "spd",
         "bold": "atk", "relaxed": "spe", "impish": "spa", "lax": "spd",
         "modest": "atk", "mild": "spd", "quiet": "spe", "rash": "spd",
         "calm": "atk", "gentle": "def", "sassy": "spe", "careful": "spa",
         "timid": "atk", "hasty": "def", "jolly": "spa", "naive": "spd"}


def nature_mod(nature: str, stat: str) -> float:
    if _UP.get(nature) == stat: return 1.1
    if _DOWN.get(nature) == stat: return 0.9
    return 1.0


def stage_mult(stage: int) -> float:
    """Gen-III main-stat stage multiplier (−6..+6)."""
    return (2 + stage) / 2 if stage >= 0 else 2 / (2 - stage)


def acc_mult(stage: int) -> float:
    """accuracy/evasion stage multiplier."""
    return (3 + stage) / 3 if stage >= 0 else 3 / (3 - stage)


def is_physical(move_type: str) -> bool:
    return move_type in PHYSICAL_TYPES


class Dex:
    def __init__(self, path: str = DATA):
        with open(path) as f:
            self.d = json.load(f)
        self.species = self.d["species"]; self.moves = self.d["moves"]
        self.abilities = self.d["abilities"]; self.chart = self.d["types"]

    def type_eff(self, atk_type: str, def_types: list[str]) -> float:
        m = 1.0
        for dt in def_types:
            m *= self.chart.get(atk_type, {}).get(dt, 1.0)
        return m

    def best_moveset(self, species: str, n: int = 4) -> list[str]:
        """A sane damaging set: highest power, one per type, ≤1 recharge move."""
        learn = self.species[species]["learnset"]
        dmg = [(nm, self.moves[nm]) for nm in learn
               if nm in self.moves and (self.moves[nm]["power"] or 0) > 0]
        dmg.sort(key=lambda kv: kv[1]["power"], reverse=True)
        chosen, seen_types, recharge_used = [], set(), False
        for nm, mv in dmg:
            if nm in EXCLUDE_AUTO:
                continue
            if nm in RECHARGE and recharge_used:
                continue
            if mv["type"] in seen_types:
                continue
            chosen.append(nm); seen_types.add(mv["type"])
            recharge_used = recharge_used or nm in RECHARGE
            if len(chosen) == n:
                return chosen
        for nm, _ in dmg:      # fill remaining
            if nm not in chosen:
                chosen.append(nm)
            if len(chosen) == n:
                break
        return chosen or ["tackle"]


@dataclass(eq=False)          # identity equality → hashable (used as dict keys)
class Pokemon:
    dex: Dex
    species: str
    level: int = 50
    ivs: dict = field(default_factory=lambda: {k: 31 for k in STATS})
    evs: dict = field(default_factory=lambda: {k: 0 for k in STATS})
    nature: str = "hardy"
    moves: list[str] | None = None
    nickname: str | None = None

    def __post_init__(self):
        s = self.dex.species[self.species]
        self.base = s["base"]; self.types = s["types"]
        if self.moves is None:
            self.moves = self.dex.best_moveset(self.species)
        self.stats = {k: self._calc(k) for k in STATS}
        self.max_hp = self.stats["hp"]; self.hp = self.max_hp
        self.status = None                # brn/psn/tox/par/slp/frz
        self.status_counter = 0           # sleep turns left / toxic tick
        self.stages = {k: 0 for k in ("atk", "def", "spa", "spd", "spe", "acc", "eva")}
        self.confused = 0                 # turns left
        self.must_recharge = False
        self.flinched = False
        self.took_damage = False          # this turn (for Focus Punch)

    def _calc(self, k: str) -> int:
        base, iv, ev, lvl = self.base[k], self.ivs[k], self.evs[k], self.level
        inner = (2 * base + iv + ev // 4) * lvl // 100
        return inner + lvl + 10 if k == "hp" else int((inner + 5) * nature_mod(self.nature, k))

    def eff_speed(self) -> int:
        v = int(self.stats["spe"] * stage_mult(self.stages["spe"]))
        if self.status == "par":
            v //= 4
        return max(1, v)

    def boost(self, stat: str, n: int) -> int:
        old = self.stages[stat]
        self.stages[stat] = max(-6, min(6, old + n))
        return self.stages[stat] - old

    def heal(self, amt: int):
        self.hp = min(self.max_hp, self.hp + max(0, amt))

    @property
    def name(self): return self.nickname or self.species.title()
    @property
    def fainted(self): return self.hp <= 0


def damage(dex: Dex, attacker: Pokemon, defender: Pokemon, move_name: str,
           roll: int = None, crit: bool = None, rng: random.Random = None):
    """Gen-III single-hit damage (stage- and burn-aware). Crit ignores the
    attacker's negative offensive stage and the defender's positive defensive
    stage. roll 85..100 (None=random); crit (None=1/16)."""
    mv = dex.moves[move_name]
    power = mv["power"] or 0
    if power == 0:
        return 0, 1.0, False, "status"
    eff = dex.type_eff(mv["type"], defender.types)
    if eff == 0:
        return 0, 0.0, False, "immune"
    phys = is_physical(mv["type"])
    ak, dk = ("atk", "def") if phys else ("spa", "spd")
    if crit is None:
        crit = (rng or random).randint(1, 16) == 1
    if roll is None:
        roll = (rng or random).randint(85, 100)
    a_stage, d_stage = attacker.stages[ak], defender.stages[dk]
    if crit:
        a_stage, d_stage = max(0, a_stage), min(0, d_stage)
    A = max(1, int(attacker.stats[ak] * stage_mult(a_stage)))
    D = max(1, int(defender.stats[dk] * stage_mult(d_stage)))
    if phys and attacker.status == "brn":
        A //= 2                                   # burn halves physical attack
    A = max(1, A)
    dmg = (((2 * attacker.level) // 5 + 2) * power * A) // D
    dmg = dmg // 50 + 2
    if crit:
        dmg *= 2
    if mv["type"] in attacker.types:
        dmg = dmg * 3 // 2
    dmg = int(dmg * eff)
    dmg = dmg * roll // 100
    return max(1, dmg), eff, crit, "hit"


def choose_move(dex: Dex, attacker: Pokemon, defender: Pokemon) -> str:
    """autonomous AI: best expected damage (accuracy-weighted). Status/boost
    moves (power 0) score 0, so a damage set never wastes a turn."""
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

    # ── status gating before a mon acts ──────────────────────────────────
    def _can_move(self, p: Pokemon) -> bool:
        if p.must_recharge:
            p.must_recharge = False
            self.log(f"  {p.name} must recharge!")
            return False
        if p.status == "frz":
            if self.rng.random() < 0.20:
                p.status = None; self.log(f"  {p.name} thawed out!")
            else:
                self.log(f"  {p.name} is frozen solid!"); return False
        if p.status == "slp":
            p.status_counter -= 1
            if p.status_counter <= 0:
                p.status = None; self.log(f"  {p.name} woke up!")
            else:
                self.log(f"  {p.name} is fast asleep."); return False
        if p.flinched:
            p.flinched = False; self.log(f"  {p.name} flinched!"); return False
        if p.status == "par" and self.rng.random() < 0.25:
            self.log(f"  {p.name} is paralyzed! It can't move!"); return False
        if p.confused > 0:
            p.confused -= 1
            if self.rng.random() < 0.5:
                # 40-BP typeless physical self-hit
                d = (((2 * p.level) // 5 + 2) * 40 * p.stats["atk"]) // p.stats["def"] // 50 + 2
                p.hp = max(0, p.hp - d)
                self.log(f"  {p.name} is confused and hurt itself ({d})!")
                if p.fainted: self._faint(p)
                return False
        return True

    def _apply_effects(self, mv, attacker, defender, dealt):
        # ailment (status / confusion)
        ail = (mv.get("ailment") or "none")
        code = AILMENT.get(ail)
        chance = mv.get("ailment_chance") or 0
        if code and (chance == 0 or self.rng.randint(1, 100) <= chance):
            if code == "confusion":
                if defender.confused == 0:
                    defender.confused = self.rng.randint(2, 5)
                    self.log(f"  {defender.name} became confused!")
            elif defender.status is None and not self._status_immune(defender, code):
                defender.status = code
                if code == "slp": defender.status_counter = self.rng.randint(1, 3)
                if code == "tox": defender.status_counter = 1
                self.log(f"  {defender.name} was {self._status_word(code)}!")
        # stat changes (self-target vs opponent from the move target)
        target_self = "user" in (mv.get("target") or "")
        sc_chance = mv.get("effect_chance")
        for ch in mv.get("stat_changes", []):
            st = {"attack": "atk", "defense": "def", "special-attack": "spa",
                  "special-defense": "spd", "speed": "spe", "accuracy": "acc", "evasion": "eva"}.get(ch["stat"])
            if not st: continue
            if sc_chance and self.rng.randint(1, 100) > sc_chance:
                continue
            who = attacker if target_self else defender
            got = who.boost(st, ch["change"])
            if got:
                self.log(f"  {who.name}'s {st} {'rose' if ch['change']>0 else 'fell'}"
                         f"{' sharply' if abs(ch['change'])>=2 else ''}!")
        # flinch
        fc = mv.get("flinch_chance") or 0
        if fc and self.rng.randint(1, 100) <= fc:
            defender.flinched = True
        # drain / healing
        if mv.get("drain"):
            attacker.heal(dealt * mv["drain"] // 100)
        if mv.get("healing"):
            attacker.heal(attacker.max_hp * mv["healing"] // 100)

    def _status_immune(self, p, code):
        # type-based status immunities (Gen III)
        if code == "brn" and "fire" in p.types: return True
        if code in ("psn", "tox") and ("poison" in p.types or "steel" in p.types): return True
        if code == "par" and "electric" in p.types: return False  # (Gen III: not immune)
        if code == "frz" and "ice" in p.types: return True
        return False

    @staticmethod
    def _status_word(c):
        return {"brn": "burned", "psn": "poisoned", "tox": "badly poisoned",
                "par": "paralyzed", "slp": "put to sleep", "frz": "frozen"}[c]

    def _faint(self, p):
        other = self.right if p is self.left else self.left
        self.over, self.winner = True, other
        self.log(f"  {p.name} fainted! {other.name} wins.")

    def _act(self, attacker: Pokemon, defender: Pokemon, move: str):
        if not self._can_move(attacker):
            return
        mv = self.dex.moves[move]
        nice = move.replace("-", " ").title()
        if move == "focus-punch" and attacker.took_damage:
            self.log(f"  {attacker.name} lost its focus and couldn't move!"); return
        # accuracy with acc/eva stages
        acc = mv["accuracy"]
        if acc is not None:
            eff_acc = acc * acc_mult(attacker.stages["acc"]) / acc_mult(defender.stages["eva"])
            if self.rng.uniform(0, 100) > eff_acc:
                self.log(f"  {attacker.name} used {nice} — it missed!"); return
        power = mv["power"] or 0
        dealt = 0
        if power > 0:
            hits = 1
            if mv.get("min_hits"):
                hits = self.rng.randint(mv["min_hits"], mv["max_hits"] or mv["min_hits"])
            total, eff, crit = 0, 1.0, False
            for _ in range(hits):
                d, eff, crit, kind = damage(self.dex, attacker, defender, move, rng=self.rng)
                if kind == "immune":
                    self.log(f"  {attacker.name} used {nice} → it doesn't affect {defender.name}…"); return
                defender.hp = max(0, defender.hp - d); total += d
                defender.took_damage = True
                if defender.fainted: break
            dealt = total
            tag = {2.0: " (super effective!)", 4.0: " (super effective!)",
                   0.5: " (resisted)", 0.25: " (resisted)"}.get(eff, "")
            crit_tag = " CRIT!" if crit else ""
            hit_tag = f" ×{hits}" if hits > 1 else ""
            self.log(f"  {attacker.name} used {nice}{hit_tag} → {total}{tag}{crit_tag}  "
                     f"({defender.name} {defender.hp}/{defender.max_hp})")
        else:
            self.log(f"  {attacker.name} used {nice}.")
        # secondary effects (unless the target already fainted)
        if not defender.fainted:
            self._apply_effects(mv, attacker, defender, dealt)
        if move in RECHARGE and power > 0:
            attacker.must_recharge = True
        if move in SELF_KO and power > 0:
            attacker.hp = 0
            self.log(f"  {attacker.name} fainted (it used {nice})!")
        if defender.fainted and attacker.fainted:
            self.over, self.winner = True, defender      # exploder loses the 1v1
            self.log(f"  both go down — {defender.name} outlasts.")
        elif defender.fainted:
            self._faint(defender)
        elif attacker.fainted:
            self._faint(attacker)

    def _end_of_turn(self, p: Pokemon):
        if p.fainted or self.over:
            return
        if p.status == "brn":
            d = max(1, p.max_hp // 8); p.hp = max(0, p.hp - d)
            self.log(f"  {p.name} is hurt by its burn ({d}).")
        elif p.status == "psn":
            d = max(1, p.max_hp // 8); p.hp = max(0, p.hp - d)
            self.log(f"  {p.name} is hurt by poison ({d}).")
        elif p.status == "tox":
            d = max(1, p.max_hp * p.status_counter // 16); p.status_counter += 1
            p.hp = max(0, p.hp - d)
            self.log(f"  {p.name} is hurt by toxic ({d}).")
        if p.fainted:
            self._faint(p)

    def _other(self, p): return self.right if p is self.left else self.left

    def run(self, max_turns: int = 300):
        self.log(f"{self.left.name} (Lv{self.left.level}) vs {self.right.name} (Lv{self.right.level})")
        t = 0
        while not self.over and t < max_turns:
            t += 1
            self.log(f"— turn {t} —")
            for p in (self.left, self.right):
                p.took_damage = False
            # both commit a move, THEN act in (priority, speed) order
            picks = {p: choose_move(self.dex, p, self._other(p)) for p in (self.left, self.right) if not p.fainted}
            order = sorted(picks.keys(),
                           key=lambda p: (self.dex.moves[picks[p]]["priority"], p.eff_speed(), self.rng.random()),
                           reverse=True)
            for attacker in order:
                if attacker.fainted or self.over:
                    continue
                self._act(attacker, self._other(attacker), picks[attacker])
                if self.over:
                    break
            for p in (self.left, self.right):   # end of turn: flinch clears, residuals
                p.flinched = False
                self._end_of_turn(p)
        return self.winner
