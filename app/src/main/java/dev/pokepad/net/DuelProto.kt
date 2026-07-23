package dev.pokepad.net

import dev.pokepad.core.Dex
import dev.pokepad.core.Director
import dev.pokepad.core.Ev
import dev.pokepad.core.Mon

/*
 * Poképad — duel wire protocol (two phones, one battle).
 *
 * Host-authoritative: the host runs the one true engine; the joiner sends its
 * chosen move each turn; the host resolves and broadcasts the turn's event
 * stream; both phones render the same truth (the joiner just mirrors sides).
 *
 * Deliberately dependency-free: line-based text over TCP, fields '|'-separated,
 * events ';'-separated, event fields ','-separated, stat lists ':'-separated.
 * (No character in the Gen-III name charmap collides with these; nicknames are
 * sanitized on send anyway.) A python or desktop-Kotlin peer can speak this in
 * a few lines — which is also how it's tested.
 *
 *   join → host   HELLO|<name>|<monSpec>|<benchSpec;benchSpec;...>
 *   host → join   START|<seed>|<hostMonSpec>|<joinMonSpec>|<ev;ev;...>|<format>|<hostBench>|<joinBench>
 *   join → host   MOVE|<turn>|<move>
 *   join → host   SWITCH|<turn>|<teamIdx>          (my replacement after a faint)
 *   host → join   TURN|<turn>|<hpbL>|<hpbR>|<hpL>|<hpR>|<over01>|<winSide|->|<ev;ev;...>
 *                     |<await>|<choicesL>|<choicesR>|<maxL>|<maxR>
 *   either        AGAIN            (rematch request)   ·   BYE
 *
 * Team fields are APPENDED so a 1v1-era peer still parses the prefix. await =
 * which sides (host coords, "-"/"L"/"R"/"LR") must send a replacement in;
 * choices = eligible bench indices (csv) per side; max = actives' max HP.
 *
 *   monSpec = species,level,nickname,ability,nature,iv1:...:iv6,ev1:...:ev6,move1:move2:...
 *   ev      = send,<side>,<species>,<name> | used,<side>,<species>,<move>,<dmg>,<eff>
 *           | faint,<side>,<species>      | win,<side>,<species>
 */
object Proto {
    const val TCP_PORT = 47474
    const val UDP_PORT = 47475
    const val BEACON_PREFIX = "POKEPAD|"

    private val STATS = listOf("hp", "atk", "def", "spa", "spd", "spe")

    fun clean(s: String) = s.replace(Regex("[|,;:]"), " ").trim()

    // ── mon spec ─────────────────────────────────────────────────────────────
    data class MonSpec(val species: String, val level: Int, val nickname: String,
                       val ability: String?, val nature: String,
                       val ivs: Map<String, Int>, val evs: Map<String, Int>,
                       val moves: List<String>) {
        fun toLine(): String {
            val iv = STATS.joinToString(":") { (ivs[it] ?: 31).toString() }
            val ev = STATS.joinToString(":") { (evs[it] ?: 0).toString() }
            return listOf(species, level.toString(), clean(nickname), ability ?: "-", nature,
                iv, ev, moves.joinToString(":")).joinToString(",")
        }
        fun toMon(dex: Dex): Mon {
            val legal = moves.filter { dex.moves.containsKey(it) }
                .ifEmpty { Director.movesetFor(dex, species) }
            return Mon(dex, species, level = level.coerceIn(1, 100), moves = legal,
                nickname = nickname.ifBlank { null }, ability = ability, nature = nature,
                ivs = ivs, evs = evs)
        }
        companion object {
            fun fromLine(s: String): MonSpec? {
                val f = s.split(","); if (f.size < 8) return null
                fun stats(x: String, def: Int) = x.split(":").let { p ->
                    STATS.mapIndexed { i, k -> k to (p.getOrNull(i)?.toIntOrNull() ?: def) }.toMap() }
                return MonSpec(f[0], f[1].toIntOrNull() ?: 50, f[2],
                    f[3].takeIf { it != "-" }, f[4], stats(f[5], 31), stats(f[6], 0),
                    f[7].split(":").filter { it.isNotBlank() })
            }
            fun of(m: Mon, ivs: Map<String, Int>? = null, evs: Map<String, Int>? = null) = MonSpec(
                m.species.name, m.level, m.name, m.ability, "hardy",
                ivs ?: STATS.associateWith { 31 }, evs ?: STATS.associateWith { 0 }, m.moves)
        }
    }

