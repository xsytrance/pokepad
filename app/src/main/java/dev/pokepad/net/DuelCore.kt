package dev.pokepad.net

import dev.pokepad.core.Battle
import dev.pokepad.core.Dex
import dev.pokepad.core.Director
import dev.pokepad.core.Ev
import dev.pokepad.core.Mon
import dev.pokepad.core.Reel

/*
 * Poképad — duel controllers (pure Kotlin, no Android).
 *
 * HostCore owns the one true Battle; JoinCore mirrors it. Both expose the same
 * surface to the UI: myMoves() for the menu, chooseMove() when the player picks,
 * chooseSwitch() when a fainted side sends its replacement, onLine() for
 * transport input, and callbacks (onReel to animate a turn, onMenu to prompt,
 * onSwitchMenu to pick the next mon, onStatus for the waiting line, onOver at
 * the end). The desktop loopback test wires two of these straight together.
 *
 * Teams: both sides bring up to `format` mon (6 = limitless, the full party).
 * When an active faints, THAT player chooses the replacement — the host defers
 * the engine (Battle.humanSides has both sides) and relays a SendIn-only TURN
 * once the choice lands, so both screens see the same summon.
 */
interface DuelSide {
    fun onLine(line: String)
    fun chooseMove(move: String)
    fun chooseSwitch(idx: Int) {}
    fun myMoves(): List<String>
    fun myName(): String
    fun foeName(): String
}

/** a bench choice the UI can put on a button: team index + display label */
data class SwitchChoice(val idx: Int, val label: String)

