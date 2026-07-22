/*
 * Poképad — CreatureRenderer (first pass).
 *
 * Turns a species' PokéAPI shape + types into an ORIGINAL 15x15 pixel creature
 * (no ripped sprites — the covenant). Archetype from `shape`, palette from the
 * types. Returns a 15x15 RGB frame the block Scene will draw; main() also writes
 * a scaled-up gallery PNG for review. This is ART-M1 (see docs/RENDERING_PLAN).
 *
 * First pass: readable by type-color + silhouette. Hero-tier hand-tuning and
 * more archetypes/features come next (with human eyes on the gallery).
 */
import java.awt.image.BufferedImage
import java.io.File
import javax.imageio.ImageIO

const val W = 15
val TYPE_COLOR = mapOf(
    "normal" to 0xBEB4A0, "fire" to 0xF06E3C, "water" to 0x5096F0, "electric" to 0xF5D246,
    "grass" to 0x6EC864, "ice" to 0x82D7E1, "fighting" to 0xC85A5A, "poison" to 0xAA5ABE,
    "ground" to 0xCDA564, "flying" to 0x96AFEB, "psychic" to 0xF56EA5, "bug" to 0xA5C846,
    "rock" to 0xB9A06E, "ghost" to 0x7864AF, "dragon" to 0x6E6EEB, "dark" to 0x6E5F5A,
    "steel" to 0xB4BECD)

class Frame {
    val px = IntArray(W * W) { 0 }   // 0 = transparent/black
    fun set(x: Int, y: Int, rgb: Int) { if (x in 0 until W && y in 0 until W) px[y * W + x] = rgb }
    fun get(x: Int, y: Int) = if (x in 0 until W && y in 0 until W) px[y * W + x] else 0
}

fun shade(rgb: Int, f: Double): Int {
    val r = ((rgb shr 16 and 0xFF) * f).toInt().coerceIn(0, 255)
    val g = ((rgb shr 8 and 0xFF) * f).toInt().coerceIn(0, 255)
    val b = ((rgb and 0xFF) * f).toInt().coerceIn(0, 255)
    return (r shl 16) or (g shl 8) or b
}

object Renderer {
    private fun ellipse(fr: Frame, cx: Double, cy: Double, rx: Double, ry: Double, c: Int) {
        for (y in 0 until W) for (x in 0 until W) {
            val dx = (x - cx) / rx; val dy = (y - cy) / ry
            if (dx * dx + dy * dy <= 1.0) fr.set(x, y, c)
        }
    }
    private fun eyes(fr: Frame, ex: Int, ey: Int, spread: Int = 2) {
        fr.set(ex - spread / 2 - 1, ey, 0x141014); fr.set(ex + spread / 2, ey, 0x141014)
        fr.set(ex - spread / 2 - 1, ey - 1, 0xF0F0F0); fr.set(ex + spread / 2, ey - 1, 0xF0F0F0)
    }

