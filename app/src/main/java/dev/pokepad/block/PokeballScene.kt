package dev.pokepad.block

import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * POKÉBALL SHOWCASE — the block IS a Pokéball. Closed at rest (breathing
 * button, an occasional wobble like something's alive in there). Say a name
 * and the top shell cracks open for a PEEK of the mon inside; say "I choose
 * you!" and it bursts fully open — the mon stands on the glass with a shiny
 * sparkle if it earned one. Double-tap the glass to page through the mon's
 * REAL save stats (level+power → stat bars → types); a move demo washes the
 * glass in the move's type color while the mon lunges.
 *
 * Driven by ShowcaseActivity (voice + phone UI); works over USB or BLE MIDI.
 * All state @Volatile — render runs on the streamer thread, input elsewhere.
 */
class PokeballScene(
    /** animated 15×15 pixels for a species at time t (activity supplies the
     *  Renderer+dex-backed source; injected so the scene stays desktop-pure) */
    private val monPx: (species: String, t: Double) -> IntArray?,
    /** phone follows block pages (double-tap on the glass) */
    private val onPage: (Int) -> Unit = {},
) : Scene {

    /** everything the glass needs to show one mon (from the REAL save) */
    class Star(
        val species: String, val shiny: Boolean, val level: Int,
        /** hp/atk/def/spa/spd/spe REAL computed stats */
        val stats: Map<String, Int>,
        val types: List<String>,
    )

    private enum class St { BALL, PEEK, OPEN, ATTACK }

    @Volatile private var st = St.BALL
    @Volatile private var star: Star? = null
    @Volatile private var page = 0
    @Volatile private var stateAt = 0.0     // scene-time of last state change
    @Volatile private var t0 = -1.0
    @Volatile private var attackColor = 0xC03028
    @Volatile private var exit = false

    val PAGES = 3

    fun abort() { exit = true }
    override fun done() = exit

    // ── input API (any thread) ───────────────────────────────────────────────
    fun peek(s: Star) { star = s; page = 0; mark(St.PEEK) }
    fun reveal(s: Star) { star = s; page = 0; mark(St.OPEN) }
    fun close() { mark(St.BALL) }
    fun setPage(n: Int) { if (st == St.OPEN) page = n.mod(PAGES) }
    fun attack(typeColor: Int) { if (star != null) { attackColor = typeColor; mark(St.ATTACK) } }

    private fun mark(s: St) { st = s; stateAt = now }
    @Volatile private var now = 0.0

    // ── block double-tap → next page ────────────────────────────────────────
    private var lastTapAt = 0L
    override fun onTouch(ev: TouchEvent) {
        if (ev.phase != TouchPhase.START) return
        val t = ev.hostTimeMs
        if (t - lastTapAt < 450) {
            lastTapAt = 0
            if (st == St.OPEN) { page = (page + 1) % PAGES; onPage(page) }
        } else lastTapAt = t
    }

    // ── rendering ────────────────────────────────────────────────────────────
    private val W = 15
    private val BG = intArrayOf(6, 6, 12)

    override fun render(t: Double): ByteArray {
        if (t0 < 0) { t0 = t; stateAt = t }
        now = t
        val dt = t - stateAt
        return when (st) {
            St.BALL -> ball(t, lift = 0)
            St.PEEK -> peekFrame(t, dt)
            St.OPEN -> openFrame(t, dt)
            St.ATTACK -> attackFrame(t, dt)
        }
    }

    private fun buf(): ByteArray {
        val b = ByteArray(W * W * 3)
        for (i in 0 until W * W) { b[i * 3] = BG[0].toByte(); b[i * 3 + 1] = BG[1].toByte(); b[i * 3 + 2] = BG[2].toByte() }
        return b
    }
    private fun set(b: ByteArray, x: Int, y: Int, c: Int) {
        if (x !in 0 until W || y !in 0 until W) return
        val p = (y * W + x) * 3
        b[p] = ((c ushr 16) and 0xFF).toByte(); b[p + 1] = ((c ushr 8) and 0xFF).toByte(); b[p + 2] = (c and 0xFF).toByte()
    }

    private fun monPixels(t: Double): IntArray? = star?.let { monPx(it.species, t) }

    /** the closed ball; lift>0 raises the top shell that many rows (the peek) */
    private fun ball(t: Double, lift: Int, monBehind: Boolean = false): ByteArray {
        val b = buf()
        // something alive inside: subtle wobble every ~4s, breathing button
        val wob = if (lift == 0 && sin(t * 1.7) > 0.995) if (sin(t * 40) > 0) 1 else -1 else 0
        if (monBehind) monPixels(t)?.let { px ->
            for (y in 0 until W) for (x in 0 until W) if (px[y * W + x] != 0) set(b, x, y, px[y * W + x])
        }
        val cx = 7.0 + wob; val cy = 7.0; val r = 6.6
        for (y in 0 until W) for (x in 0 until W) {
            val d = sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy))
            if (d > r) continue
            val topHalf = y - cy < 0
            val edge = d > r - 1.3
            val c = when {
                kotlin.math.abs(y - cy) < 0.8 -> 0x14141A       // black band
                topHalf -> if (edge) 0x8E1F1A else if (x - cx < -1 && y - cy < -1) 0xF06058 else 0xD8322A
                else -> if (edge) 0x9A9AA4 else 0xEDEDF2
            }
            // the top shell rides up by `lift`; the gap shows what's behind
            set(b, x, if (topHalf) y - lift else y, c)
        }
        // button (breathes; flashes white while peeking)
        val bt = if (lift > 0) 0xFFFFFF else {
            val g = (200 + 55 * sin(t * 2.4)).roundToInt().coerceIn(150, 255)
            (g shl 16) or (g shl 8) or g
        }
        if (lift == 0) { set(b, 7, 7, bt); set(b, 6, 7, 0x3A3A44); set(b, 8, 7, 0x3A3A44) }
        return b
    }

    private fun peekFrame(t: Double, dt: Double): ByteArray {
        // shell cracks up 1px then 3px, light spilling out of the gap
        val lift = if (dt < 0.15) 1 else 3
        val b = ball(t, lift, monBehind = true)
        // glow line in the gap
        val gy = 6
        for (x in 3..11) {
            val p = (gy * W + x) * 3
            if (b[p].toInt() == BG[0] && b[p + 1].toInt() == BG[1]) set(b, x, gy, 0x8A8AD0)
        }
        return b
    }

    private fun openFrame(t: Double, dt: Double): ByteArray {
        val s = star ?: return ball(t, 0)
        // burst: white flash then the mon (or a stats page)
        if (dt < 0.25) { val b = buf(); for (y in 0 until W) for (x in 0 until W) set(b, x, y, 0xF0F0FF); return b }
        return when (page) {
            1 -> powerPage(s)
            2 -> statPage(s)
            else -> monPage(t, s)
        }
    }

    private fun monPage(t: Double, s: Star): ByteArray {
        val b = buf()
        monPixels(t)?.let { px ->
            for (y in 0 until W) for (x in 0 until W) if (px[y * W + x] != 0) set(b, x, y, px[y * W + x])
        }
        if (s.shiny) {                                   // it earned the sparkle
            val ph = ((t * 3).toInt() % 4)
            val pts = listOf(1 to 2, 13 to 3, 2 to 12, 12 to 12)
            pts.forEachIndexed { i, (x, y) -> if (i == ph) { set(b, x, y, 0xFFF2A0); set(b, x + 1, y, 0xF5D246) } }
        }
        return b
    }

    /** page 1: big level digits + POWER bar (stat total, 720 = full row) */
    private fun powerPage(s: Star): ByteArray {
        val b = buf()
        val txt = s.level.toString().take(3)
        val w = txt.length * 4 - 1
        var x0 = (W - w) / 2
        for (ch in txt) { glyph(b, ch, x0, 3, 0xF5D246); x0 += 4 }
        // 'Lv' dots over the number
        set(b, (W - w) / 2, 1, 0x8A87A0); set(b, (W - w) / 2 + 1, 1, 0x8A87A0)
        val total = s.stats.values.sum()
        val n = (13.0 * total / 720.0).roundToInt().coerceIn(1, 13)
        for (i in 0 until 13) set(b, 1 + i, 11, 0x2A3050)
        for (i in 0 until n) set(b, 1 + i, 11, if (i > 9) 0xF5D246 else 0x5FD97A)
        return b
    }

    /** page 2: six stat bars, hp atk def spa spd spe (real save spread) */
    private fun statPage(s: Star): ByteArray {
        val b = buf()
        val order = listOf("hp", "atk", "def", "spa", "spd", "spe")
        val cols = listOf(0x5FD97A, 0xE5533F, 0xF5D246, 0xB03E6E, 0x4A8A96, 0x5A6EA8)
        order.forEachIndexed { i, k ->
            val y = 1 + i * 2 + (if (i >= 3) 1 else 0)   // small gap between phys/spec
            val v = s.stats[k] ?: 0
            val n = (13.0 * v / 200.0).roundToInt().coerceIn(1, 13)
            for (x in 0 until 13) set(b, 1 + x, y, 0x1A2038)
            for (x in 0 until n) set(b, 1 + x, y, cols[i])
        }
        return b
    }

    private fun attackFrame(t: Double, dt: Double): ByteArray {
        if (dt > 1.1) { mark(St.OPEN); return openFrame(t, 1.0) }
        val b = buf()
        // type-colored shockwave ring expanding from center under the mon
        val rad = dt * 14.0
        for (y in 0 until W) for (x in 0 until W) {
            val d = sqrt((x - 7.0) * (x - 7.0) + (y - 7.0) * (y - 7.0))
            if (d < rad && d > rad - 2.5) set(b, x, y, attackColor)
        }
        monPixels(t)?.let { px ->
            val lunge = if (dt < 0.4) (dt * 5).toInt().coerceAtMost(2) else 0
            for (y in 0 until W) for (x in 0 until W) if (px[y * W + x] != 0) set(b, x - lunge + 1, y, px[y * W + x])
        }
        return b
    }

    /** 3×5 digit font for the level page */
    private fun glyph(b: ByteArray, ch: Char, x0: Int, y0: Int, c: Int) {
        val rows = DIGITS[ch] ?: return
        for (y in rows.indices) for (x in 0 until 3)
            if ((rows[y] shr (2 - x)) and 1 == 1) set(b, x0 + x, y0 + y, c)
    }

    private companion object {
        val DIGITS = mapOf(
            '0' to intArrayOf(0b111, 0b101, 0b101, 0b101, 0b111),
            '1' to intArrayOf(0b010, 0b110, 0b010, 0b010, 0b111),
            '2' to intArrayOf(0b111, 0b001, 0b111, 0b100, 0b111),
            '3' to intArrayOf(0b111, 0b001, 0b111, 0b001, 0b111),
            '4' to intArrayOf(0b101, 0b101, 0b111, 0b001, 0b001),
            '5' to intArrayOf(0b111, 0b100, 0b111, 0b001, 0b111),
            '6' to intArrayOf(0b111, 0b100, 0b111, 0b101, 0b111),
            '7' to intArrayOf(0b111, 0b001, 0b010, 0b010, 0b010),
            '8' to intArrayOf(0b111, 0b101, 0b111, 0b101, 0b111),
            '9' to intArrayOf(0b111, 0b101, 0b111, 0b001, 0b111))
    }
}
