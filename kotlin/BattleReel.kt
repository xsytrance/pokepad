/*
 * Poképad — Battle director (engine → visuals, end to end).
 *
 * Runs a REAL Gen-III battle on the Kotlin engine (Battle.kt), captures its
 * typed event stream (Ev.SendIn / Used / Faint / Win), and turns each event into
 * the matching animation beat (Anim.summon / attack / hurt / faint) rendered on a
 * two-panel 15x15 grid — exactly what the on-device Scene will do when it drives
 * two snapped blocks from the same event stream. No human input: the AI picks
 * moves, the mechanics decide damage, the pixels just report it.
 *
 * main() writes build/anim/reel_*.png (assembled to a GIF for review).
 */
import java.awt.image.BufferedImage
import java.io.File
import javax.imageio.ImageIO

fun main() {
    val dex = Dex("data")

    // shapes aren't in the engine's Species (renderer-only), so load them alongside
    val shape = HashMap<String, String>()
    File("data/gen3_species.tsv").forEachLine {
        if (it.isBlank()) return@forEachLine
        val f = it.split("\t"); shape[f[0]] = f.getOrElse(11) { "" }
    }
    fun feats(sp: String) = FEATURES[sp] ?: autoFeatures(dex.species[sp]!!.types)
    fun still(sp: String) = Renderer.render(shape[sp] ?: "", dex.species[sp]!!.types, feats(sp), -1)
    fun idle(sp: String, t: Int) = Renderer.render(shape[sp] ?: "", dex.species[sp]!!.types, feats(sp), t)

    // a compact, type-diverse showcase battle (deterministic seed → reproducible reel)
    fun mon(sp: String, vararg mv: String, nat: String = "hardy", ab: String? = null) =
            Mon(dex, sp, moves = mv.toList(), nature = nat, ability = ab)
    val teamA = listOf(
        mon("charizard", "flamethrower", "air-slash", "dragon-claw", "slash", nat = "timid"),
        mon("blastoise", "surf", "ice-beam", "flash-cannon", "body-slam", nat = "modest"))
    val teamB = listOf(
        mon("venusaur", "giga-drain", "sludge-bomb", "body-slam", "earthquake", nat = "modest"),
        mon("pikachu", "thunderbolt", "iron-tail", "quick-attack", "thunder", nat = "jolly"))

    val events = ArrayList<Ev>()
    val winner = Battle(dex, teamA, teamB, seed = 3, log = {}, emit = { events.add(it) }).run()

    // ── event stream → composite frame pairs ──────────────────────────────────
    val cur = HashMap<String, String>()               // side → currently-out species
    val pairs = ArrayList<Pair<Frame, Frame>>()
    var gt = 0
    fun push(a: Frame, b: Frame) { pairs.add(a to b); gt++ }
    fun sideFrames(actSide: String, actFrame: Frame, useIdleOther: Boolean): Pair<Frame, Frame> {
        val otherSide = if (actSide == "L") "R" else "L"
        val oth = cur[otherSide]?.let { if (useIdleOther) idle(it, gt) else still(it) } ?: blankFrame()
        return if (actSide == "L") actFrame to oth else oth to actFrame
    }
    fun gap(n: Int) = repeat(n) {                      // both sides breathe between beats
        val l = cur["L"]?.let { idle(it, gt) } ?: blankFrame()
        val r = cur["R"]?.let { idle(it, gt) } ?: blankFrame()
        push(l, r)
    }

    for (ev in events) when (ev) {
        is Ev.SendIn -> {
            cur[ev.side] = ev.species
            for (t in 0 until Anim.SUMMON) { val (l, r) = sideFrames(ev.side, Anim.summon(still(ev.species), t), true); push(l, r) }
            gap(2)
        }
        is Ev.Used -> {
            val defSide = if (ev.side == "L") "R" else "L"
            for (t in 0 until Anim.ATTACK) {
                val atk = Anim.attack(still(ev.species), t)
                val hurtT = t - 4
                val def = if (ev.dmg > 0 && hurtT in 0 until Anim.HURT) Anim.hurt(still(cur[defSide]!!), hurtT)
                          else cur[defSide]?.let { idle(it, gt) } ?: blankFrame()
                push(if (ev.side == "L") atk else def, if (ev.side == "L") def else atk)
            }
            gap(1)
        }
        is Ev.Faint -> {
            for (t in 0 until Anim.FAINT) { val (l, r) = sideFrames(ev.side, Anim.faint(still(ev.species), t), true); push(l, r) }
            cur.remove(ev.side)
            gap(2)
        }
        is Ev.Win -> repeat(12) {                       // victor holds the field
            val v = idle(ev.species, gt); val (l, r) = sideFrames(ev.side, v, true); push(l, r)
        }
    }

    // ── write PNG frames (2 panels + a thin divider) ──────────────────────────
    val scale = 18; val gapPx = scale; val w = 2 * W * scale + gapPx; val h = W * scale
    File("build/anim").mkdirs()
    File("build/anim").listFiles { f -> f.name.startsWith("reel_") }?.forEach { it.delete() }
    fun panel(g: java.awt.Graphics, fr: Frame, ox: Int) {
        g.color = java.awt.Color(0x101014); g.fillRect(ox, 0, W * scale, h)
        for (y in 0 until W) for (x in 0 until W) { val c = fr.get(x, y); if (c == 0) continue
            g.color = java.awt.Color(c); g.fillRect(ox + x * scale, y * scale, scale, scale) }
    }
    pairs.forEachIndexed { i, (a, b) ->
        val img = BufferedImage(w, h, BufferedImage.TYPE_INT_RGB)
        val g = img.graphics; g.color = java.awt.Color(0x18181E); g.fillRect(0, 0, w, h)
        panel(g, a, 0); panel(g, b, W * scale + gapPx)
        ImageIO.write(img, "png", File("build/anim/reel_%04d.png".format(i)))
    }
    println("battle: ${events.count { it is Ev.Used }} moves, ${events.count { it is Ev.Faint }} KOs, " +
            "winner=${winner?.name ?: "draw"}  →  ${pairs.size} frames")
}