    // ── events ───────────────────────────────────────────────────────────────
    fun evToStr(e: Ev): String = when (e) {
        is Ev.SendIn -> "send,${e.side},${e.species},${clean(e.name)},${e.hpFrac}"
        is Ev.Used -> "used,${e.side},${e.species},${e.move},${e.dmg},${e.eff},${clean(e.name)}"
        is Ev.Faint -> "faint,${e.side},${e.species},${clean(e.name)}"
        is Ev.Win -> "win,${e.side},${e.species},${clean(e.name)}"
    }
    fun evFromStr(s: String): Ev? {
        val f = s.split(","); if (f.size < 3) return null
        return when (f[0]) {
            "send" -> Ev.SendIn(f[1], f[2], f.getOrElse(3) { f[2] },
                f.getOrNull(4)?.toFloatOrNull() ?: 1f)
            "used" -> Ev.Used(f[1], f[2], f.getOrElse(3) { "" },
                f.getOrNull(4)?.toIntOrNull() ?: 0, f.getOrNull(5)?.toDoubleOrNull() ?: 1.0,
                f.getOrElse(6) { f[2] })
            "faint" -> Ev.Faint(f[1], f[2], f.getOrElse(3) { f[2] })
            "win" -> Ev.Win(f[1], f[2], f.getOrElse(3) { f[2] })
            else -> null
        }
    }
    fun evsToStr(evs: List<Ev>) = evs.joinToString(";") { evToStr(it) }
    fun evsFromStr(s: String) = s.split(";").mapNotNull { if (it.isBlank()) null else evFromStr(it) }

    /** the joiner sees the battle mirrored: host(L)↔joiner(R) */
    fun swap(e: Ev): Ev {
        fun s(x: String) = if (x == "L") "R" else "L"
        return when (e) {
            is Ev.SendIn -> e.copy(side = s(e.side))
            is Ev.Used -> e.copy(side = s(e.side))
            is Ev.Faint -> e.copy(side = s(e.side))
            is Ev.Win -> e.copy(side = s(e.side))
        }
    }

    // ── messages ─────────────────────────────────────────────────────────────
    fun benchToStr(bench: List<MonSpec>) = bench.joinToString(";") { it.toLine() }
    fun benchFromStr(s: String) = s.split(";").filter { it.isNotBlank() }.mapNotNull { MonSpec.fromLine(it) }

    fun hello(name: String, team: List<MonSpec>) =
        "HELLO|${clean(name)}|${team.first().toLine()}|${benchToStr(team.drop(1))}"
    fun start(seed: Long, host: List<MonSpec>, join: List<MonSpec>, opening: List<Ev>, format: Int) =
        "START|$seed|${host.first().toLine()}|${join.first().toLine()}|${evsToStr(opening)}|$format|" +
        "${benchToStr(host.drop(1))}|${benchToStr(join.drop(1))}"
    fun move(turn: Int, move: String) = "MOVE|$turn|$move"
    fun switchMsg(turn: Int, idx: Int) = "SWITCH|$turn|$idx"
    fun turn(n: Int, hpbL: Int, hpbR: Int, hpL: Int, hpR: Int, over: Boolean, winSide: String?, evs: List<Ev>,
             await: String = "-", choicesL: List<Int> = emptyList(), choicesR: List<Int> = emptyList(),
             maxL: Int = 0, maxR: Int = 0) =
        "TURN|$n|$hpbL|$hpbR|$hpL|$hpR|${if (over) 1 else 0}|${winSide ?: "-"}|${evsToStr(evs)}" +
        "|${await.ifEmpty { "-" }}|${choicesL.joinToString(",")}|${choicesR.joinToString(",")}|$maxL|$maxR"
}