    fun render(shape: String, types: List<String>): Frame {
        val fr = Frame()
        val body = TYPE_COLOR[types[0]] ?: 0xBEB4A0
        val accent = TYPE_COLOR[types.getOrElse(1) { types[0] }] ?: body
        val dk = shade(body, 0.7)
        when (shape) {
            "ball", "blob" -> { ellipse(fr, 7.0, 7.5, 5.2, 5.0, body); eyes(fr, 7, 6) }
            "squiggle" -> {   // serpentine S
                for (y in 1..13) { val x = 7 + (Math.sin(y * 0.7) * 3).toInt(); for (dx in -1..1) fr.set(x + dx, y, body) }
                eyes(fr, 7 + (Math.sin(1.4) * 3).toInt(), 2)
            }
            "fish" -> { ellipse(fr, 6.0, 7.5, 4.6, 3.0, body); for (y in 5..10) for (x in 10..13) if (Math.abs(y - 7.5) < (x - 9) * 0.9) fr.set(x, y, accent); eyes(fr, 5, 6) }
            "wings", "bug-wings" -> {   // body + side wings
                ellipse(fr, 7.0, 8.0, 2.6, 4.2, body)
                for (s in intArrayOf(-1, 1)) for (y in 4..8) for (x in 1..4) fr.set(7 + s * (x + 1), y, shade(accent, 0.9))
                eyes(fr, 7, 6)
            }
            "tentacles" -> { ellipse(fr, 7.0, 5.5, 4.6, 4.0, body); for (x in intArrayOf(3, 5, 7, 9, 11)) for (y in 9..13) fr.set(x, y, if (y % 2 == 0) accent else body); eyes(fr, 7, 5) }
            "quadruped", "legs" -> {
                ellipse(fr, 7.0, 7.0, 5.0, 3.4, body)                 // body
                ellipse(fr, 11.0, 5.5, 2.4, 2.4, body)               // head
                for (lx in intArrayOf(4, 6, 9, 11)) for (y in 10..12) fr.set(lx, y, dk)  // legs
                eyes(fr, 11, 5, 1)
            }
            "armor" -> { for (y in 3..12) for (x in 3..11) fr.set(x, y, if ((x + y) % 4 == 0) shade(body, 1.15) else body); eyes(fr, 7, 6) }
            "upright", "humanoid", "arms", "heads" -> {              // biped
                ellipse(fr, 7.0, 4.5, 2.6, 2.6, body)                // head
                for (y in 6..11) for (x in 5..9) fr.set(x, y, body)  // torso
                for (s in intArrayOf(-1, 1)) for (y in 6..8) fr.set(7 + s * 4, y, shade(accent, 0.95)) // arms
                for (lx in intArrayOf(6, 8)) for (y in 12..13) fr.set(lx, y, dk)  // legs
                eyes(fr, 7, 4)
            }
            else -> { ellipse(fr, 7.0, 7.5, 4.8, 4.6, body); eyes(fr, 7, 6) }
        }
        // type aura hint: a faint ring in the secondary/accent color
        if (types.size > 1) for (a in 0 until 360 step 30) {
            val x = (7 + 6 * Math.cos(Math.toRadians(a.toDouble()))).toInt()
            val y = (7 + 6 * Math.sin(Math.toRadians(a.toDouble()))).toInt()
            if (fr.get(x, y) == 0) fr.set(x, y, shade(accent, 0.5))
        }
        return fr
    }
}

fun main() {
    // load species → (types, shape)
    data class Sp(val name: String, val types: List<String>, val shape: String)
    val sp = HashMap<String, Sp>()
    File("data/gen3_species.tsv").forEachLine {
        if (it.isBlank()) return@forEachLine
        val f = it.split("\t")
        val types = if (f[2].isEmpty()) listOf(f[1]) else listOf(f[1], f[2])
        sp[f[0]] = Sp(f[0], types, f.getOrElse(11) { "" })
    }
    val show = listOf("bulbasaur", "charmander", "squirtle", "treecko", "torchic", "mudkip",
        "pikachu", "gengar", "gyarados", "dragonite", "tyranitar", "snorlax",
        "alakazam", "machamp", "lapras", "mewtwo", "rayquaza", "groudon",
        "kyogre", "charizard", "blastoise", "venusaur", "loudred", "zigzagoon",
        "scizor", "gardevoir", "salamence", "metagross").filter { it in sp }

    val SCALE = 16; val cell = W * SCALE; val cols = 7; val rows = (show.size + cols - 1) / cols
    val img = BufferedImage(cols * cell, rows * cell, BufferedImage.TYPE_INT_RGB)
    val g = img.graphics
    show.forEachIndexed { i, name ->
        val fr = Renderer.render(sp[name]!!.shape, sp[name]!!.types)
        val ox = (i % cols) * cell; val oy = (i / cols) * cell
        g.color = java.awt.Color(0x101014); g.fillRect(ox, oy, cell, cell)
        for (y in 0 until W) for (x in 0 until W) {
            val c = fr.get(x, y); if (c == 0) continue
            g.color = java.awt.Color(c); g.fillRect(ox + x * SCALE, oy + y * SCALE, SCALE, SCALE)
        }
    }
    val out = File("build/creature_gallery.png"); out.parentFile.mkdirs()
    ImageIO.write(img, "png", out)
    println("wrote ${out.path}  (${show.size} creatures, ${cols}×${rows} grid)")
    println("order: " + show.joinToString(", "))
}