class HostCore(
    private val dex: Dex,
    private val myTeam: List<Proto.MonSpec>,
    private val format: Int,
    private val seed: Long,
    private val send: (String) -> Unit,
    private val onReel: (Reel) -> Unit,
    private val onMenu: () -> Unit,
    private val onSwitchMenu: (List<SwitchChoice>) -> Unit,
    private val onStatus: (String) -> Unit,
    private val onOver: (Boolean) -> Unit,
) : DuelSide {
    private var battle: Battle? = null
    private var turnN = 0
    private var round = 0
    private var myPick: String? = null
    private var theirPick: String? = null
    private val events = ArrayList<Ev>()
    private var afterReel: (() -> Unit)? = null
    private var lastJoinTeam: List<Proto.MonSpec> = emptyList()

    private fun teamSize() = if (format >= 6) 6 else format

    override fun myName() = myTeam.first().nickname.ifBlank { myTeam.first().species }
    override fun foeName() = battle?.right?.name ?: "challenger"
    override fun myMoves() = battle?.leftMoves() ?: emptyList()

    @Synchronized override fun onLine(line: String) {
        val f = line.split("|")
        when (f[0]) {
            "HELLO" -> {
                val lead = Proto.MonSpec.fromLine(f.getOrElse(2) { "" }) ?: return
                val bench = Proto.benchFromStr(f.getOrElse(3) { "" })
                startRound(listOf(lead) + bench)
            }
            "MOVE" -> {
                theirPick = f.getOrElse(2) { "" }
                    .takeIf { m -> battle?.right?.moves?.contains(m) == true }
                    ?: battle?.right?.moves?.firstOrNull()
                maybeResolve()
            }
            "SWITCH" -> {
                val bt = battle ?: return
                val idx = f.getOrElse(2) { "" }.toIntOrNull() ?: return
                if (!bt.awaitingSwitch("R") || idx !in bt.switchChoices("R")) return
                applySwitch("R", idx)
            }
            "AGAIN" -> if (lastJoinTeam.isNotEmpty()) startRound(lastJoinTeam)
        }
    }

    private fun startRound(theirTeam: List<Proto.MonSpec>) {
        lastJoinTeam = theirTeam
        round++
        val mine = myTeam.take(teamSize()).map { it.toMon(dex) }
        val theirs = theirTeam.take(teamSize()).map { it.toMon(dex) }
        turnN = 0; myPick = null; theirPick = null
        events.clear()
        val bt = Battle(dex, mine, theirs, seed = seed + round * 1000L, emit = { events.add(it) })
        bt.humanSides.add("L"); bt.humanSides.add("R")
        battle = bt
        bt.startInteractive()
        val opening = ArrayList(events); events.clear()
        send(Proto.start(seed, myTeam.take(teamSize()), theirTeam.take(teamSize()), opening, format))
        afterReel = { onMenu() }
        onReel(Director.renderEvents(dex, bt.left.species.name, bt.right.species.name, opening,
            bt.left.maxHp.toFloat(), bt.right.maxHp.toFloat(), bt.left.maxHp.toFloat(), bt.right.maxHp.toFloat(),
            leftBack = true, bothOut = false))
    }

    @Synchronized override fun chooseMove(move: String) {
        val bt = battle ?: return
        if (bt.over || bt.awaitingSwitch("L") || bt.awaitingSwitch("R") || myPick != null) return
        myPick = move
        onStatus("waiting for ${foeName()}…")
        maybeResolve()
    }

    @Synchronized override fun chooseSwitch(idx: Int) {
        val bt = battle ?: return
        if (!bt.awaitingSwitch("L") || idx !in bt.switchChoices("L")) return
        applySwitch("L", idx)
    }

    private fun await(bt: Battle) =
        (if (bt.awaitingSwitch("L")) "L" else "") + (if (bt.awaitingSwitch("R")) "R" else "")

    /** apply a replacement, broadcast the SendIn-only TURN, animate it locally */
    private fun applySwitch(side: String, idx: Int) {
        val bt = battle ?: return
        events.clear()
        bt.sendIn(side, idx)
        val evs = ArrayList(events); events.clear()
        sendTurn(bt, bt.left.hp, bt.right.hp, evs)
        renderTurn(bt, bt.left.hp.toFloat(), bt.right.hp.toFloat(), evs, null)
    }

    private fun maybeResolve() {
        val bt = battle ?: return
        val mine = myPick ?: return
        val theirs = theirPick ?: return
        myPick = null; theirPick = null
        turnN++
        val hpbL = bt.left.hp; val hpbR = bt.right.hp
        val leftSp = bt.left.species.name; val rightSp = bt.right.species.name
        val maxL = bt.left.maxHp; val maxR = bt.right.maxHp
        events.clear()
        bt.stepPvp(mine, theirs)
        val evs = ArrayList(events); events.clear()
        sendTurn(bt, hpbL, hpbR, evs)
        renderTurn(bt, hpbL.toFloat(), hpbR.toFloat(), evs, RenderSpecies(leftSp, rightSp, maxL, maxR))
    }

    private fun sendTurn(bt: Battle, hpbL: Int, hpbR: Int, evs: List<Ev>) {
        send(Proto.turn(turnN, hpbL, hpbR, bt.left.hp, bt.right.hp, bt.over, bt.winSide, evs,
            await = await(bt).ifEmpty { "-" },
            choicesL = bt.switchChoices("L"), choicesR = bt.switchChoices("R"),
            maxL = bt.left.maxHp, maxR = bt.right.maxHp))
    }

    /** species/maxima captured BEFORE the step (actives can faint mid-turn) */
    private data class RenderSpecies(val leftSp: String, val rightSp: String, val maxL: Int, val maxR: Int)

    private fun renderTurn(bt: Battle, hpbL: Float, hpbR: Float, evs: List<Ev>, pre: RenderSpecies?) {
        val leftSp = pre?.leftSp ?: bt.left.species.name
        val rightSp = pre?.rightSp ?: bt.right.species.name
        val maxL = (pre?.maxL ?: bt.left.maxHp).toFloat()
        val maxR = (pre?.maxR ?: bt.right.maxHp).toFloat()
        afterReel = when {
            bt.over -> { { onOver(bt.winSide == "L") } }
            bt.awaitingSwitch("L") -> { { onSwitchMenu(choices(bt, "L")) } }
            bt.awaitingSwitch("R") -> { { onStatus("${foeName()} is choosing the next mon…") } }
            else -> { { onMenu() } }
        }
        onReel(Director.renderEvents(dex, leftSp, rightSp, evs, hpbL, hpbR, maxL, maxR,
            leftBack = true, winnerName = if (bt.over) (bt.winner?.name ?: "") else "", bothOut = true))
    }

    private fun choices(bt: Battle, side: String) = bt.switchChoices(side).map { i ->
        val m = bt.team(side)[i]
        SwitchChoice(i, "${m.name}\nLv${m.level} · ${100 * m.hp / m.maxHp}%")
    }

    /** the turn animation finished — advance to menu / picker / result */
    fun reelDone() { val cb = afterReel; afterReel = null; cb?.invoke() }
}

class JoinCore(
    private val dex: Dex,
    private val myTeam: List<Proto.MonSpec>,
    private val send: (String) -> Unit,
    private val onReel: (Reel) -> Unit,
    private val onMenu: () -> Unit,
    private val onSwitchMenu: (List<SwitchChoice>) -> Unit,
    private val onStatus: (String) -> Unit,
    private val onOver: (Boolean) -> Unit,
) : DuelSide {
    private var myMons: List<Mon> = emptyList()   // host's RIGHT team; our side on screen
    private var myIdx = 0
    private var theirActive: Mon? = null          // host's current active (display only)
    private var theirName = "host"
    private var turnN = 0
    @Volatile private var live = false
    @Volatile private var picked = false
    private var afterReel: (() -> Unit)? = null
    private val myHp = HashMap<Int, Int>()        // team idx → last known hp (actives update)

    fun helloLine() = Proto.hello(myTeam.first().nickname, myTeam)
    override fun myName() = myMons.getOrNull(myIdx)?.name ?: myTeam.first().nickname.ifBlank { myTeam.first().species }
    override fun foeName() = theirName
    override fun myMoves() = myMons.getOrNull(myIdx)?.moves?.filter { dex.moves.containsKey(it) } ?: emptyList()

    @Synchronized override fun onLine(line: String) {
        val f = line.split("|")
        when (f[0]) {
            "START" -> {
                val hostLead = Proto.MonSpec.fromLine(f.getOrElse(2) { "" }) ?: return
                val joinLead = Proto.MonSpec.fromLine(f.getOrElse(3) { "" }) ?: return
                val joinBench = Proto.benchFromStr(f.getOrElse(7) { "" })
                myMons = (listOf(joinLead) + joinBench).map { it.toMon(dex) }
                myIdx = 0; myHp.clear()
                myMons.forEachIndexed { i, m -> myHp[i] = m.maxHp }
                theirActive = hostLead.toMon(dex); theirName = theirActive!!.name
                turnN = 0; live = true; picked = false
                // mirror: our mon is LEFT on our screen
                val opening = Proto.evsFromStr(f.getOrElse(4) { "" }).map { Proto.swap(it) }
                afterReel = { onMenu() }
                val me = myMons[0]
                onReel(Director.renderEvents(dex, me.species.name, theirActive!!.species.name, opening,
                    me.maxHp.toFloat(), theirActive!!.maxHp.toFloat(),
                    me.maxHp.toFloat(), theirActive!!.maxHp.toFloat(),
                    leftBack = true, bothOut = false))
            }
            "TURN" -> {
                if (!live) return
                turnN = f.getOrElse(1) { "0" }.toIntOrNull() ?: turnN
                val hpbL = f.getOrElse(2) { "0" }.toIntOrNull() ?: 0   // host side
                val hpbR = f.getOrElse(3) { "0" }.toIntOrNull() ?: 0   // our side
                val hpR = f.getOrElse(5) { "0" }.toIntOrNull() ?: 0
                val over = f.getOrElse(6) { "0" } == "1"
                val winSide = f.getOrElse(7) { "-" }
                val evs = Proto.evsFromStr(f.getOrElse(8) { "" }).map { Proto.swap(it) }
                val await = f.getOrElse(9) { "-" }
                val myChoices = f.getOrElse(11) { "" }.split(",").mapNotNull { it.toIntOrNull() }
                val maxHost = f.getOrElse(12) { "0" }.toIntOrNull() ?: 0
                val maxMine = f.getOrElse(13) { "0" }.toIntOrNull() ?: 0

                // track what we can see of our own team + the host's active
                myHp[myIdx] = hpR
                for (e in evs) when (e) {
                    is Ev.SendIn -> if (e.side == "L") {           // our side (mirrored)
                        myMons.indexOfFirst { it.species.name == e.species && !isDown(it) }
                            .takeIf { it >= 0 }?.let { myIdx = it }
                    } else theirName = e.name.ifBlank { e.species }
                    else -> {}
                }
                picked = false
                val me = myMons.getOrNull(myIdx) ?: return
                val mMine = (if (maxMine > 0) maxMine else me.maxHp).toFloat()
                val mHost = (if (maxHost > 0) maxHost else theirActive?.maxHp ?: 1).toFloat()
                if (over) live = false
                afterReel = when {
                    over -> { { onOver(winSide == "R") } }
                    "R" in await -> { {                        // host coords R = us
                        onSwitchMenu(myChoices.mapNotNull { i -> myMons.getOrNull(i)?.let { m ->
                            SwitchChoice(i, "${m.name}\nLv${m.level} · ${100 * (myHp[i] ?: m.maxHp) / m.maxHp}%")
                        } })
                    } }
                    "L" in await -> { { onStatus("$theirName is choosing the next mon…") } }
                    else -> { { onMenu() } }
                }
                onReel(Director.renderEvents(dex, me.species.name,
                    theirActive?.species?.name ?: me.species.name, evs,
                    hpbR.toFloat(), hpbL.toFloat(), mMine, mHost,
                    leftBack = true, winnerName = when (winSide) {
                        "R" -> myName(); "L" -> theirName; else -> "" }, bothOut = true))
            }
        }
    }

    private fun isDown(m: Mon): Boolean {
        val i = myMons.indexOf(m)
        return (myHp[i] ?: m.maxHp) <= 0
    }

    @Synchronized override fun chooseMove(move: String) {
        if (!live || picked) return
        picked = true
        onStatus("waiting for ${foeName()}…")
        send(Proto.move(turnN + 1, move))
    }

    @Synchronized override fun chooseSwitch(idx: Int) {
        if (!live) return
        myIdx = idx.coerceIn(0, myMons.size - 1)
        onStatus("sending ${myMons.getOrNull(myIdx)?.name ?: "the next mon"} in…")
        send(Proto.switchMsg(turnN, idx))
    }

    fun again() = send("AGAIN")
    fun reelDone() { val cb = afterReel; afterReel = null; cb?.invoke() }
}
